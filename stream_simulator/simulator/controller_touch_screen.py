#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random

from commlib.logger import Logger

from stream_simulator import ConnParams
if ConnParams.type == "amqp":
    from commlib.transports.amqp import RPCService
elif ConnParams.type == "redis":
    from commlib.transports.redis import RPCService

class TouchScreenController:
    def __init__(self, info = None):
        self.logger = Logger(info["name"] + "-" + info["id"])

        self.info = info
        self.name = info["name"]

        self.memory = 100 * [0]

        self.show_image_rpc_server = RPCService(conn_params=ConnParams.get(), on_request=self.show_image_callback, rpc_name=info["base_topic"] + "/show_image")

        self.enable_rpc_server = RPCService(conn_params=ConnParams.get(), on_request=self.enable_callback, rpc_name=info["base_topic"] + "/enable")
        self.disable_rpc_server = RPCService(conn_params=ConnParams.get(), on_request=self.disable_callback, rpc_name=info["base_topic"] + "/disable")

    def enable_callback(self, message, meta):
        self.info["enabled"] = True
        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        self.show_image_rpc_server.run()
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

    def stop(self):
        self.show_image_rpc_server.stop()
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()

    def memory_write(self, data):
        del self.memory[-1]
        self.memory.insert(0, data)

    def show_image_callback(self, message, meta):
        self.logger.info("Robot {}: Show image callback".format(self.name))
        ret = {
            "reaction_time": -1,
            "selected": -1
        }
        if self.info["enabled"] is False:
            return ret

        try:
            image_width = message["image_width"]
            image_height = message["image_height"]
            file_flag = message["file_flag"]
            source = message["source"]
            time_enabled = message["time_enabled"]
            touch_enabled = message["touch_enabled"]
            color_rgb = message["color_rgb"]
            options = message["options"]
            multiple_options = message["multiple_options"]
            time_window = message["time_window"]
            text = message["text"]
            show_image = message["show_image"]
            show_color = message["show_color"]
            show_video = message["show_video"]
            show_options = message["show_options"]
        except Exception as e:
            self.logger.error("{}: Malformed message for show image: {} - {}".format(self.name, str(e.__class__), str(e)))
            return []

        if self.info["mode"] == "mock":
            ret["reaction_time"] = random.uniform(0,200) / 200.0
            if len(options) > 0:
                ret["selected"] = options[0]
            else:
                ret["selected"] = ""

        elif self.info["mode"] == "simulation":
            ret["reaction_time"] = random.uniform(0,200) / 200.0
            if len(options) > 0:
                ret["selected"] = options[0]
            else:
                ret["selected"] = ""
        else: # The real deal
            self.logger.warning("{} mode not implemented for {}".format(self.info["mode"], self.name))

        return ret
