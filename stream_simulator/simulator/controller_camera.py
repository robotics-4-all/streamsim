#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random
import cv2
import os
import base64

from commlib_py.logger import Logger

from stream_simulator import ConnParams
if ConnParams.type == "amqp":
    from commlib_py.transports.amqp import RPCServer
elif ConnParams.type == "redis":
    from commlib_py.transports.redis import RPCServer

class CameraController:
    def __init__(self, info = None):
        self.logger = Logger(info["name"] + "-" + info["id"])

        self.info = info
        self.name = info["name"]

        self.memory = 100 * [0]

        self.get_image_rpc_server = RPCServer(conn_params=ConnParams.get(), on_request=self.get_image_callback, rpc_name=info["base_topic"] + "/get")

        self.enable_rpc_server = RPCServer(conn_params=ConnParams.get(), on_request=self.enable_callback, rpc_name=info["base_topic"] + "/enable")
        self.disable_rpc_server = RPCServer(conn_params=ConnParams.get(), on_request=self.disable_callback, rpc_name=info["base_topic"] + "/disable")

    def enable_callback(self, message, meta):
        self.info["enabled"] = True
        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        self.get_image_rpc_server.run()
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

    def memory_write(self, data):
        del self.memory[-1]
        self.memory.insert(0, data)
        self.logger.info("Robot {}: memory updated for {}".format(self.name, "ir"))

    def get_image_callback(self, message, meta):
        self.logger.info("Robot {}: get image callback: {}".format(self.name, message))
        try:
            width = message["width"]
            height = message["height"]
        except Exception as e:
            self.logger.error("{}: Malformed message for image get: {} - {}".format(self.name, str(e.__class__), str(e)))
            return {}

        if self.info["mode"] == "mock":
            dirname = os.path.dirname(__file__)
            im = cv2.imread(dirname + '/resources/face.jpg')
            im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
            image = cv2.resize(im, dsize=(width, height))
            data = [int(d) for row in image for c in row for d in c]
            data = base64.b64encode(bytes(data)).decode("ascii")
        elif self.info["mode"] == "simulation":
            self.logger.warning("{} mode not implemented for {}".format(self.info["mode"], self.name))
            data = ""
        else: # The real deal
            self.logger.warning("{} mode not implemented for {}".format(self.info["mode"], self.name))
            data = ""


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
            "format": "RGB",
            "per_rows": True,
            "width": width,
            "height": height,
            "image": data
        }
        return ret
