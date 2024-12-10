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

from stream_simulator.base_classes import BaseThing

class EnvSpeakerController(BaseThing):
    def __init__(self,
                 conf = None,
                 package = None
                 ):

        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        super().__init__(conf["name"])

        _type = "SPEAKERS"
        _category = "actuator"
        _class = "audio"
        _subclass = "speaker"

        _name = conf["name"]
        _pack = package["base"]
        _place = conf["place"]
        _namespace = package["namespace"]
        id = "d_" + str(BaseThing.id)
        info = {
            "type": _type,
            "base_topic": f"{_namespace}.{_pack}.{_place}.{_category}.{_class}.{_subclass}.{_name}",
            "name": _name,
            "place": conf["place"],
            "enabled": True,
            "mode": conf["mode"],
            "conf": conf,
            "categorization": {
                "host_type": _pack,
                "place": _place,
                "category": _category,
                "class": _class,
                "subclass": [_subclass],
                "name": _name
            }
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
            "subtype": {
                "category": _category,
                "class": _class,
                "subclass": [_subclass]
            },
            "pose": self.pose,
            "base_topic": self.base_topic,
            "name": self.name
        }

        self.host = None
        if 'host' in info['conf']:
            self.host = info['conf']['host']
            tf_package['host'] = self.host
            # No other host type is available for env_devices
            tf_package['host_type'] = 'pan_tilt'

        self.set_communication_layer(package)

        self.tf_declare_rpc.call(tf_package)

        self.blocked = False

    def set_communication_layer(self, package):
        self.set_tf_communication(package)
        self.set_enable_disable_rpcs(self.base_topic, self.enable_callback, self.disable_callback)
        
        self.play_action_server = self.commlib_factory.getActionServer(
            callback = self.on_goal_play,
            action_name = self.base_topic + ".play"
        )
        self.speak_action_server = self.commlib_factory.getActionServer(
            callback = self.on_goal_speak,
            action_name = self.base_topic + ".speak"
        )

        self.play_pub = self.commlib_factory.getPublisher(
            topic = self.base_topic + ".play.notify"
        )
        self.speak_pub = self.commlib_factory.getPublisher(
            topic = self.base_topic + ".speak.notify"
        )

    def enable_callback(self, message):
        self.info["enabled"] = True

        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        self.play_action_server.run()
        self.speak_action_server.run()

        return {"enabled": True}

    def disable_callback(self, message):
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

        self.play_pub.publish({
            "text": string,
            "volume": volume
        })

        if self.info["mode"] in ["mock", "simulation"]:
            now = time.time()
            self.logger.info("Playing...")
            while time.time() - now < 5:
                if goalh.cancel_event.is_set():
                    self.logger.info("Cancel got")
                    self.blocked = False
                    return
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

        self.commlib_factory.notify_ui(
            type = "effector_command",
            data = {
                "name": self.name,
                "value": {
                    "text": goalh.data["text"]
                }
            }
        )

        try:
            texts = goalh.data["text"]
            volume = goalh.data["volume"]
            language = goalh.data["language"]
        except Exception as e:
            self.logger.error("{} wrong parameters: {}".format(self.name, ))

        self.speak_pub.publish({
            "text": texts,
            "volume": volume,
            "language": language,
            "speaker": self.name
        })

        if self.info["mode"] in ["mock", "simulation"]:
            now = time.time()
            self.logger.info("Speaking...")
            while time.time() - now < 5:
                if goalh.cancel_event.is_set():
                    self.logger.info("Cancel got")
                    self.blocked = False
                    return
                time.sleep(0.1)
            self.logger.info("Speaking done")

        self.logger.info("{} Speak finished".format(self.name))
        self.blocked = False
        return {
            'timestamp': time.time()
        }
