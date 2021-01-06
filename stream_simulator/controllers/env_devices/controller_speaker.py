#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random
import os
import cv2
import base64

from colorama import Fore, Style

from commlib.logger import Logger
from stream_simulator.base_classes import BaseThing
from stream_simulator.connectivity import CommlibFactory

class EnvSpeakerController(BaseThing):
    def __init__(self,
                 conf = None,
                 package = None
                 ):

        if package["logger"] is None:
            self.logger = Logger(conf["name"])
        else:
            self.logger = package["logger"]

        super(self.__class__, self).__init__()

        _name = conf["name"]

        _type = "SPEAKERS"
        _category = "audio"
        _brand = "logitech"
        _name_suffix = "speaker_"
        _endpoints = {
            "enable": "rpc",
            "disable": "rpc",
            "play": "action",
            "speak": "action"
        }

        id = BaseThing.id
        info = {
            "type": _type,
            "brand": _brand,
            "base_topic": package["base"] + conf["place"] + f".sensor.{_category}.{_name}.d" + str(id),
            "name": _name_suffix + str(id),
            "place": conf["place"],
            "enabled": True,
            "mode": conf["mode"],
            "conf": conf,
            "endpoints": _endpoints
        }

        self.info = info
        self.name = info["name"]
        self.base_topic = info["base_topic"]
        self.mode = info["mode"]
        self.place = info["conf"]["place"]
        self.pose = info["conf"]["pose"]

        # tf handling
        tf_package = {
            "type": "env",
            "subtype": "speaker",
            "pose": self.pose,
            "base_topic": self.base_topic,
            "name": self.name
        }

        self.host = None
        if 'host' in info['conf']:
            self.host = info['conf']['host']
            tf_package['host'] = self.host

        package["tf_declare"].call(tf_package)

        self.blocked = False

        # Communication
        self.play_action_server = CommlibFactory.getActionServer(
            broker = "redis",
            callback = self.on_goal_play,
            action_name = info["base_topic"] + ".play"
        )
        self.speak_action_server = CommlibFactory.getActionServer(
            broker = "redis",
            callback = self.on_goal_speak,
            action_name = info["base_topic"] + ".speak"
        )
        self.enable_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.enable_callback,
            rpc_name = self.base_topic + ".enable"
        )
        self.disable_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.disable_callback,
            rpc_name = self.base_topic + ".disable"
        )


    def enable_callback(self, message, meta):
        self.info["enabled"] = True

        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        self.play_action_server.run()
        self.speak_action_server.run()

        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        self.play_action_server.run()
        self.speak_action_server.run()

    def stop(self):
        self.info["enabled"] = False
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()

        self.play_action_server._goal_rpc.stop()
        self.play_action_server._cancel_rpc.stop()
        self.play_action_server._result_rpc.stop()
        self.speak_action_server._goal_rpc.stop()
        self.speak_action_server._cancel_rpc.stop()
        self.speak_action_server._result_rpc.stop()

    def on_goal_play(self, goalh):
        self.logger.info("{} play started".format(self.name))
        if self.info["enabled"] == False:
            return {}

        # Concurrent speaker calls handling
        while self.blocked:
            time.sleep(0.1)
        self.logger.info("Speaker unlocked")
        self.blocked = True

        try:
            string = goalh.data["string"]
            volume = goalh.data["volume"]
        except Exception as e:
            self.logger.error("{} wrong parameters: {}".format(self.name, ))

        if self.info["mode"] in ["mock", "simulation"]:
            now = time.time()
            self.logger.info("Playing...")
            while time.time() - now < 5:
                if goalh.cancel_event.is_set():
                    self.logger.info("Cancel got")
                    self.blocked = False
                    return ret
                time.sleep(0.1)
            self.logger.info("Playing done")

        self.logger.info("{} Playing finished".format(self.name))
        self.blocked = False
        return {
            "timestamp": time.time()
        }

    def on_goal_speak(self, goalh):
        self.logger.info("{} speak started".format(self.name))
        if self.info["enabled"] == False:
            return {}

        # Concurrent speaker calls handling
        while self.blocked:
            time.sleep(0.1)
        self.logger.info("Speaker unlocked")
        self.blocked = True

        try:
            texts = goalh.data["text"]
            volume = goalh.data["volume"]
            language = goalh.data["language"]
        except Exception as e:
            self.logger.error("{} wrong parameters: {}".format(self.name, ))

        if self.info["mode"] in ["mock", "simulation"]:
            now = time.time()
            self.logger.info("Speaking...")
            while time.time() - now < 5:
                if goalh.cancel_event.is_set():
                    self.logger.info("Cancel got")
                    self.blocked = False
                    return ret
                time.sleep(0.1)
            self.logger.info("Speaking done")

        self.logger.info("{} Speak finished".format(self.name))
        self.blocked = False
        return {
            'timestamp': time.time()
        }
