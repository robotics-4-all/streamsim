#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import logging
import pathlib
import yaml
import math

from .robot import Robot
from .world import World

from commlib_py.logger import Logger

class Simulator:
    def __init__(self, tick = 0.1):
        self.tick = tick
        self.logger = Logger("simulator")

        curr_dir = pathlib.Path().absolute()

        self.world = World(
            filename = str(curr_dir) + "/../worlds/map_1.yaml"
        )

        self.robot = Robot(
            world = self.world.world,
            map = self.world.map,
            name = "robot_1",
            tick = self.tick
        )

    def start(self):
        self.robot.start()
        self.logger.info("Simulation started")
        if self.robot.world['robots'][0]['mode'] == 'real':
            from r4a_apis.robot_api import RobotAPI
            from r4a_apis.google_api import GoogleAPI, GoogleLanguages
            import logging
            import os
            from r4a_apis.utilities import Logger as r4alog
            from r4a_apis.utilities import InputMessage, OutputMessage, TekException, Languages

            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/pi/google_ttsp.json"

            log = r4alog(allow_cutelog = False)
            log.debug('main', "TestGoogleApi_text2Speech")
            self.rapi = RobotAPI(logger = log)
            self.gapi = GoogleAPI(memory = self.rapi.memory, logger = log)
            InputMessage.logger = log
            OutputMessage.logger = log
            TekException.logger = log

            self.rapi.speak(InputMessage({
                'device_id': "id_0",
                'texts': ['Η συσκευή σας είναι έτοιμη προς χρήση!'],
                'language': Languages.EL,
                'volume': 100
            }))

    def experiment_sub(self):
        pass
