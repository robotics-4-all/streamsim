#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random

from stream_simulator import Logger

from stream_simulator import AmqpParams
from commlib_py.transports.amqp import RPCServer

class TofController:
    def __init__(self, name = "robot", logger = None):
        self.logger = logger
        self.name = name

        self.memory = 100 * [0]

        self.tof_rpc_server = RPCServer(conn_params=AmqpParams.get(), on_request=self.tof_callback, rpc_name=name + ":tof")

    def start(self):
        self.tof_rpc_server.run()
        self.logger.info("Robot {}: tof_rpc_server started".format(self.name))

    def memory_write(self, data):
        del self.memory[-1]
        self.memory.insert(0, data)
        self.logger.info("Robot {}: memory updated for {}".format(self.name, "tof"))

    def tof_callback(self, message, meta):
        self.logger.info("Robot {}: tof callback: {}".format(self.name, message))
        try:
            _to = message["from"] + 1
            _from = message["to"]
        except Exception as e:
            self.logger.error("{}: Malformed message for tof: {} - {}".format(self.name, str(e.__class__), str(e)))
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
                "distance": float(random.uniform(30, 10))
            })
        return ret
