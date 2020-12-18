#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import yaml
import numpy
import logging

from commlib.logger import Logger

from stream_simulator.connectivity import ConnParams
if ConnParams.type == "amqp":
    from commlib.transports.amqp import Publisher
elif ConnParams.type == "redis":
    from commlib.transports.redis import Publisher

class World:
    def __init__(self):
        self.logger = Logger("world")

    def load_environment(self, configuration = None):
        self.configuration = configuration
        self.logger.info("World loaded")
        self.setup()

    def setup(self):

        self.width = self.configuration['map']['width']
        self.height = self.configuration['map']['height']

        self.map = numpy.zeros((self.width, self.height))
        self.resolution = self.configuration['map']['resolution']

        # Add obstacles information in map
        self.obstacles = self.configuration['map']['obstacles']['lines']
        for obst in self.obstacles:
            x1 = obst['x1']
            x2 = obst['x2']
            y1 = obst['y1']
            y2 = obst['y2']
            if x1 == x2:
                if y1 > y2:
                    tmp = y2
                    y2 = y1
                    y1 = tmp
                for i in range(y1, y2 + 1):
                    self.map[x1, i] = 1
            elif y1 == y2:
                if x1 > x2:
                    tmp = x2
                    x2 = x1
                    x1 = tmp
                for i in range(x1, x2 + 1):
                    self.map[i, y1] = 1
