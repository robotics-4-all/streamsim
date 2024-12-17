#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random

from colorama import Fore, Style

from stream_simulator.base_classes import BaseThing

class LedsController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        id = "d_leds_" + str(BaseThing.id + 1)
        name = id
        if 'name' in conf:
            name = conf['name']
        _category = "actuator"
        _class = "visual"
        _subclass = "leds"
        _pack = package["name"]
        _namespace = package["namespace"]

        super().__init__(id)

        info = {
            "type": "LED",
            "brand": "neopx",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": name,
            "place": conf["place"],
            "id": id,
            "enabled": True,
            "orientation": float(conf["orientation"]),
            "queue_size": 0,
            "mode": package["mode"],
            "speak_mode": package["speak_mode"],
            "namespace": package["namespace"],
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
        self.base_topic = info["base_topic"]
        self.derp_data_key = info["base_topic"] + ".raw"

        self.set_tf_communication(package)

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
            "name": self.name,
            "namespace": _namespace,
            "range": conf["range"]
        }
        tf_package['host'] = package['device_name']
        tf_package['host_type'] = 'robot'
        if 'host' in conf:
            tf_package['host'] = conf['host']
            tf_package['host_type'] = 'pan_tilt'
        
        self.tf_declare_rpc.call(tf_package)

        self._color = {
                'r': 0.0,
                'g': 0.0,
                'b': 0.0
        }
        self._luminosity = 0

        self.leds_pub = self.commlib_factory.getPublisher(
            topic = self.info['device_name'] + ".leds"
        )
        self.leds_wipe_pub = self.commlib_factory.getPublisher(
            topic = self.base_topic + ".wipe"
        )

        self.set_rpc_server = self.commlib_factory.getRPCService(
            callback = self.leds_set_callback,
            rpc_name = self.base_topic + ".set"
        )
        self.get_rpc_server = self.commlib_factory.getRPCService(
            callback = self.leds_get_callback,
            rpc_name = self.base_topic + ".get"
        )
        self.leds_wipe_server = self.commlib_factory.getRPCService(
            callback = self.leds_wipe_callback,
            rpc_name = self.base_topic + ".wipe"
        )
        self.enable_rpc_server = self.commlib_factory.getRPCService(
            callback = self.enable_callback,
            rpc_name = self.base_topic + ".enable"
        )
        self.disable_rpc_server = self.commlib_factory.getRPCService(
            callback = self.disable_callback,
            rpc_name = self.base_topic + ".disable"
        )

    def enable_callback(self, _):
        self.info["enabled"] = True
        return {"enabled": True}

    def disable_callback(self, _):
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        pass

    def stop(self):
        self.commlib_factory.stop()

    def leds_get_callback(self, _):
        return {
            "color": self._color,
            "luminosity": self._luminosity
        }

    def leds_set_callback(self, message):
        try:
            response = message

            r = response["r"] if "r" in response else 0.0
            g = response["g"] if "g" in response else 0.0
            b = response["b"] if "b" in response else 0.0
            intensity = response["luminosity"] if "luminosity" in response else 0.0

            real_color = [r, g, b, intensity]

            _values = {
                'r': r,
                'g': g,
                'b': b,
                'luminosity': intensity,
            }

            self.commlib_factory.notify_ui(
                type_ = "effector_command",
                data = {
                    "name": self.name,
                    "value": _values
                }
            )

            if self.info["mode"] == "mock":
                pass
            elif self.info["mode"] == "simulation":
                self._color["r"] = r
                self._color["g"] = g
                self._color["b"] = b
                self._luminosity = intensity

            self.logger.info("{}: New leds command: {}".format(self.name, message))

        except Exception as e:
            self.logger.error("{}: leds_set is wrongly formatted: {} - {}".format(self.name, str(e.__class__), str(e)))

        return {}

    def leds_wipe_callback(self, message):
        try:
            response = message
            r = response["r"]
            g = response["g"]
            b = response["b"]
            intensity = response["luminosity"]
            ms = response["wait_ms"]
            self._color = [r, g, b, intensity]

            self.commlib_factory.notify_ui(
                type_ = "effector_command",
                data = {
                    "name": self.name,
                    "value": {
                        'r': r,
                        'g': g,
                        'b': b,
                        'luminosity': intensity
                    }
                }
            )

            if self.info["mode"] == "mock":
                pass
            elif self.info["mode"] == "simulation":
                pass

            self.logger.info("{}: New leds wipe command: {}".format(self.name, message))

        except Exception as e:
            self.logger.error("{}: leds_wipe is wrongly formatted: {} - {}".format(self.name, str(e.__class__), str(e)))

        return {}
