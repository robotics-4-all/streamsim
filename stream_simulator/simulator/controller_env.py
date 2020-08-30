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
    from commlib.transports.amqp import RPCService
elif ConnParams.type == "redis":
    from commlib.transports.redis import RPCService

from derp_me.client import DerpMeClient

class EnvController:
    def __init__(self, info = None):
        self.logger = Logger(info["name"] + "-" + info["id"])

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]

        self.derp_client = DerpMeClient(conn_params=ConnParams.get("redis"))

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
            ## https://github.com/robotics-4-all/tektrain-ros-packages/blob/master/ros_packages/robot_hw_interfaces/bme680_hw_interface/bme680_hw_interface/bme680_hw_interface.py

        self.memory = 100 * [0]

        self.env_rpc_server = RPCService(conn_params=ConnParams.get("redis"), on_request=self.env_callback, rpc_name=info["base_topic"] + "/get")
        self.logger.info("Created redis RPCService {}".format(
            info["base_topic"] + "/get"
        ))

        self.enable_rpc_server = RPCService(conn_params=ConnParams.get("redis"), on_request=self.enable_callback, rpc_name=info["base_topic"] + "/enable")
        self.disable_rpc_server = RPCService(conn_params=ConnParams.get("redis"), on_request=self.disable_callback, rpc_name=info["base_topic"] + "/disable")

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
                self.logger.warning("{} mode not implemented for {}".format(self.info["mode"], self.name))

            r = self.derp_client.lset(
                self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.env.temperature",
                [{"data": val["temperature"], "timestamp": time.time()}])
            r = self.derp_client.lset(
                self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.env.pressure",
                [{"data": val["pressure"], "timestamp": time.time()}])
            r = self.derp_client.lset(
                self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.env.humidity",
                [{"data": val["humidity"], "timestamp": time.time()}])
            r = self.derp_client.lset(
                self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.env.gas",
                [{"data": val["gas"], "timestamp": time.time()}])

            self.memory_write(val)

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
        self.env_rpc_server.run()
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        if self.info["enabled"]:
            self.memory = self.info["queue_size"] * [0]
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info("Env {} reads with {} Hz".format(self.info["id"], self.info["hz"]))

    def stop(self):
        self.info["enabled"] = False
        self.env_rpc_server.stop()
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()

    def memory_write(self, data):
        del self.memory[-1]
        self.memory.insert(0, data)
        # self.logger.info("Robot {}: memory updated for {}".format(self.name, "leds"))

    def env_callback(self, message, meta):
        if self.info["enabled"] is False:
            return {"data": []}

        self.logger.info("Robot {}: Env callback: {}".format(self.name, message))
        try:
            _to = message["from"] + 1
            _from = message["to"]
        except Exception as e:
            self.logger.error("{}: Malformed message for env: {} - {}".format(self.name, str(e.__class__), str(e)))
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
                "temperature": self.memory[-i]["temperature"],
                "pressure": self.memory[-i]["pressure"],
                "humidity": self.memory[-i]["humidity"],
                "gas": self.memory[-i]["gas"]
            })
        return ret
