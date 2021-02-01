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

class MotionController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = Logger(conf["name"])
        else:
            self.logger = package["logger"]

        super(self.__class__, self).__init__()
        id = "d_" + str(BaseThing.id)
        name = id
        if 'name' in conf:
            name = conf['name']
        _category = "actuator"
        _class = "motion"
        _subclass = "twist"
        _pack = package["name"]

        info = {
            "type": "SKID_STEER",
            "brand": "twist",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": name,
            "place": conf["place"],
            "id": id,
            "enabled": True,
            "orientation": conf["orientation"],
            "queue_size": 0,
            "mode": package["mode"],
            "namespace": package["namespace"],
            "sensor_configuration": conf["sensor_configuration"],
            "device_name": package["device_name"],
            "categorization": {
                "host_type": "robot",
                "place": _pack.split(".")[-1],
                "category": _category,
                "class": _class,
                "subclass": [_subclass],
                "name": name
            }
        }

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]
        self.base_topic = info["base_topic"]
        self.derp_data_key = info["base_topic"] + ".raw"

        # tf handling
        tf_package = {
            "type": "robot",
            "subtype": {
                "category": _category,
                "class": _class,
                "subclass": [_subclass]
            },
            "pose": conf["pose"],
            "base_topic": info['base_topic'],
            "name": self.name
        }
        tf_package['host'] = package['device_name']
        tf_package['host_type'] = 'robot'
        package["tf_declare"].call(tf_package)

        if self.info["mode"] == "real":
            from pidevices import DfrobotMotorControllerRPiGPIO

            self.motor_driver = DfrobotMotorControllerRPiGPIO(E1=self.conf["E1"], M1=self.conf["M1"], E2=self.conf["E2"], M2=self.conf["M2"])

            self.wheel_separation = self.conf["wheel_separation"]
            self.wheel_radius = self.conf["wheel_radius"]

        self._linear = 0
        self._angular = 0

        self.vel_sub = CommlibFactory.getSubscriber(
            broker = "redis",
            topic = info["base_topic"] + ".set",
            callback = self.cmd_vel
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
        self.vel_sub.run()

        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        if self.info["mode"] == "real":
            self.motor_driver.start()

    def stop(self):
        self.vel_sub.stop()

        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()

        if self.info["mode"] == "real":
            self.motor_driver.stop()

    def cmd_vel(self, message, meta):
        try:
            response = message

            # Checks for types
            try:
                float(response['linear'])
                float(response['angular'])
            except:
                if not response['linear'].isdigit():
                    raise Exception("Linear is no integer nor float")
                if not response['angular'].isdigit():
                    raise Exception("Angular is no integer nor float")

            self._linear = response['linear']
            self._angular = response['angular']
            self._raw = response['raw']

            # Storing value:
            r = CommlibFactory.derp_client.lset(
                self.derp_data_key,
                [{
                    "data": {
                        "linear": self._linear,
                        "angular": self._angular,
                        "raw": self._raw
                    },
                    "timestamp": time.time()
                }]
            )

            if self.info["mode"] == "mock":
                pass
            elif self.info["mode"] == "simulation":
                pass
            else: # The real deal
                if self._raw == True:
                    self.motor_driver.write(self._linear, self._angular)        # write pwm values
                else:
                    self.motor_driver.setSpeed(self._linear, self._angular)     # write speed values

            self.logger.debug("{}: New motion command: {}, {}".format(self.name, self._linear, self._angular))
        except Exception as e:
            self.logger.error("{}: cmd_vel is wrongly formatted: {} - {}".format(self.name, str(e.__class__), str(e)))
