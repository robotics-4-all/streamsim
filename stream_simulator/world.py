#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import yaml
import numpy
import logging

from commlib.logger import Logger
from stream_simulator.connectivity import CommlibFactory

class World:
    def __init__(self):
        self.logger = Logger("world")

    def load_environment(self, configuration = None):
        self.configuration = configuration
        self.name = self.configuration["world"]["name"]
        self.env_devices = self.configuration["env_devices"]
        self.logger.info("World loaded")
        self.devices = []
        self.controllers = {}

        self.devices_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.devices_callback,
            rpc_name = self.name + '.nodes_detector.get_connected_devices'
        )
        self.devices_rpc_server.run()

        self.setup()
        self.device_lookup()

        # Start all controllers
        for c in self.controllers:
            self.controllers[c].start()

    def devices_callback(self, message, meta):
        return {
            "devices": self.devices,
            "timestamp": time.time()
        }

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

    def register_controller(self, c):
        if c.name in self.controllers:
            self.logger.error(f"Device {c.name} declared twice")
        else:
            self.devices.append(c.info)
            self.controllers[c.name] = c

    def device_lookup(self):
        p = {
            "base": "world.",
            "mode": "simulation",
            "logger": None
        }
        for d in self.env_devices:
            devices = self.env_devices[d]
            if d == "relays":
                from stream_simulator.controllers import RelayController
                for dev in devices:
                    c = RelayController(conf = dev, package = p)
                    self.register_controller(c)
            if d == "ph_sensors":
                from stream_simulator.controllers import PhSensorController
                for dev in devices:
                    c = PhSensorController(conf = dev, package = p)
                    self.register_controller(c)
