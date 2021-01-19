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

        _type = "CAMERA"
        _category = "sensor"
        _class = "visual"
        _subclass = "camera"
        _name = conf["name"]
        _pack = package["base"]
        _place = conf["place"]
        id = "d_" + str(BaseThing.id)

        info = {
            "type": _type,
            "base_topic": f"{_pack}.{_place}.{_category}.{_class}.{_subclass}.{_name}.{id}",
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
        self.width = conf['width']
        self.height = conf['height']
        self.name = info["name"]
        self.base_topic = info["base_topic"]
        self.hz = info['conf']['hz']
        self.mode = info["mode"]
        self.place = info["conf"]["place"]
        self.pose = info["conf"]["pose"]
        self.derp_data_key = info["base_topic"] + ".raw"

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

        package["tf_declare"].call(tf_package)

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

            # Storing value:
            r = CommlibFactory.derp_client.lset(
                self.derp_data_key,
                [{
                    "value": {
                        "timestamp": time.time(),
                        "format": "RGB",
                        "per_rows": True,
                        "width": width,
                        "height": height,
                        "image": data
                    },
                    "timestamp": time.time()
                }]
            )

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
