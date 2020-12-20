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

class EncoderController:
    def __init__(self, info = None, logger = None):
        if logger is None:
            self.logger = Logger(info["name"])
        else:
            self.logger = logger

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]
        self.base_topic = info["base_topic"]
        self.derp_data_key = info["base_topic"] + ".raw"

        self.publisher = CommlibFactory.getPublisher(
            broker = "redis",
            topic = self.base_topic + ".data"
        )

        if self.info["mode"] == "real":
            from pidevices import DfRobotWheelEncoderPiGPIO

            self.sensor = DfRobotWheelEncoderPiGPIO(gpio=self.conf["pin"],
                                                      pulses_per_rev = 10,
                                                      name=self.name,
                                                      max_data_length=self.conf["max_data_length"])

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

    def sensor_read(self):
        self.logger.info("Encoder {} sensor read thread started".format(self.info["id"]))
        period = 1.0 / self.info["hz"]

        while self.info["enabled"]:
            if self.info["mode"] == "mock":
                self.data = float(random.uniform(1000,2000))
            elif self.info["mode"] == "simulation":
                self.data = float(random.uniform(1000,2000))
            else: # The real deal
                self.data = self.sensor.read_rpm()

            time.sleep(period)

            # Publishing value:
            self.publisher.publish({
                "rpm": self.data,
                "timestamp": time.time()
            })

            # Storing value:
            r = CommlibFactory.derp_client.lset(
                self.derp_data_key,
                [{
                    "rpm": self.data,
                    "timestamp": time.time()
                }]
            )

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

        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()

        if self.info["mode"] == "real":
            self.sensor.stop()
