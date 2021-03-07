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
from stream_simulator.connectivity import CommlibFactory
from stream_simulator.base_classes import BaseThing

class ServoController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = Logger(conf["name"])
        else:
            self.logger = package["logger"]

        super(self.__class__, self).__init__()
        id = BaseThing.id

        # edit here
        info = {
            "type": "SERVO",
            "brand": "sg90",
            "base_topic": package["name"] + ".actuator.servo.d" + str(id),
            "name": "servo_" + str(id),
            "place": conf["place"],
            "id": id,
            "enabled": True,
            "orientation": conf["orientation"],
            "mode": package["mode"],
            "speak_mode": package["speak_mode"],
            "namespace": package["namespace"],
            "sensor_configuration": conf["sensor_configuration"],
            "device_name": package["device_name"],
            "endpoints":{
                "enable": "rpc",
                "disable": "rpc",
                "set": "subscriber"
            },
            "data_models": []
        }

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]
        self.base_topic = info["base_topic"]
        self.derp_data_key = info["base_topic"] + ".raw"

        # tf handling
        tf_package = {
            "type": "robot",
            "subtype": "servo",
            "pose": conf["pose"],
            "base_topic": info['base_topic'],
            "name": self.name
        }
        tf_package['host'] = package['device_name']
        tf_package['host_type'] = 'robot'
        package["tf_declare"].call(tf_package)

        # create object
        if self.info["mode"] == "real":
            from pidevices import PCA9685
            self.servo = PCA9685(bus=self.conf["bus"],
                                    frequency=self.conf["frequency"],
                                    max_data_length=self.conf["max_data_length"])

            self.servo_channel = self.conf["servo_channel"]

        self.servo_set_sub = CommlibFactory.getSubscriber(
            broker = "redis",
            topic = info["base_topic"] + ".set",
            callback = self.servo_set_callback
        )
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

    def enable_callback(self, message, meta):
        self.info["enabled"] = True
        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        self.servo_set_sub.run()

        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        if self.info["mode"] == "real":
            self.servo.start()

    def stop(self):
        self.servo_set_sub.stop()

        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()

        # stop servos
        if self.info["mode"] == "real":
            self.servo.stop()

    def servo_set_callback(self, message, meta):
        try:

            response = message
            self._angle = response['angle']

            # Storing value:
            r = CommlibFactory.derp_client.lset(
                self.derp_data_key,
                [{
                    "data": {
                        "angle": self._angle
                    },
                    "timestamp": time.time()
                }]
            )

            if self.info["mode"] == "mock":
                pass
            elif self.info["mode"] == "simulation":
                pass
            else: # The real deal
                self.servo.write(self.servo_channel, self._angle, degrees=True)

            self.logger.info("{}: New servo command: {}".format(self.name, self._angle))
        except Exception as e:
            self.logger.error("{}: servo is wrongly formatted: {} - {}".format(self.name, str(e.__class__), str(e)))
