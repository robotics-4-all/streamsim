#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import yaml
import numpy
import logging
import math

from stream_simulator.connectivity import CommlibFactory

class World:
    def __init__(self):
        self.commlib_factory = CommlibFactory(node_name = "World")
        self.commlib_factory.run()
        self.logger = logging.getLogger(__name__)

    def load_environment(self, configuration = None):
        self.configuration = configuration

        self.tf_base = self.configuration['tf_base']
        self.tf_declare_rpc = self.commlib_factory.getRPCClient(
            rpc_name = self.tf_base + ".declare"
        )

        self.name = "world"
        self.env_properties = {
            'temperature': 20,
            'humidity': 50,
            'luminosity': 100
        }

        if "world" in self.configuration:
            self.name = self.configuration["world"]["name"]

            if 'properties' in self.configuration['world']:
                prop = self.configuration['world']['properties']
                for p in ['temperature', 'humidity', 'luminosity']:
                    if p in prop:
                        self.env_properties[p] = prop[p]

        self.env_devices = []
        if "env_devices" in self.configuration:
            self.env_devices = self.configuration["env_devices"]

        self.actors = []
        if "actors" in self.configuration:
            self.actors = self.configuration["actors"]

        # self.logger.info("World loaded")
        self.devices = []
        self.controllers = {}

        self.devices_rpc_server = self.commlib_factory.getRPCService(
            callback = self.devices_callback,
            rpc_name = self.name + '.nodes_detector.get_connected_devices'
        )

        self.setup()
        self.device_lookup()

        self.actors_configurations = []
        self.actors_controllers = {}
        self.actors_lookup()

        # Start all controllers
        for c in self.controllers:
            self.controllers[c].start()

    def devices_callback(self, message):
        return {
            "devices": self.devices,
            "timestamp": time.time()
        }

    def setup(self):
        self.width = 0
        self.height = 0
        self.map = None
        self.resolution = 0
        self.obstacles = []
        if 'map' in self.configuration:
            self.resolution = self.configuration['map']['resolution']
            self.width = int(self.configuration['map']['width'] / self.resolution)
            self.height = int(self.configuration['map']['height'] / self.resolution)
            self.map = numpy.zeros((self.width, self.height))
            

            # Add obstacles information in map
            self.obstacles = self.configuration['map']['obstacles']['lines']
            for obst in self.obstacles:
                x1 = max(min(int(obst['x1'] / self.resolution), self.width - 1), 0)
                x2 = max(min(int(obst['x2'] / self.resolution), self.width - 1), 0)
                y1 = max(min(int(obst['y1'] / self.resolution), self.height - 1), 0)
                y2 = max(min(int(obst['y2'] / self.resolution), self.height - 1), 0)

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
                else: # we have a tilted line
                    f_ang = math.atan2(y2 - y1, x2 - x1)
                    dist = math.sqrt(
                        math.pow(x2 - x1, 2) + math.pow(y2 - y1, 2)
                    )
                    dist = int(dist) + 1
                    d = 0
                    while d <= dist:
                        tmpx = int(x1 + d * math.cos(f_ang))
                        tmpy = int(y1 + d * math.sin(f_ang))
                        d += 1
                        self.map[tmpx, tmpy] = 1

    def register_controller(self, c):
        if c.name in self.controllers:
            self.logger.error(f"Device {c.name} declared twice")
        else:
            self.devices.append(c.info)
            self.controllers[c.name] = c

    def device_lookup(self):
        p = {
            "base": "world",
            "logger": None,
            "namespace": self.configuration["simulation"]["name"],
            'tf_declare': self.tf_declare_rpc,
            'tf_declare_rpc_topic': self.tf_base + '.declare',
            'tf_affection_rpc_topic': self.tf_base + '.get_affections',
            'env': self.env_properties,
            "map": self.map,
            "resolution": self.resolution
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
           "humidifiers": getattr(str_contro, "EnvHumidifierController"),
        }
        for d in self.env_devices:
            devices = self.env_devices[d]
            for dev in devices:
                # Handle pose theta
                if 'theta' not in dev['pose']:
                    dev['pose']['theta'] = None

                self.register_controller(map[d](conf = dev, package = p))

    def actors_lookup(self):
        p = {
            "logger": None,
            'tf_declare': self.tf_declare_rpc
        }
        str_sim = __import__("stream_simulator")
        str_contro = getattr(str_sim, "controllers")
        map = {
           "humans": getattr(str_contro, "HumanActor"),
           "superman": getattr(str_contro, "SupermanActor"),
           "sound_sources": getattr(str_contro, "SoundSourceActor"),
           "qrs": getattr(str_contro, "QrActor"),
           "barcodes": getattr(str_contro, "BarcodeActor"),
           "colors": getattr(str_contro, "ColorActor"),
           "texts": getattr(str_contro, "TextActor"),
           "rfid_tags": getattr(str_contro, "RfidTagActor"),
           "fires": getattr(str_contro, "FireActor"),
           "waters": getattr(str_contro, "WaterActor"),
        }
        for type in self.actors:
            actors = self.actors[type]
            for act in actors:
                c = map[type](conf = act, package = p)
                if c.name in self.actors:
                    self.logger.error(f"Device {c.name} declared twice")
                else:
                    self.actors_configurations.append(c.info)
                    self.actors_controllers[c.name] = c
                    self.logger.info(f"Actor {c.name} declared")
