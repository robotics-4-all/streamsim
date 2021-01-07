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

class LedsController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = Logger(conf["name"])
        else:
            self.logger = package["logger"]

        super(self.__class__, self).__init__()
        id = "d_" + str(BaseThing.id)
        name = "led_" + str(id)
        if 'name' in conf:
            name = conf['name']
            id = name

        info = {
            "type": "LED",
            "brand": "neopx",
            "base_topic": package["name"] + ".actuator.visual.leds.neopx." + str(id),
            "name": name,
            "place": conf["place"],
            "id": id,
            "enabled": True,
            "orientation": conf["orientation"],
            "queue_size": 0,
            "mode": package["mode"],
            "speak_mode": package["speak_mode"],
            "namespace": package["namespace"],
            "sensor_configuration": conf["sensor_configuration"],
            "device_name": package["device_name"],
            "endpoints":{
                "enable": "rpc",
                "disable": "rpc",
                "leds.set": "subscriber",
                "leds_wipe.set": "rpc"
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
            "subtype": "leds",
            "pose": conf["pose"],
            "base_topic": info['base_topic'],
            "name": self.name
        }
        tf_package['host'] = package['device_name']
        tf_package['host_type'] = 'robot'
        if 'host' in conf:
            tf_package['host'] = conf['host']
            tf_package['host_type'] = 'pan_tilt'
        package["tf_declare"].call(tf_package)

        if self.info["mode"] == "real":
            from pidevices import LedController
            self.led_strip = LedController(led_count=self.conf["led_count"],
                                            led_pin=self.conf["led_pin"],
                                            led_freq_hz=self.conf["led_freq_hz"],
                                            led_brightness=self.conf["led_brightness"],
                                            led_channel=self.conf["led_channel"])

        # These are to inform amqp###################
        self.leds_pub = CommlibFactory.getPublisher(
            broker = "redis",
            topic = self.info['device_name'] + ".leds"
        )
        self.leds_wipe_pub = CommlibFactory.getPublisher(
            broker = "redis",
            topic = self.info['device_name'] + ".leds.wipe"
        )
        #############################################

        self.leds_set_sub = CommlibFactory.getSubscriber(
            broker = "redis",
            topic = info["base_topic"] + ".set",
            callback = self.leds_set_callback
        )
        self.leds_wipe_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.leds_wipe_callback,
            rpc_name = info["base_topic"] + ".wipe"
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
        self.leds_set_sub.run()
        self.leds_wipe_server.run()
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

    def stop(self):
        self.leds_set_sub.stop()
        self.leds_wipe_server.stop()
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()

    def leds_set_callback(self, message, meta):
        try:
            response = message
            id = response["id"]
            r = response["r"]
            g = response["g"]
            b = response["b"]
            intensity = response["intensity"]
            self._color = [r, g, b, intensity]

            if self.info["mode"] == "mock":
                pass
            elif self.info["mode"] == "simulation":
                pass
            else: # The real deal
                self.led_strip.write([self._color], wipe = False)

            self.leds_pub.publish({"r": r, "g": g, "b": b})

            # Storing value:
            r = CommlibFactory.derp_client.lset(
                self.derp_data_key,
                [{
                    "data": {"r": r, "g": g, "b": b, "intensity": intensity},
                    "type": "simple",
                    "timestamp": time.time()
                }]
            )

            self.logger.info("{}: New leds command: {}".format(self.name, message))

        except Exception as e:
            self.logger.error("{}: leds_set is wrongly formatted: {} - {}".format(self.name, str(e.__class__), str(e)))

        return {}

    def leds_wipe_callback(self, message, meta):
        try:
            response = message
            r = response["r"]
            g = response["g"]
            b = response["b"]
            intensity = response["brightness"]
            ms = response["wait_ms"]
            self._color = [r, g, b, intensity]

            if self.info["mode"] == "mock":
                pass
            elif self.info["mode"] == "simulation":
                pass
            else: # The real deal
                self.led_strip.write([self._color], wipe=True)

            self.leds_wipe_pub.publish({"r": r, "g": g, "b": b})

            # Storing value:
            r = CommlibFactory.derp_client.lset(
                self.derp_data_key,
                [{
                    "data": {"r": r, "g": g, "b": b, "intensity": intensity},
                    "type": "wipe",
                    "timestamp": time.time()
                }]
            )

            self.logger.info("{}: New leds wipe command: {}".format(self.name, message))

        except Exception as e:
            self.logger.error("{}: leds_wipe is wrongly formatted: {} - {}".format(self.name, str(e.__class__), str(e)))

        return {}
