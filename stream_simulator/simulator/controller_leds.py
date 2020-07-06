#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random

from stream_simulator import Logger

from stream_simulator import ConnParams
if ConnParams.type == "amqp":
    from commlib_py.transports.amqp import RPCServer, Subscriber, Publisher
elif ConnParams.type == "redis":
    from commlib_py.transports.redis import RPCServer, Subscriber, Publisher

class LedsController:
    def __init__(self, name = "robot", logger = None):
        self.logger = logger
        self.name = name

        self.memory = 100 * [0]

        self.leds_wipe_pub = Publisher(conn_params=ConnParams.get(), topic= name + ":leds_wipe")

        self.leds_set_sub = Subscriber(conn_params=ConnParams.get(), topic = name + ":leds", on_message = self.leds_set_callback)

        self.leds_wipe_server = RPCServer(conn_params=ConnParams.get(), on_request=self.leds_wipe_callback, rpc_name=name + ":leds_wipe")

        self.leds_get_server = RPCServer(conn_params=ConnParams.get(), on_request=self.leds_get_callback, rpc_name=name + ":leds:memory")

    def start(self):
        self.leds_set_sub.run()
        self.logger.info("Robot {}: leds_set_sub started".format(self.name))

        self.leds_wipe_server.run()
        self.logger.info("Robot {}: leds_wipe_server started".format(self.name))

        self.leds_get_server.run()
        self.logger.info("Robot {}: leds_get_server started".format(self.name))

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
            self.memory_write(self._color)
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
            self.memory_write(self._color)
            self.logger.info("{}: New leds wipe command: {}".format(self.name, message))

            self.leds_wipe_pub.publish({"r": r, "g": g, "b": b})
        except Exception as e:
            self.logger.error("{}: leds_wipe is wrongly formatted: {} - {}".format(self.name, str(e.__class__), str(e)))

        return {}
