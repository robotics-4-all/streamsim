#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random

from colorama import Fore, Style

from commlib.logger import Logger
from stream_simulator.base_classes import BaseThing
from stream_simulator.connectivity import CommlibFactory

class EnvLightController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = Logger(conf["name"])
        else:
            self.logger = package["logger"]

        super(self.__class__, self).__init__()

        _type = "LIGHTS"
        _category = "actuator"
        _class = "visual"
        _subclass = "leds"

        _name = conf["name"]
        _pack = package["base"]
        _place = conf["place"]
        id = "d_" + str(BaseThing.id)
        info = {
            "type": _type,
            "base_topic": f"{_pack}.{_place}.{_category}.{_class}.{_subclass}.{_name}",
            "name": _name,
            "place": conf["place"],
            "enabled": True,
            "mode": conf["mode"],
            "conf": conf,
            "categorization": {
                "host_type": _pack,
                "place": _place,
                "category": _category,
                "class": _class,
                "subclass": [_subclass],
                "name": _name
            }
        }

        self.info = info
        self.pose = info["conf"]["pose"]
        self.name = info["name"]
        self.base_topic = info["base_topic"]
        self.place = info["conf"]["place"]
        self.luminosity = info['conf']['luminosity']
        self.color = {
            'r': 255,
            'g': 255,
            'b': 255,
            'a': self.luminosity * 255.0 / 100
        }
        self.range = info["conf"]["range"]

        # tf handling
        tf_package = {
            "type": "env",
            "subtype": {
                "category": _category,
                "class": _class,
                "subclass": [_subclass]
            },
            "pose": self.pose,
            "base_topic": self.base_topic,
            "name": self.name,
            "range": self.range,
            "properties": {
                "color": self.color,
                "luminosity": self.luminosity
            }
        }

        self.host = None
        if 'host' in info['conf']:
            self.host = info['conf']['host']
            tf_package['host'] = self.host
            # No other host type is available for env_devices
            tf_package['host_type'] = 'pan_tilt'

        package["tf_declare"].call(tf_package)

        self.enable_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.enable_callback,
            rpc_name = info["base_topic"] + ".enable"
        )
        self.disable_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.disable_callback,
            rpc_name = info["base_topic"] + ".disable"
        )
        self.set_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.set_callback,
            rpc_name = info["base_topic"] + ".set"
        )
        self.get_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.get_callback,
            rpc_name = info["base_topic"] + ".get"
        )

    def enable_callback(self, message, meta):
        self.info["enabled"] = True

        self.enable_rpc_server.run()
        self.disable_rpc_server.run()
        self.get_rpc_server.run()
        self.set_rpc_server.run()

        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        return {"enabled": False}

    def get_callback(self, message, meta):
        return {
            "color": self.color,
            "luminosity": self.luminosity
        }

    def set_callback(self, message, meta):
        if "r" in message:
            self.color['r'] = message["r"]
        if "g" in message:
            self.color['g'] = message["g"]
        if "b" in message:
            self.color['b'] = message["b"]
        if "luminosity" in message:
            self.luminosity = message["luminosity"]
            self.color['a'] = self.luminosity * 255.0 / 100.0

        return {}

    def start(self):
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()
        self.get_rpc_server.run()
        self.set_rpc_server.run()

    def stop(self):
        self.info["enabled"] = False
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()
        self.get_rpc_server.stop()
        self.set_rpc_server.stop()
