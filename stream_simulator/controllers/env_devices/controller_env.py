#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random

from commlib.logger import Logger
from stream_simulator.connectivity import CommlibFactory

class RelayController:
    def __init__(self, info = None, logger = None):
        if logger is None:
            self.logger = Logger(info["name"])
        else:
            self.logger = logger

        self.info = info
        self.name = info["name"]
        self.base_topic = info["base_topic"]
        self.derp_data_key = info["base_topic"] + ".raw"

        self.state = info["initial_state"]
        self.available_states = info["states"]

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
        self.get_status_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.get_status_callback,
            rpc_name = info["base_topic"] + ".get"
        )
        self.set_status_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.set_status_callback,
            rpc_name = info["base_topic"] + ".set"
        )

    def enable_callback(self, message, meta):
        self.info["enabled"] = True
        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        return {"enabled": False}

    def get_status_callback(self, message, meta):
        if self.info["enabled"]:
            return {"status": self.status}
        return {"status": None}

    def set_status_callback(self, message, meta):
        if not self.info["enabled"]:
            return {"status": None}

        new_status = message["status"]
        if new_status not in self.available_states:
            raise Exception(f"Relay {self.name} does \
                            not support {new_status} as status")

        self.status = new_status
        return {"status": self.status}

    def start(self):
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()
        self.get_status_rpc_server.run()
        self.set_status_rpc_server.run()

    def stop(self):
        self.info["enabled"] = False
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()
        self.get_status_rpc_server.stop()
        self.set_status_rpc_server.stop()
