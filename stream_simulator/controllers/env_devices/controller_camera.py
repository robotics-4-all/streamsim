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

class EnvCameraController(BaseThing):
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

        _type = "CAMERA"
        _category = "visual"
        _brand = "logitech"
        _name_suffix = "camera_"
        _endpoints = {
            "enable": "rpc",
            "disable": "rpc",
            "data": "pub"
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
        self.width = conf['width']
        self.height = conf['height']
        self.name = info["name"]
        self.base_topic = info["base_topic"]
        self.hz = info['conf']['hz']
        self.mode = info["mode"]
        self.place = info["conf"]["place"]
        self.pose = info["conf"]["pose"]

        # Communication
        self.publisher = CommlibFactory.getPublisher(
            broker = "redis",
            topic = self.base_topic + ".data"
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

    def sensor_read(self):
        self.logger.info(f"Sensor {self.name} read thread started")
        width = self.width
        height = self.height

        while self.info["enabled"]:
            time.sleep(1.0 / self.hz)

            data = None
            if self.mode == "mock":
                dirname = os.path.dirname(__file__) + "/../.."
                im = cv2.imread(dirname + '/resources/all.png')
                im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
                image = cv2.resize(im, dsize=(width, height))
                data = [int(d) for row in image for c in row for d in c]
                data = base64.b64encode(bytes(data)).decode("ascii")

            # Publishing value:
            self.publisher.publish({
                "value": {
                    "timestamp": time.time(),
                    "format": "RGB",
                    "per_rows": True,
                    "width": width,
                    "height": height,
                    "image": data
                },
                "timestamp": time.time()
            })

    def enable_callback(self, message, meta):
        self.info["enabled"] = True

        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        self.sensor_read_thread = threading.Thread(target = self.sensor_read)
        self.sensor_read_thread.start()

        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        if self.info["enabled"]:
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()

    def stop(self):
        self.info["enabled"] = False
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()
