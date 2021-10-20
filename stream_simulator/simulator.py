#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import logging
import pathlib
import yaml
import math
import pprint as pp

from .robot import Robot
from .world import World

from commlib.logger import Logger
from stream_simulator.connectivity import ConnParams
if ConnParams.type == "amqp":
    from commlib.transports.amqp import Subscriber
elif ConnParams.type == "redis":
    from commlib.transports.redis import Subscriber

from stream_simulator.connectivity import CommlibFactory
from stream_simulator.transformations import TfController

### Dont know why but if I remove this no controllers are found
from stream_simulator.controllers import IrController

class Simulator:
    def __init__(self,
                 tick = 0.1,
                 conf_file = None,
                 configuration = None,
                 device_sim_name = None
                 ):

        self.tick = tick
        self.logger = Logger("simulator")

        logging.getLogger("pika").setLevel(logging.WARNING)
        logging.getLogger("Adafruit_I2C").setLevel(logging.INFO)
        logging.getLogger().setLevel(logging.WARNING)

        self.configuration = self.parseConfiguration(conf_file, configuration)
        if "simulation" in self.configuration:
            self.name = self.configuration["simulation"]["name"]
        else:
            self.name = "streamsim"

        resolution = 0.2
        if 'map' in self.configuration:
            if 'resolution' in self.configuration['map']:
                resolution = self.configuration['map']['resolution']

        if 'amqp' in self.configuration:
            ConnParams.set(
                type = "amqp",
                settings = self.configuration['amqp']
            )
        
        if 'redis' in self.configuration:
            ConnParams.set(
                type = "redis",
                settings = self.configuration['redis']
            )

        # Declaring tf controller and setting basetopic
        self.tf = TfController(
            base = self.name,
            device = device_sim_name
        )
        self.configuration['tf_base'] = self.tf.base_topic
        time.sleep(0.5)

        real_mode_exists = False
        if "robots" in self.configuration:
            for robot in self.configuration["robots"]:
                if "mode" in robot:
                    if robot["mode"] == "real":
                        real_mode_exists = True
                        break

        # Setup notification channel
        if not real_mode_exists:
            self.logger.warning(f"==========Created {device_sim_name}.notifications publisher!============")
            CommlibFactory.notify_sim = CommlibFactory.getPublisher(
                broker = 'amqp',
                topic = f"{device_sim_name}.notifications"
            )
        else:
            self.logger.warning("Robot with real mode detected. Skipping notifications publisher!")

        # Initializing world
        self.world = World()
        self.world.load_environment(configuration = self.configuration)
        self.world_name = self.world.name

        # Initializing robots
        self.robots = []
        self.robot_names = []
        if "robots" in self.configuration:
            for r in self.configuration["robots"]:
                # check if a robot name even exists
                if not "name" in r:
                    r["name"] = device_sim_name if device_sim_name is not None else "default"
                    self.logger.error("No robot name given in configuration. Setting it to <default>!")
                else: 
                    self.logger.warning(f"==============={r['name']}===============")

                # create robot
                self.robots.append(
                    Robot(
                        configuration = r,
                        world = self.world,
                        map = self.world.map,
                        sim_name = device_sim_name,
                        tick = self.tick
                    )
                )
                self.robot_names.append(r["name"])

        self.devices_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.devices_callback,
            rpc_name = self.name + '.get_device_groups'
        )
        self.devices_rpc_server.run()

    def devices_callback(self, message, meta):
        return {
                "robots": self.robot_names,
                "world": self.world_name
        }

    def parseConfiguration(self, conf_file, configuration):
        tmp_conf = {}
        curr_dir = str(pathlib.Path().absolute()) + "/../configurations/"
        if conf_file is not None:
            # Must load and parse file here
            filename = curr_dir + conf_file + ".yaml"
            try:
                tmp_conf = self.loadYaml(filename)
                tmp_conf = self.recursiveConfParse(tmp_conf, curr_dir)
            except Exception as e:
                self.logger.critical(str(e))
        elif configuration is not None:
            tmp_conf = configuration

        return tmp_conf

    def loadYaml(self, yaml_file):
        import yaml
        try:
            with open(yaml_file, 'r') as stream:
                conf = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            self.logger.critical(f"Yaml file {yaml_file} does not exist")
        return conf

    def recursiveConfParse(self, conf, curr_dir):
        if isinstance(conf, dict):
            tmp_conf = {}
            for s in conf:
                # Check if "source"
                if s == "source":
                    self.logger.warning(f"We hit a source: {conf[s]}")
                    r = self.loadYaml(curr_dir + conf[s] + ".yaml")
                    r = self.recursiveConfParse(r, curr_dir)
                    tmp_conf = {**tmp_conf, **r}
                else:
                    r = self.recursiveConfParse(conf[s], curr_dir)
                    tmp_conf[s] = r

            return tmp_conf

        elif isinstance(conf, list):
            tmp_conf = []
            for s in conf:
                tmp_conf.append(self.recursiveConfParse(s, curr_dir))
            return tmp_conf
        else:
            return conf

    def stop(self):
        for r in self.robots:
            r.stop()
        self.logger.warning("Simulation stopped")

    def start(self):
        # Create robots
        for i in range(0, len(self.robots)):
            _robot = self.robots[i]
            _robot.start()

            CommlibFactory.notify_ui(
                type = "logs",
                data = {
                    "message": f"Robot {_robot.name} launched"
                }
            )

            self.logger.warning("Simulation started")
            if _robot.world['robots'][i]['mode'] == 'real' and _robot.world['robots'][i]['speak_mode'] == "google":
                # Wait for rhasspy
                from derp_me.client import DerpMeClient
                self.derp_client = DerpMeClient(conn_params=ConnParams.get("redis"))
                self.logger.warning(f"New derp-me client from simulator.py")

                wait_for = _robot.world['robots'][i]['wait_for']

                if "rhasspy" in wait_for:
                    rhasspy_ok = False
                    self.logger.warning("Waiting for rhasspy")
                    while not rhasspy_ok:
                        time.sleep(0.3)
                        r = self.derp_client.lget("rhasspy/state", 0, 0)
                        self.logger.info(r)
                        if r['status'] == 1:
                            self.logger.warning("Rhasspy is up!")
                            rhasspy_ok = True

                # Get the speaker
                sp_con = None
                for c in _robot.controllers:
                    if _robot.controllers[c].info['categorization']['subclass'][0] == "speaker":
                        sp_con = _robot.controllers[c]
                        break

                if sp_con != None:
                    sp_con.google_speak(
                            language="el",
                            texts='Η συσκευή σας είναι έτοιμη προς χρήση!',
                            volume=50
                    )

        self.tf.setup()

        # Setup tf affectability channel
        CommlibFactory.get_tf_affection = CommlibFactory.getRPCClient(
            rpc_name = f"{self.name}.tf.get_affections"
        )
        # Setup tf channel
        CommlibFactory.get_tf = CommlibFactory.getRPCClient(
            rpc_name = f"{self.name}.tf.get_tf"
        )

        # Communications report
        self.logger.info("Communications report:")
        total = 0
        for t in CommlibFactory.stats:
            for k in CommlibFactory.stats[t]:
                n = CommlibFactory.stats[t][k]
                total += n
                if n == 0:
                    continue
                self.logger.info(f"\t{t} {k}: {n}")
        self.logger.info(f"Total connections: {total}")

        # Just to be informed for pose
        for i in range(0, len(self.robots)):
            self.robots[i].dispatch_pose_local()

        for _robot in self.robots:
            CommlibFactory.notify_ui(
                type = "logs",
                data = {
                    "message": f"Simulator started"
                }
            )
