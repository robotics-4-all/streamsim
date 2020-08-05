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

        # merge actors
        self.actors = []
        for i in info["actors"]:
            for h in info["actors"][i]:
                k = h
                h["type"] = i
                self.actors.append(k)

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
            "barcodes": "barcode.jpg",
            "humans": "faces.jpg",
            "qrs": "qr_code.png",
            "texts": "testocr.png",
            "colors": "dog.jpg"
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
            # Find actors in camera's view
            x = self.robot_pose["x"]
            y = self.robot_pose["y"]
            th = self.robot_pose["theta"]
            reso = self.robot_pose["resolution"]

            findings = {
                "humans": [],
                "qrs": [],
                "barcodes": [],
                "colors": [],
                "texts": []
            }
            closest = "empty"
            closest_dist = 1000000000000
            closest_full = None

            for h in self.actors:
                if h["type"] not in ["humans", "qrs", "barcodes", "colors", "texts"]:
                    continue
                    
                xx = h["x"] * reso
                yy = h["y"] * reso
                d = math.hypot(xx - x, yy - y)
                self.logger.info("dist to {}: {}".format(h["id"], d))
                if d <= 2.0:
                    # In range - check if in the same semi-plane
                    xt = x + math.cos(th) * d
                    yt = y + math.sin(th) * d
                    thres = d * 1.4142
                    self.logger.info("\tThres to {}: {} / {}".format(h["id"], math.hypot(xt - xx, yt - yy), thres))
                    if math.hypot(xt - xx, yt - yy) < thres:
                        # We got a winner!
                        findings[h["type"]].append(h)
                        if d < closest_dist:
                            closest = h["type"]
                            closest_full = h

            for i in findings:
                for j in findings[i]:
                    self.logger.info("Camera detected: " + str(j))
            self.logger.info("Closest detection: {}".format(closest))

            img = self.images[closest]

            dirname = os.path.dirname(__file__)

            # Special handle for color
            if closest == "colors":
                import numpy as np
                img = 'temp.png'
                tmp = np.zeros((height, width, 3), np.uint8)
                tmp[:] = (
                    closest_full["b"],
                    closest_full["g"],
                    closest_full["r"]
                )
                cv2.imwrite(dirname + "/resources/" + img, tmp)

            # Special handle for qrs
            if closest == "qrs":
                import qrcode
                im = qrcode.make(closest_full["message"])
                im.save(dirname + "/resources/temp.png")
                img = "temp.png"

            # Special handle for texts
            if closest == "texts":
                import numpy as np
                img = 'temp.png'
                try:
                    from PIL import Image, ImageDraw, ImageFont, ImageFilter
                    im  =  Image.new ( "RGB", (width,height), (255, 255, 255) )
                    draw  =  ImageDraw.Draw ( im )

                    final_text = closest_full["text"]
                    final_text = [final_text[i:i+30] for i in range(0, len(final_text), 30)]

                    start_coord = 30
                    for i in final_text:
                        draw.text (
                            (10, start_coord),
                            i,
                            font=ImageFont.truetype("DejaVuSans.ttf", 36),
                            fill=(0,0,0)
                        )
                        start_coord += 40
                    im.save(dirname + "/resources/" + img)
                except Exception as e:
                    self.logger.error("CameraController: Error with text image generation")
                    print(e)

            im = cv2.imread(dirname + '/resources/' + img)
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
