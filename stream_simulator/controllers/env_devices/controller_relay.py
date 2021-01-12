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

class EnvRelayController(BaseThing):
    def __init__(self, conf = None, package = None):
        self.logger = Logger(conf['name']) if package['logger'] is None \
            else package['logger']

        super(self.__class__, self).__init__()

        _name = conf["name"]

        id = BaseThing.id
        info = {
            "type": "RELAY",
            "brand": "relay",
            "base_topic": package["base"] + conf["place"] + ".effector.mechanical." + _name + ".d" + str(id),
            "name": "relay_" + str(id),
            "place": conf["place"],
            "enabled": True,
            "mode": conf["mode"],
            "conf": conf,
            "endpoints":{
                "enable": "rpc",
                "disable": "rpc",
                "set": "rpc",
                "get": "rpc"
            }
        }

        self.pose = info["conf"]["pose"]

        self.info = info
        self.name = info["name"]
        self.base_topic = info["base_topic"]

        self.state = info["conf"]["initial_state"]
        self.allowed_states = info["conf"]["states"]
        self.place = info["conf"]["place"]

        # tf handling
        tf_package = {
            "type": "env",
            "subtype": "relay",
            "pose": self.pose,
            "base_topic": self.base_topic,
            "name": self.name
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
        return {"state": self.state}

    def set_callback(self, message, meta):
        state = message["state"]
        if state not in self.allowed_states:
            raise Exception(f"Relay {self.name} does not allow {state} state")

        self.state = state
        return {"state": self.state}

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
