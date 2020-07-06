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

from stream_simulator import Logger

class Simulator:
    def __init__(self, tick = 0.1, debug_level = logging.INFO):
        self.tick = tick
        self.logger = Logger("simulator", debug_level)

        curr_dir = pathlib.Path().absolute()
        self.world = World(filename = str(curr_dir) + "/../worlds/map_1.yaml",\
            debug_level = debug_level)
        resolution = self.world.world['map']['resolution']

        self.robot = Robot(name = "robot_1", tick = self.tick, debug_level = debug_level)
        pose = self.world.world['robots'][0]['starting_pose']

        self.robot.set_pose(\
            pose['x'] * resolution, \
            pose['y'] * resolution, \
            pose['theta'] / 180.0 * math.pi)
        self.robot.set_map(self.world.map, self.world.resolution)
        self.robot.world = self.world

    def start(self):
        self.robot.start()
        self.logger.info("Simulation started")

    def experiment_sub(self):
        pass
