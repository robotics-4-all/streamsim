#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import yaml
import numpy
import logging

from commlib.logger import Logger
from stream_simulator.connectivity import CommlibFactory

from stream_simulator.device_configurations import RelayEnvConf

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

    def device_lookup(self):
        cnt = -1
        package = {
            "base": "world.",
            "mode": "simulation",
            "logger": None
        }
        for d in self.env_devices:
            devices = self.env_devices[d]
            if d == "relays":
                for dev in devices:
                    cnt += 1
                    c = RelayEnvConf.configure(
                        id = cnt,
                        conf = dev,
                        package = package
                    )
                    self.devices.append(c['device'])
                    if dev['name'] in self.controllers:
                        self.logger.error(f"Device {dev['name']} declared twice")
                    else:
                        self.controllers[dev['name']] = c['controller']
