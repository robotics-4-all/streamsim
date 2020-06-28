#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import logging

from .robot import Robot

from stream_simulator import Logger

class Simulator:
    def __init__(self, tick = 0.1, debug_level = logging.INFO):
        self.tick = tick
        self.logger = Logger("simulator", debug_level)

        self.robot = Robot(name = "robot_1", tick = self.tick, debug_level = debug_level)
        self.robot.set_pose(1, 1, 0.0)

    def start(self):
        self.robot.start()
        self.logger.info("Simulation started")
