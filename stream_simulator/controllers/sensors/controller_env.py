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

from stream_simulator.connectivity import ConnParams
if ConnParams.type == "amqp":
    from commlib.transports.amqp import RPCService, Publisher
elif ConnParams.type == "redis":
    from commlib.transports.redis import RPCService, Publisher

from derp_me.client import DerpMeClient

class EnvController:
    def __init__(self, info = None, logger = None, derp = None):
        if logger is None:
            self.logger = Logger(info["name"])
        else:
            self.logger = logger

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]
        self.base_topic = info["base_topic"]
        self.derp_data_key = info["base_topic"] + ".raw"

        _topic = self.base_topic + ".data"
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
            from pidevices import BME680
            self.sensor = BME680(self.conf["bus"], self.conf["slave"],
                                 t_oversample=self.conf["t_over"],
                                 h_oversample=self.conf["h_over"],
                                 p_oversample=self.conf["p_over"],
                                 iir_coef=self.conf["iir_coef"],
                                 gas_status=self.conf["g_status"],
                                 name=self.name,
                                 max_data_length=self.conf["max_data_length"])
            self.sensor.set_heating_temp([0], [320])
            self.sensor.set_heating_time([0], [100])
            self.sensor.set_nb_conv(0)

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

    def sensor_read(self):
        self.logger.info("Env {} sensor read thread started".format(self.info["id"]))
        while self.info["enabled"]:
            time.sleep(1.0 / self.info["hz"])

            val = {
                "temperature": 0,
                "pressure": 0,
                "humidity": 0,
                "gas": 0
            }
            if self.info["mode"] == "mock":
                val["temperature"] = float(random.uniform(30, 10))
                val["pressure"] = float(random.uniform(30, 10))
                val["humidity"] = float(random.uniform(30, 10))
                val["gas"] = float(random.uniform(30, 10))

            elif self.info["mode"] == "simulation":
                val["temperature"] = self.info["temperature"] + \
                    random.uniform(-3, 3)
                val["pressure"] = self.info["pressure"] + random.uniform(-3, 3)
                val["humidity"] = self.info["humidity"] + random.uniform(-3, 3)
                val["gas"] = self.info["gas"] + random.uniform(-3, 3)
            else: # The real deal
                data = self.sensor.read()

                val["temperature"] = data.temp
                val["pressure"] = data.pres
                val["humidity"] = data.hum
                val["gas"] = data.gas

            # Publishing value:
            self.publisher.publish({
                "data": val,
                "timestamp": time.time()
            })

            # Storing value:
            r = self.derp_client.lset(
                self.derp_data_key,
                [{
                    "data": val,
                    "timestamp": time.time()
                }]
            )

        self.logger.info("Env {} sensor read thread stopped".format(self.info["id"]))

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
        self.logger.info("Env {} stops reading".format(self.info["id"]))
        return {"enabled": False}

    def start(self):
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        if self.info["enabled"]:
            self.memory = self.info["queue_size"] * [0]
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info("Env {} reads with {} Hz".format(self.info["id"], self.info["hz"]))

    def stop(self):
        self.info["enabled"] = False
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()
