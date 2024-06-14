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

from stream_simulator.connectivity import CommlibFactory
from stream_simulator.transformations import TfController

### Dont know why but if I remove this no controllers are found
from stream_simulator.controllers import IrController

class Simulator:
    def __init__(self,
                 tick = 0.1,
                 conf_file = None,
                 configuration = None,
                 device = None
                 ):

        self.tick = tick
        self.logger = logging.getLogger(__name__)

        self.configuration = self.parseConfiguration(conf_file, configuration)
        
        if "simulation" in self.configuration:
            self.name = self.configuration["simulation"]["name"]
        else:
            self.name = "streamsim"
        
        self.configuration['tf_base'] = self.name + ".tf"

        resolution = 0.2
        if 'map' in self.configuration and 'resolution' in self.configuration['map']:
            resolution = self.configuration['map']['resolution']

        # Create the CommlibFactory
        self.commlib_factory = CommlibFactory(node_name = "Simulator")
        self.commlib_factory.run()
        
        self.logger.info(f"Created {self.name}.notifications publisher!")
        self.commlib_factory.notify = self.commlib_factory.getPublisher(
            topic = f"{self.name}.notifications"
        )

        self.devices_rpc_server = self.commlib_factory.getRPCService(
            callback = self.devices_callback,
            rpc_name = self.name + '.get_device_groups'
        )

        # Initializing tf
        self.tf = TfController(
            base = self.name,
            resolution = resolution,
        )
        
        # Initializing world
        self.world = World()
        self.world.load_environment(configuration = self.configuration)
        self.world_name = self.world.name

        # Initializing robots
        self.robots = []
        self.robot_names = []
        if "robots" in self.configuration:
            for r in self.configuration["robots"]:
                self.robots.append(
                    Robot(
                        configuration = r,
                        world = self.world,
                        map = self.world.map,
                        tick = self.tick,
                        namespace = self.name,
                    )
                )
                self.robot_names.append(r["name"])

        # Initializing tf
        self.tf.setup()

    def devices_callback(self, message):
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
        self.world.stop()
        self.tf.stop()
        self.commlib_factory.stop()
        self.logger.warning("Simulation stopped")

    def start(self):
        self.logger.info("******** Simulator starting *********")
        # Create robots
        for i in range(0, len(self.robots)):
            _robot = self.robots[i]
            _robot.start()

            self.commlib_factory.notify_ui(
                type = "new_message",
                data = {
                    "type": "logs",
                    "message": f"Robot {_robot.name} launched"
                }
            )

        # Communications report
        self.logger.info("Communications report:")
        total = 0
        for t in self.commlib_factory.stats:
            for k in self.commlib_factory.stats[t]:
                n = self.commlib_factory.stats[t][k]
                total += n
                if n == 0:
                    continue
                self.logger.info(f"\t{t} {k}: {n}")
        self.logger.info(f"Total connections: {total}")

        # Just to be informed for pose
        for i in range(0, len(self.robots)):
            self.robots[i].dispatch_pose_local()

        self.commlib_factory.notify_ui(
            type = "new_message",
            data = {
                "type": "logs",
                "message": f"Simulator started"
            }
        )

        self.logger.warning("Simulation started")
