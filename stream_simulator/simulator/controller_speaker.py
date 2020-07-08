#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random
import base64

from stream_simulator import ConnParams
if ConnParams.type == "amqp":
    from commlib_py.transports.amqp import ActionServer, RPCServer
elif ConnParams.type == "redis":
    from commlib_py.transports.redis import ActionServer, RPCServer

class SpeakerController:
    def __init__(self, info = None, logger = None):
        self.logger = logger

        self.info = info
        self.name = info["name"]

        self.memory = 100 * [0]

        self.play_action_server = ActionServer(conn_params=ConnParams.get(), on_goal=self.on_goal_play, action_name=info["base_topic"] + "/play")
        self.speak_action_server = ActionServer(conn_params=ConnParams.get(), on_goal=self.on_goal_speak, action_name=info["base_topic"] + "/speak")

        self.enable_rpc_server = RPCServer(conn_params=ConnParams.get(), on_request=self.enable_callback, rpc_name=info["base_topic"] + "/enable")
        self.disable_rpc_server = RPCServer(conn_params=ConnParams.get(), on_request=self.disable_callback, rpc_name=info["base_topic"] + "/disable")

    def on_goal_speak(self, goalh):
        self.logger.info("{} speak started".format(self.name))
        if self.info["enabled"] == False:
            return {}

        try:
            texts = goalh.data["text"]
            volume = goalh.data["volume"]
            language = goalh.data["language"]
        except Exception as e:
            self.logger.error("{} wrong parameters: {}".format(self.name, ))

        timestamp = time.time()
        secs = int(timestamp)
        nanosecs = int((timestamp-secs) * 10**(9))
        ret = {
            "header":{
                "stamp":{
                    "sec": secs,
                    "nanosec": nanosecs
                }
            }
        }
        if self.info["mode"] == "mock":
            now = time.time()
            while time.time() - now < 5:
                self.logger.info("Speaking...")
                if goalh.cancel_event.is_set():
                    self.logger.info("Cancel got")
                    return ret
                time.sleep(0.1)

        elif self.info["mode"] == "simulation":
            pass
        else: # The real deal
            self.logger.warning("{} mode not implemented for {}".format(self.info["mode"], self.name))

        self.logger.info("{} Speak finished".format(self.name))
        return ret

    def on_goal_play(self, goalh):
        self.logger.info("{} play started".format(self.name))
        if self.info["enabled"] == False:
            return {}

        try:
            string = goalh.data["string"]
            volume = goalh.data["volume"]
        except Exception as e:
            self.logger.error("{} wrong parameters: {}".format(self.name, ))

        timestamp = time.time()
        secs = int(timestamp)
        nanosecs = int((timestamp-secs) * 10**(9))
        ret = {
            "header":{
                "stamp":{
                    "sec": secs,
                    "nanosec": nanosecs
                }
            }
        }
        if self.info["mode"] == "mock":
            now = time.time()
            while time.time() - now < 5:
                self.logger.info("Playing...")
                if goalh.cancel_event.is_set():
                    self.logger.info("Cancel got")
                    return ret
                time.sleep(0.1)

        elif self.info["mode"] == "simulation":
            pass
        else: # The real deal
            self.logger.warning("{} mode not implemented for {}".format(self.info["mode"], self.name))

        self.logger.info("{} Playing finished".format(self.name))
        return ret

    def enable_callback(self, message, meta):
        self.info["enabled"] = True
        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        self.play_action_server.run()
        self.speak_action_server.run()
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

    def memory_write(self, data):
        del self.memory[-1]
        self.memory.insert(0, data)
