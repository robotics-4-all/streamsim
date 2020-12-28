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

class EnvLinearAlarmController(BaseThing):
    def __init__(self,
                 conf = None,
                 package = None
                 ):

        if package["logger"] is None:
            self.logger = Logger(conf["name"])
        else:
            self.logger = package["logger"]

        super(self.__class__, self).__init__()

        _name = conf["name"]

        _type = "LINEAR_ALARM"
        _category = "alarm"
        _brand = "secur"
        _name_suffix = "alarm_line_"
        _endpoints = {
            "enable": "rpc",
            "disable": "rpc",
            "data": "pub",
            "triggers": "pub",
        }

        id = BaseThing.id
        info = {
            "type": _type,
            "brand": _brand,
            "base_topic": package["base"] + conf["place"] + f".sensor.{_category}.{_name}.d" + str(id),
            "name": _name_suffix + str(id),
            "place": conf["place"],
            "enabled": True,
            "mode": conf["mode"],
            "conf": conf,
            "endpoints": _endpoints
        }

        self.info = info
        self.name = info["name"]
        self.base_topic = info["base_topic"]
        self.hz = info['conf']['hz']
        self.mode = info["mode"]
        self.place = info["conf"]["place"]
        self.pose = info["conf"]["pose"]

        # Communication
        self.publisher = CommlibFactory.getPublisher(
            broker = "redis",
            topic = self.base_topic + ".data"
        )
        self.publisher_triggers = CommlibFactory.getPublisher(
            broker = "redis",
            topic = self.base_topic + ".triggers"
        )
        self.enable_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.enable_callback,
            rpc_name = self.base_topic + ".enable"
        )
        self.disable_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.disable_callback,
            rpc_name = self.base_topic + ".disable"
        )

    def sensor_read(self):
        self.logger.info(f"Sensor {self.name} read thread started")
        prev = 0
        triggers = 0
        while self.info["enabled"]:
            time.sleep(1.0 / self.hz)

            val = None
            if self.mode == "mock":
                val = random.randint(0, 1)

            # Publishing value:
            self.publisher.publish({
                "value": val,
                "timestamp": time.time()
            })

            if prev == 0 and val == 1:
                triggers += 1
                self.publisher_triggers.publish({
                    "value": triggers,
                    "timestamp": time.time()
                })
            prev = val

    def enable_callback(self, message, meta):
        self.info["enabled"] = True

        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        self.sensor_read_thread = threading.Thread(target = self.sensor_read)
        self.sensor_read_thread.start()

        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        if self.info["enabled"]:
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()

    def stop(self):
        self.info["enabled"] = False
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()
