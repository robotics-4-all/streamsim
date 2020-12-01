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

from .conn_params import ConnParams
if ConnParams.type == "amqp":
    from commlib.transports.amqp import RPCService, Subscriber
elif ConnParams.type == "redis":
    from commlib.transports.redis import RPCService, Subscriber

class PanTiltController:
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

        # create object
        if self.info["mode"] == "real":
            from pidevices import PCA9685
            self.pan_tilt = PCA9685(bus=self.conf["bus"],
                                    frequency=self.conf["frequency"],
                                    max_data_length=self.conf["max_data_length"])
            self.yaw_channel = 0
            self.pitch_channel = 1

        _topic = info["base_topic"] + ".set"
        self.pan_tilt_set_sub = Subscriber(
            conn_params=ConnParams.get("redis"),
            topic = _topic,
            on_message = self.pan_tilt_set_callback)
        self.logger.info(f"{Fore.GREEN}Created redis Subscriber {_topic}{Style.RESET_ALL}")

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
        self.pan_tilt_set_sub.run()

        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        if self.info["mode"] == "real":
            self.pan_tilt.start()

    def stop(self):
        self.pan_tilt_set_sub.stop()

        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()

        # stop servos
        if self.info["mode"] == "real":
            self.pan_tilt.stop()

    def pan_tilt_set_callback(self, message, meta):
        try:

            response = message
            self._yaw = response['yaw']
            self._pitch = response['pitch']

            # Storing value:
            r = self.derp_client.lset(
                self.derp_data_key,
                [{
                    "data": {
                        "yaw": self._yaw,
                        "pitch": self._pitch
                    },
                    "timestamp": time.time()
                }]
            )

            if self.info["mode"] == "mock":
                pass
            elif self.info["mode"] == "simulation":
                pass
            else: # The real deal
                #self.logger.warning("{} mode not implemented for {}".format(self.info["mode"], self.name))
                self.pan_tilt.write(self.yaw_channel, self._yaw, degrees=True)
                self.pan_tilt.write(self.pitch_channel, self._pitch, degrees=True)

            self.logger.info("{}: New pan tilt command: {}, {}".format(self.name, self._yaw, self._pitch))
        except Exception as e:
            self.logger.error("{}: pan_tilt is wrongly formatted: {} - {}".format(self.name, str(e.__class__), str(e)))
