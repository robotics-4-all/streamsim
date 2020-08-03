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

from commlib.logger import Logger

from .conn_params import ConnParams
if ConnParams.type == "amqp":
    from commlib.transports.amqp import RPCService, Subscriber
elif ConnParams.type == "redis":
    from commlib.transports.redis import RPCService, Subscriber

class CameraController:
    def __init__(self, info = None):
        self.logger = Logger(info["name"] + "-" + info["id"])

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]
        self.actors = info["actors"]

        if self.info["mode"] == "real":
            from pidevices import Camera, Dims
            self.sensor = Camera(framerate=self.conf["framerate"],
                                 resolution=Dims(self.conf["width"], self.conf["height"]),
                                 name=self.name,
                                 max_data_length=self.conf["max_data_length"])
            self.sensor.stop()
            ## https://github.com/robotics-4-all/tektrain-ros-packages/blob/master/ros_packages/robot_hw_interfaces/camera_hw_interface/camera_hw_interface/camera_hw_interface.py

        self.memory = 100 * [0]

        self.get_image_rpc_server = RPCService(conn_params=ConnParams.get(), on_request=self.get_image_callback, rpc_name=info["base_topic"] + "/get")

        self.enable_rpc_server = RPCService(conn_params=ConnParams.get(), on_request=self.enable_callback, rpc_name=info["base_topic"] + "/enable")
        self.disable_rpc_server = RPCService(conn_params=ConnParams.get(), on_request=self.disable_callback, rpc_name=info["base_topic"] + "/disable")

        if self.info["mode"] == "simulation":
            self.robot_pose_sub = Subscriber(conn_params=ConnParams.get(), topic = self.info['device_name'] + "/pose", on_message = self.robot_pose_update)
            self.robot_pose_sub.run()

        # The images
        self.images = {
            "barcode": "barcode.jpg",
            "face": "faces.jpg",
            "qr": "qr_code.png",
            "ocr_gr": "testocr.png",
            "ocr_en": "text.png"
        }

    def robot_pose_update(self, message, meta):
        self.robot_pose = message

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

    def stop(self):
        self.get_image_rpc_server.stop()
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()

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
            im = cv2.imread(dirname + '/resources/all.png')
            im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
            image = cv2.resize(im, dsize=(width, height))
            data = [int(d) for row in image for c in row for d in c]
            data = base64.b64encode(bytes(data)).decode("ascii")
        elif self.info["mode"] == "simulation":
            dirname = os.path.dirname(__file__)
            im = cv2.imread(dirname + '/resources/all.png')
            im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
            image = cv2.resize(im, dsize=(width, height))
            data = [int(d) for row in image for c in row for d in c]
            data = base64.b64encode(bytes(data)).decode("ascii")
        else: # The real deal
            self.sensor.start()
            img = self.sensor.read(image_dims=(width, height))[-1].frame
            self.sensor.stop()
            data = base64.b64encode(img).decode("ascii")

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
