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

class EnvPanTiltController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = Logger(conf["name"])
        else:
            self.logger = package["logger"]

        super(self.__class__, self).__init__()

        _name = conf["name"]

        id = BaseThing.id
        info = {
            "type": "PAN_TILT",
            "brand": "bosch",
            "base_topic": package["base"] + conf["place"] + ".effector.motors.pan_tilt.d" + str(id),
            "name": "pan_tilt_" + str(id),
            "place": conf["place"],
            "enabled": True,
            "mode": conf["mode"],
            "conf": conf,
            "endpoints":{
                "enable": "rpc",
                "disable": "rpc",
                "set": "pub",
                "get": "rpc",
                "set_mode": "rpc"
            }
        }

        self.pose = info["conf"]["pose"]

        self.info = info
        self.name = info["name"]
        self.base_topic = info["base_topic"]

        self.place = info["conf"]["place"]
        self.pan = 0
        self.tilt = 0

        # tf handling
        tf_package = {
            "type": "env",
            "subtype": "pan_tilt",
            "pose": self.pose,
            "base_topic": self.base_topic,
            "name": self.name
        }

        self.host = None
        if 'host' in info['conf']:
            self.host = info['conf']['host']
            tf_package['host'] = self.host

        package["tf_declare"].call(tf_package)

        self.operation = info['conf']['operation']
        self.operation_parameters = info['conf']['operation_parameters']

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
        self.set_subscriber = CommlibFactory.getSubscriber(
            broker = "redis",
            callback = self.set_callback,
            topic = info["base_topic"] + ".set"
        )
        self.get_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.get_callback,
            rpc_name = info["base_topic"] + ".get"
        )
        self.set_operation_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.set_mode_callback,
            rpc_name = info["base_topic"] + ".set_mode"
        )

    def set_mode_callback(self, message, meta):
        self.operation = message["mode"]
        return {}

    def enable_callback(self, message, meta):
        self.info["enabled"] = True

        self.enable_rpc_server.run()
        self.disable_rpc_server.run()
        self.get_rpc_server.run()
        self.set_subscriber.run()

        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        return {"enabled": False}

    def get_callback(self, message, meta):
        return {
            'pan': self.pan,
            'tilt': self.tilt
        }

    def set_callback(self, message, meta):
        self.pan = message['pan']
        self.tilt = message['tilt']
        return {}

    def start(self):
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()
        self.get_rpc_server.run()
        self.set_subscriber.run()

    def stop(self):
        self.info["enabled"] = False
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()
        self.get_rpc_server.stop()
        self.set_subscriber.stop()
