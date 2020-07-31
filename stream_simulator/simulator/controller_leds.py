#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random

from commlib.logger import Logger

from .conn_params import ConnParams
if ConnParams.type == "amqp":
    from commlib.transports.amqp import RPCService, Subscriber, Publisher
elif ConnParams.type == "redis":
    from commlib.transports.redis import RPCService, Subscriber, Publisher

class LedsController:
    def __init__(self, info = None):
        self.logger = Logger(info["name"] + "-" + info["id"])

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]

        if self.info["mode"] == "real":
            pass
            ## https://github.com/robotics-4-all/tektrain-ros-packages/blob/master/ros_packages/robot_hw_interfaces/led_strip_hw_interface/led_strip_hw_interface/led_strip_hw_interface.py

        self.memory = 100 * [0]

        self.leds_wipe_pub = Publisher(conn_params=ConnParams.get(), topic=info["base_topic"] + "/leds_wipe/pub")

        self.leds_set_sub = Subscriber(conn_params=ConnParams.get(), topic =info["base_topic"] + "/leds/set", on_message = self.leds_set_callback)

        self.leds_wipe_server = RPCService(conn_params=ConnParams.get(), on_request=self.leds_wipe_callback, rpc_name=info["base_topic"] + "/leds_wipe/set")

        self.leds_get_server = RPCService(conn_params=ConnParams.get(), on_request=self.leds_get_callback, rpc_name=info["base_topic"] + "/get")

        self.enable_rpc_server = RPCService(conn_params=ConnParams.get(), on_request=self.enable_callback, rpc_name=info["base_topic"] + "/enable")
        self.disable_rpc_server = RPCService(conn_params=ConnParams.get(), on_request=self.disable_callback, rpc_name=info["base_topic"] + "/disable")

    def enable_callback(self, message, meta):
        self.info["enabled"] = True
        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        self.leds_set_sub.run()
        self.leds_wipe_server.run()
        self.leds_get_server.run()

        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

    def stop(self):
        self.leds_set_sub.stop()
        self.leds_wipe_server.stop()
        self.leds_get_server.stop()

        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()

    def memory_write(self, data):
        del self.memory[-1]
        self.memory.insert(0, data)
        self.logger.info("Robot {}: memory updated for {}".format(self.name, "leds"))

    def leds_get_callback(self, message, meta):
        self.logger.info("Robot {}: Leds get callback: {}".format(self.name, message))
        try:
            _to = message["from"] + 1
            _from = message["to"]
        except Exception as e:
            self.logger.error("{}: Malformed message for leds get: {} - {}".format(self.name, str(e.__class__), str(e)))
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
                "leds": [
                    {
                        "r": self.memory[-i][0],
                        "g": self.memory[-i][1],
                        "b": self.memory[-i][2],
                        "intensity": self.memory[-i][3]
                    }
                ]
            })
        return ret

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
                self.memory_write(self._color)
            elif self.info["mode"] == "simulation":
                self.memory_write(self._color)
                self.leds_wipe_pub.publish({"r": r, "g": g, "b": b})
            else: # The real deal
                self.logger.warning("{} mode not implemented for {}".format(self.info["mode"], self.name))

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
                self.memory_write(self._color)
            elif self.info["mode"] == "simulation":
                self.memory_write(self._color)
                self.leds_wipe_pub.publish({"r": r, "g": g, "b": b})
            else: # The real deal
                self.logger.warning("{} mode not implemented for {}".format(self.info["mode"], self.name))

            self.logger.info("{}: New leds wipe command: {}".format(self.name, message))

        except Exception as e:
            self.logger.error("{}: leds_wipe is wrongly formatted: {} - {}".format(self.name, str(e.__class__), str(e)))

        return {}
