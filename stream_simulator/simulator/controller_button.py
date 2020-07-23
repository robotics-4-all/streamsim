#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random

from stream_simulator import ConnParams
if ConnParams.type == "amqp":
    from commlib_py.transports.amqp import RPCServer
elif ConnParams.type == "redis":
    from commlib_py.transports.redis import RPCServer

from commlib_py.logger import Logger
from derp_me.client import DerpMeClient

class ButtonController:
    def __init__(self, info = None):
        self.logger = Logger(info["name"] + "-" + info["id"])

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]

        self.derp_client = DerpMeClient(conn_params=ConnParams.get())

        if self.info["mode"] == "real":
            from pidevices import ButtonMcp23017
            self.sensor = ButtonMcp23017(bus=self.conf["bus"],
                                         address=self.conf["address"],
                                         pin_num=self.conf["pin_num"],
                                         direction=self.conf["direction"],
                                         edge=self.conf["edge"],
                                         bounce=self.conf["bounce"],
                                         name=self.name,
                                         max_data_length=self.conf["max_data_length"])

            self.sensor.when_pressed(self.real_button_pressed)
            #### Continue implementation: https://github.com/robotics-4-all/tektrain-ros-packages/blob/master/ros_packages/robot_hw_interfaces/button_hw_interface/button_hw_interface/button_hw_interface.py

        self.memory = 100 * [0]

        self.button_rpc_server = RPCServer(conn_params=ConnParams.get(), on_request=self.button_callback, rpc_name=info["base_topic"] + "/get")

        self.enable_rpc_server = RPCServer(conn_params=ConnParams.get(), on_request=self.enable_callback, rpc_name=info["base_topic"] + "/enable")
        self.disable_rpc_server = RPCServer(conn_params=ConnParams.get(), on_request=self.disable_callback, rpc_name=info["base_topic"] + "/disable")

    def sensor_read(self):
        self.logger.info("Button {} sensor read thread started".format(self.info["id"]))
        while self.info["enabled"]:
            time.sleep(1.0 / self.info["hz"])

            if self.info["mode"] == "mock":
                val = float(random.randint(0,1))
                self.memory_write(val)
            elif self.info["mode"] == "simulation":
                val = float(random.randint(0,1))
                self.memory_write(val)
            else: # The real deal
                self.logger.warning("{} mode not implemented for {}".format(self.info["mode"], self.name))

            r = self.derp_client.lset(
                self.info["namespace"][1:] + ".variables.robot.buttons." + self.info["place"],
                [{
                    "data": val,
                    "timestamp": time.time()
                }])
            r = self.derp_client.lset(
                self.info["namespace"][1:] + ".variables.robot.buttons." + self.info["place"],
                [{
                    "data": "Tactile." + self.info["place"],
                    "timestamp": time.time()
                }])

        self.logger.info("Button {} sensor read thread stopped".format(self.info["id"]))

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
        self.logger.info("TOF {} stops reading".format(self.info["id"]))
        return {"enabled": False}

    def start(self):
        self.button_rpc_server.run()
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        if self.info["enabled"]:
            self.memory = self.info["queue_size"] * [0]
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info("Button {} reads with {} Hz".format(self.info["id"], self.info["hz"]))

    def stop(self):
        self.info["enabled"] = False
        self.button_rpc_server.stop()
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()

    def memory_write(self, data):
        del self.memory[-1]
        self.memory.insert(0, data)
        # self.logger.info("Robot {}: memory updated for {}".format(self.name, "button"))

    def button_callback(self, message, meta):
        if self.info["enabled"] is False:
            return {"data": []}

        self.logger.info("Robot {}: Button callback: {}".format(self.name, message))
        try:
            _to = message["from"] + 1
            _from = message["to"]
        except Exception as e:
            self.logger.error("{}: Malformed message for button: {} - {}".format(self.name, str(e.__class__), str(e)))
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
                "change": self.memory[-i]
            })
        return ret
