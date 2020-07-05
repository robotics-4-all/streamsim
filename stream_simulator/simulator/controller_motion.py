#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random

from stream_simulator import Logger, Subscriber, RpcServer

class MotionController:
    def __init__(self, name = "robot", logger = None):
        self.logger = logger
        self.name = name
        self._linear = 0
        self._angular = 0

        self.memory = 100 * [0]

        self.vel_sub = Subscriber(topic = name + ":cmd_vel", func = self.cmd_vel)
        self.motion_get_server = RpcServer(topic = name + ":motion:memory", func = self.motion_get_callback)

    def start(self):
        self.vel_sub.start()
        self.logger.info("Robot {}: vel_sub started".format(self.name))

        self.motion_get_server.start()
        self.logger.info("Robot {}: motion_get_server started".format(self.name))

    def memory_write(self, data):
        del self.memory[-1]
        self.memory.insert(0, data)
        self.logger.info("Robot {}: memory updated for {}".format(self.name, "leds"))

    def cmd_vel(self, message):
        try:
            response = json.loads(message['data'])
            self._linear = response['linear']
            self._angular = response['angular']
            self.memory_write([self._linear, self._angular])
            self.logger.info("{}: New motion command: {}, {}".format(self.name, self._linear, self._angular))
        except Exception as e:
            self.logger.error("{}: cmd_vel is wrongly formatted: {} - {}".format(self.name, str(e.__class__), str(e)))

    def motion_get_callback(self, message):
        self.logger.info("Robot {}: Motion get callback: {}".format(self.name, message))
        try:
            _to = message["from"] + 1
            _from = message["to"]
        except Exception as e:
            self.logger.error("{}: Malformed message for motion get: {} - {}".format(self.name, str(e.__class__), str(e)))
            return []
        ret = []
        for i in range(_from, _to): # 0 to -1
            timestamp = time.time()
            secs = int(timestamp)
            nanosecs = int((timestamp-secs) * 10**(9))
            ret.append({
                "header":{
                    "stamp":{
                        "sec": secs,
                        "nanosec": nanosecs
                    }
                },
                "linear": self.memory[-i][0],
                "angular": self.memory[-i][1],
                "deviceId": 0
            })
        return ret
