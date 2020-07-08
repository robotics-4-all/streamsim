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

    def experiment_sub(self):
        pass
