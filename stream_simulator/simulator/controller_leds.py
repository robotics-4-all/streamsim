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
from derp_me.client import DerpMeClient

from .conn_params import ConnParams
if ConnParams.type == "amqp":
    from commlib.transports.amqp import RPCService, Subscriber, Publisher
elif ConnParams.type == "redis":
    from commlib.transports.redis import RPCService, Subscriber, Publisher

class LedsController:
    def __init__(self, info = None, logger = None, derp = None):
        if logger is None:
            self.logger = Logger(info["name"] + "-" + info["id"])
        else:
            self.logger = logger

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]
        self.base_topic = info["base_topic"]
        self.derp_data_key = info["base_topic"] + ".raw"

        if derp is None:
            self.derp_client = DerpMeClient(conn_params=ConnParams.get("redis"))
            self.logger.warning(f"New derp-me client from {info['name']}")
        else:
            self.derp_client = derp

        if self.info["mode"] == "real":
            from pidevices import LedController
            self.led_strip = LedController(led_count=self.conf["led_count"],
                                            led_pin=self.conf["led_pin"],
                                            led_freq_hz=self.conf["led_freq_hz"],
                                            led_brightness=self.conf["led_brightness"],
                                            led_channel=self.conf["led_channel"])

        # These are to inform amqp###################
        _topic = self.info['device_name'] + ".leds"
        self.leds_pub = Publisher(
            conn_params=ConnParams.get("redis"),
            topic=_topic)
        self.logger.info(f"{Fore.GREEN}Created redis Publisher {_topic}{Style.RESET_ALL}")

        _topic = self.info['device_name'] + ".leds.wipe"
        self.leds_wipe_pub = Publisher(
            conn_params=ConnParams.get("redis"),
            topic=_topic)
        self.logger.info(f"{Fore.GREEN}Created redis Publisher {_topic}{Style.RESET_ALL}")
        #############################################

        _topic = info["base_topic"] + ".set"
        self.leds_set_sub = Subscriber(
            conn_params=ConnParams.get("redis"),
            topic=_topic,
            on_message = self.leds_set_callback)
        self.logger.info(f"{Fore.GREEN}Created redis Subscriber {_topic}{Style.RESET_ALL}")

        _topic = info["base_topic"] + ".wipe"
        self.leds_wipe_server = RPCService(
            conn_params=ConnParams.get("redis"),
            on_request=self.leds_wipe_callback,
            rpc_name=_topic)
        self.logger.info(f"{Fore.GREEN}Created redis RPCService {_topic}{Style.RESET_ALL}")

        _topic = info["base_topic"] + ".enable"
        self.enable_rpc_server = RPCService(
            conn_params=ConnParams.get("redis"),
            on_request=self.enable_callback,
            rpc_name=_topic)
        self.logger.info(f"{Fore.GREEN}Created redis RPCService {_topic}{Style.RESET_ALL}")

        _topic = info["base_topic"] + ".disable"
        self.disable_rpc_server = RPCService(
            conn_params=ConnParams.get("redis"),
            on_request=self.disable_callback,
            rpc_name=_topic)
        self.logger.info(f"{Fore.GREEN}Created redis RPCService {_topic}{Style.RESET_ALL}")

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
            r = self.derp_client.lset(
                self.derp_data_key,
                [{
                    "data": {"r": r, "g": g, "b": b, "intensity": intensity},
                    "type": "simple",
                    "timestamp": time.time()
                }]
            )

        except Exception as e:
            self.logger.error("{}: leds_set is wrongly formatted: {} - {}".format(self.name, str(e.__class__), str(e)))

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
            r = self.derp_client.lset(
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
