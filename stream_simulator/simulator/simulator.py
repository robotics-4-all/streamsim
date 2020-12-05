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
    def __init__(self, tick = 0.25, conf_file = None, configuration = None, device = None):
        self.tick = tick
        self.logger = Logger("simulator")

        self.world = World()

        self.parseConfiguration(conf_file, configuration)

        self.robot = Robot(
            world = self.world.world,
            map = self.world.map,
            name = device,
            tick = self.tick
        )

    def stop(self):
        self.robot.stop()
        self.logger.warning("Simulation stopped")

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

            self.world.from_configuration(configuration = tmp_conf)
        elif configuration is not None:
            self.world.from_configuration(configuration = configuration)

    def start(self):
        self.robot.start()
        self.logger.warning("Simulation started")
        if self.robot.world['robots'][0]['mode'] == 'real' and self.robot.world['robots'][0]['speak_mode'] == "google":
            from r4a_apis.robot_api import RobotAPI
            from r4a_apis.google_api import GoogleAPI, GoogleLanguages
            import os
            from r4a_apis.utilities import InputMessage, OutputMessage, TekException, Languages

            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/pi/google_ttsp.json"

            self.logger.debug('main', "TestGoogleApi_text2Speech")
            self.rapi = RobotAPI(logger = self.logger)
            self.gapi = GoogleAPI(memory = self.rapi.memory, logger = self.logger)
            InputMessage.logger = self.logger
            OutputMessage.logger = self.logger
            TekException.logger = self.logger

            # Wait for rhasspy
            from derp_me.client import DerpMeClient
            self.derp_client = DerpMeClient(conn_params=ConnParams.get("redis"))
            self.logger.warning(f"New derp-me client from simulator.py")

            wait_for = self.robot.world['robots'][0]['wait_for']

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

            self.rapi.speak(InputMessage({
                'device_id': "id_0",
                'texts': ['Η συσκευή σας είναι έτοιμη προς χρήση!'],
                'language': Languages.EL,
                'volume': 50
            }))
