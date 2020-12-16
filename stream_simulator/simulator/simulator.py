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
from .conn_params import ConnParams
if ConnParams.type == "amqp":
    from commlib.transports.amqp import Subscriber
elif ConnParams.type == "redis":
    from commlib.transports.redis import Subscriber

class Simulator:
    def __init__(self,
                 tick = 0.25,
                 conf_file = None,
                 configuration = None,
                 device = None
                 ):

        self.tick = tick
        self.logger = Logger("simulator")

        self.parseConfiguration(conf_file, configuration)

        self.world = World()
        self.world.load_environment(configuration = self.configuration)

        self.robots = []
        for r in self.configuration["robots"]:
            self.robots.append(
                Robot(
                    configuration = r,
                    world = self.world.configuration,
                    map = self.world.map,
                    tick = self.tick
                )
            )

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

        self.configuration = tmp_conf

    def loadYaml(self, yaml_file):
        import yaml
        try:
            with open(yaml_file, 'r') as stream:
                conf = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            self.logger.critical(f"Yaml file {yaml_file} does not exist")
        return conf

    def stop(self):
        for r in self.robots:
            r.stop()
        self.logger.warning("Simulation stopped")


    def recursiveConfParse(self, conf, curr_dir):
        if isinstance(conf, dict):
            tmp_conf = {}
            for s in conf:
                # Check if "source"
                if s == "source":
                    self.logger.warning(f"We hit a source: {conf[s]}")
                    r = self.loadYaml(curr_dir + conf[s] + ".yaml")
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

    def start(self):
        for i in range(0, len(self.robots)):
            _robot = self.robots[i]
            _robot.start()
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
                    if "speaker" in c:
                        sp_con = _robot.controllers[c]
                        break

                if sp_con != None:
                    sp_con.google_speak(
                            language="el",
                            texts='Η συσκευή σας είναι έτοιμη προς χρήση!',
                            volume=50
                    )
