#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random
import base64

from commlib_py.logger import Logger

from stream_simulator import ConnParams
if ConnParams.type == "amqp":
    from commlib_py.transports.amqp import ActionServer, RPCServer
elif ConnParams.type == "redis":
    from commlib_py.transports.redis import ActionServer, RPCServer

class MicrophoneController:
    def __init__(self, info = None):
        self.logger = Logger(info["name"] + "-" + info["id"])

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]

        if self.info["mode"] == "real":
            from pidevices import Microphone
            self.sensor = Microphone(dev_name=self.conf["dev_name"],
                                     channels=self.conf["channels"],
                                     name=self.name,
                                     max_data_length=self.conf["max_data_length"])
            ## https://github.com/robotics-4-all/tektrain-ros-packages/blob/master/ros_packages/robot_hw_interfaces/microphone_hw_interface/microphone_hw_interface/microphone_hw_interface.py

        self.memory = 100 * [0]

        self.record_action_server = ActionServer(conn_params=ConnParams.get(), on_goal=self.on_goal, action_name=info["base_topic"] + "/record")

        self.enable_rpc_server = RPCServer(conn_params=ConnParams.get(), on_request=self.enable_callback, rpc_name=info["base_topic"] + "/enable")
        self.disable_rpc_server = RPCServer(conn_params=ConnParams.get(), on_request=self.disable_callback, rpc_name=info["base_topic"] + "/disable")

    def on_goal(self, goalh):
        self.logger.info("{} recording started".format(self.name))
        if self.info["enabled"] == False:
            return {}

        try:
            duration = goalh.data["duration"]
        except Exception as e:
            self.logger.error("{} goal had no duration as parameter".format(self.name))

        timestamp = time.time()
        secs = int(timestamp)
        nanosecs = int((timestamp-secs) * 10**(9))
        ret = {
            "header":{
                "stamp":{
                    "sec": secs,
                    "nanosec": nanosecs
                }
            },
            "record": "",
            "volume": 0
        }
        if self.info["mode"] == "mock":
            now = time.time()
            while time.time() - now < duration:
                self.logger.info("Recording...")
                if goalh.cancel_event.is_set():
                    self.logger.info("Cancel got")
                    return ret
                time.sleep(0.1)

            ret["record"] = base64.b64encode(b'0x55').decode("ascii")
            ret["volume"] = 100

        elif self.info["mode"] == "simulation":
            pass
        else: # The real deal
            self.sensor.async_read(secs = duration, volume = 100, framerate = self.conf["framerate"])
            now = time.time()
            while time.time() - now < duration + 0.2:
                time.sleep(0.1)
            ret["record"] = base64.b64encode(self.sensor.record).decode("ascii")

        self.logger.info("{} recording finished".format(self.name))
        return ret

    def enable_callback(self, message, meta):
        self.info["enabled"] = True
        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        self.record_action_server.run()
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

    def memory_write(self, data):
        del self.memory[-1]
        self.memory.insert(0, data)
