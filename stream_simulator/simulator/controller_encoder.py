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
    from commlib.transports.amqp import RPCService, Publisher
elif ConnParams.type == "redis":
    from commlib.transports.redis import RPCService, Publisher

from derp_me.client import DerpMeClient

class EncoderController:
    def __init__(self, info = None, logger = None, derp = None):
        if logger is None:
            self.logger = Logger(info["name"] + "-" + info["id"])
        else:
            self.logger = logger

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]
        self.base_topic = info["base_topic"]
        self.streamable = info["streamable"]
        if self.streamable:
            _topic = self.base_topic + "/data"
            self.publisher = Publisher(
                conn_params=ConnParams.get("redis"),
                topic=_topic
            )
            self.logger.info(f"{Fore.GREEN}Created redis Publisher {_topic}{Style.RESET_ALL}")

        if derp is None:
            self.derp_client = DerpMeClient(conn_params=ConnParams.get("redis"))
            self.logger.warning(f"New derp-me client from {info['name']}")
        else:
            self.derp_client = derp

        if self.info["mode"] == "real":
            from pidevices import DfRobotWheelEncoderPiGPIO

            self.sensor = DfRobotWheelEncoderPiGPIO(gpio=self.conf["pin"],
                                                      pulses_per_rev = 10,
                                                      name=self.name,
                                                      max_data_length=self.conf["max_data_length"])

        self.memory = 100 * [0]

        _topic = info["base_topic"] + "/get"
        self.encoder_rpc_server = RPCService(
            conn_params=ConnParams.get("redis"),
            on_request=self.encoder_callback,
            rpc_name=_topic)
        self.logger.info(f"{Fore.GREEN}Created redis RPCService {_topic}{Style.RESET_ALL}")

        self.enable_rpc_server = RPCService(
            conn_params=ConnParams.get("redis"),
            on_request=self.enable_callback,
            rpc_name=info["base_topic"] + "/enable")
        self.disable_rpc_server = RPCService(
            conn_params=ConnParams.get("redis"),
            on_request=self.disable_callback,
            rpc_name=info["base_topic"] + "/disable")

    def sensor_read(self):
        self.logger.info("Encoder {} sensor read thread started".format(self.info["id"]))
        period = 1.0 / self.info["hz"]

        while self.info["enabled"]:
            if self.info["mode"] == "mock":
                self.data = float(random.uniform(1000,2000))
                self.memory_write(self.data)
            elif self.info["mode"] == "simulation":
                self.data = float(random.uniform(1000,2000))
                self.memory_write(self.data)
            else: # The real deal
                self.data = self.sensor.read_rpm()
                self.memory_write(self.data)

            time.sleep(period)

            if self.streamable:
                self.publisher.publish({
                    "data": self.data,
                    "timestamp": time.time()
                })

        self.logger.info("Encoder {} sensor read thread stopped".format(self.info["id"]))

    def enable_callback(self, message, meta):
        self.info["enabled"] = True
        self.info["hz"] = message["hz"]
        self.info["queue_size"] = message["queue_size"]

        self.memory = self.info["queue_size"] * [0]
        self.sensor_read_thread = threading.Thread(target = self.sensor_read)
        self.sensor_read_thread.start()
        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        self.logger.info("Encoder {} stops reading".format(self.info["id"]))
        return {"enabled": False}

    def start(self):
        self.encoder_rpc_server.run()
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        if self.info["enabled"]:
            self.memory = self.info["queue_size"] * [0]
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info("Encoder {} reads with {} Hz".format(self.info["id"], self.info["hz"]))

            if self.info["mode"] == "real":
                self.sensor.start()

    def stop(self):
        self.info["enabled"] = False

        self.encoder_rpc_server.stop()
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()

        if self.info["mode"] == "real":
            self.sensor.stop()

    def memory_write(self, data):
        del self.memory[-1]
        self.memory.insert(0, data)
        # self.logger.info("Robot {}: memory updated for {}".format(self.name, "encoder"))

    def encoder_callback(self, message, meta):
        if self.info["enabled"] is False:
            return {"data": []}

        self.logger.debug("Robot {}: encoder callback: {}".format(self.name, message))
        try:
            _to = message["from"] + 1
            _from = message["to"]
        except Exception as e:
            self.logger.error("{}: Malformed message for encoder: {} - {}".format(self.name, str(e.__class__), str(e)))
            return []
        ret = {"data": []}
        for i in range(_from, _to): # 0 to -1
            timestamp = time.time()
            secs = int(timestamp)
            nanosecs = int((timestamp-secs) * 10**(9))
            ret["data"].append({
                "header":{
                    "stamp":{
                        "sec": secs,
                        "nanosec": nanosecs
                    }
                },
                "rpm": self.memory[-i]
            })
        return ret
