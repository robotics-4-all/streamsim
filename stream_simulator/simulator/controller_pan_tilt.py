#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random

from stream_simulator import Logger

class PanTiltController:
    def __init__(self, name = "robot", logger = None):
        self.logger = logger
        self.name = name

        self.memory = 100 * [0]

    def memory_write(self, data):
        del self.memory[-1]
        self.memory.insert(0, data)
        self.logger.info("Robot {}: memory updated for {}".format(self.name, "pan_tilt"))

    def pan_tilt_get_callback(self, message):
        self.logger.info("Robot {}: Pan tilt get callback: {}".format(self.name, message))
        try:
            _to = message["from"] + 1
            _from = message["to"]
        except Exception as e:
            self.logger.error("{}: Malformed message for pan tilt get: {} - {}".format(self.name, str(e.__class__), str(e)))
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
                "yaw": self.memory[-i][0],
                "pitch": self.memory[-i][1],
                "deviceId": 0
            })
        return ret

    def pan_tilt_set_callback(self, message):
        try:

            response = json.loads(message['data'])
            self._yaw = response['yaw']
            self._pitch = response['pitch']
            self.memory_write([self._yaw, self._pitch])
            self.logger.info("{}: New pan tilt command: {}, {}".format(self.name, self._yaw, self._pitch))
        except Exception as e:
            self.logger.error("{}: pan_tilt is wrongly formatted: {} - {}".format(self.name, str(e.__class__), str(e)))
