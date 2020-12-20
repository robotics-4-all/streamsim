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

class CytronLFController:
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
            from pidevices import CytronLfLSS05Mcp23017

            self.lf_sensor = CytronLfLSS05Mcp23017(bus=self.conf["bus"],
                                                address=self.conf["address"],
                                                mode=self.conf["mode"],
                                                so_1=self.conf["so_1"],
                                                so_2=self.conf["so_2"],
                                                so_3=self.conf["so_3"],
                                                so_4=self.conf["so_4"],
                                                so_5=self.conf["so_5"],
                                                cal=self.conf["cal"],
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
        self.logger.info("Cytron-LF {} sensor read thread started".format(self.info["id"]))

        while self.info["enabled"]:
            time.sleep(1.0 / self.info["hz"])

            val = {}

            if self.info["mode"] == "mock":
                val = {
                    "so_1": 1 if (random.uniform(0,1) > 0.5) else 0,
                    "so_2": 1 if (random.uniform(0,1) > 0.5) else 0,
                    "so_3": 1 if (random.uniform(0,1) > 0.5) else 0,
                    "so_4": 1 if (random.uniform(0,1) > 0.5) else 0,
                    "so_5": 1 if (random.uniform(0,1) > 0.5) else 0
                }

            elif self.info["mode"] == "simulation":
                try:
                    val = {
                        "so_1": 1 if (random.uniform(0,1) > 0.5) else 0,
                        "so_2": 1 if (random.uniform(0,1) > 0.5) else 0,
                        "so_3": 1 if (random.uniform(0,1) > 0.5) else 0,
                        "so_4": 1 if (random.uniform(0,1) > 0.5) else 0,
                        "so_5": 1 if (random.uniform(0,1) > 0.5) else 0
                    }
                except:
                    self.logger.warning("Pose not got yet..")
            else: # The real deal
                data = self.lf_sensor.read()

                val = data._asdict()

            # Publishing value:
            self.publisher.publish({
                'so_1': val['so_1'],
                'so_2': val['so_2'],
                'so_3': val['so_3'],
                'so_4': val['so_4'],
                'so_5': val['so_5']
            })

            # Storing value:
            r = CommlibFactory.derp_client.lset(
                self.derp_data_key,
                [{
                    "data": {
                        'so_1': val['so_1'],
                        'so_2': val['so_2'],
                        'so_3': val['so_3'],
                        'so_4': val['so_4'],
                        'so_5': val['so_5']
                    },
                    "timestamp": time.time()
                }]
            )

        self.logger.info("Cytron-LF {} sensor read thread stopped".format(self.info["id"]))

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
        self.logger.info("Cytron-LF {} stops reading".format(self.info["id"]))
        return {"enabled": False}

    def start(self):
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        if self.info["mode"] == "real":
            self.lf_sensor.calibrate()

        if self.info["enabled"]:
            self.memory = self.info["queue_size"] * [0]
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info("Cytron Line Follower {} reads with {} Hz".format(self.info["id"], self.info["hz"]))

    def stop(self):
        self.info["enabled"] = False
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()

        self.sensor_read_thread.join()

        # if we are on "real" mode and the controller has started then Terminate it
        if self.info["mode"] == "real":
            self.lf_sensor.stop()
