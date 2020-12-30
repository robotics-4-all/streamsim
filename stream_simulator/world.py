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
            "logger": None
        }
        str_sim = __import__("stream_simulator")
        str_contro = getattr(str_sim, "controllers")
        map = {
           "relays": getattr(str_contro, "EnvRelayController"),
           "ph_sensors": getattr(str_contro, "EnvPhSensorController"),
           "temperature_sensors": getattr(str_contro, "EnvTemperatureSensorController"),
           "humidity_sensors": getattr(str_contro, "EnvHumiditySensorController"),
           "gas_sensors": getattr(str_contro, "EnvGasSensorController"),
           "camera_sensors": getattr(str_contro, "EnvCameraController"),
           "distance_sensors": getattr(str_contro, "EnvDistanceController"),
           "alarms_linear": getattr(str_contro, "EnvLinearAlarmController"),
           "alarms_area": getattr(str_contro, "EnvAreaAlarmController"),
           "ambient_light_sensor": getattr(str_contro, "EnvAmbientLightController"),
           "pan_tilt": getattr(str_contro, "EnvPanTiltController"),
           "speakers": getattr(str_contro, "EnvSpeakerController"),
           "lights": getattr(str_contro, "EnvLightController"),
           "thermostats": getattr(str_contro, "EnvThermostatController"),
           "microphones": getattr(str_contro, "EnvMicrophoneController"),
        }
        for d in self.env_devices:
            devices = self.env_devices[d]
            for dev in devices:
                self.register_controller(map[d](conf = dev, package = p))
