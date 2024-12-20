#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging
import threading
import random
import numpy as np
import os
from os.path import expanduser
import base64
import cv2
import qrcode

from stream_simulator.base_classes import BaseThing

class CameraController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        id = "d_camera_" + str(BaseThing.id + 1)
        name = id
        if 'name' in conf:
            name = conf['name']
        _category = "sensor"
        _class = "visual"
        _subclass = "camera"
        _pack = package["name"]
        _namespace = package["namespace"]

        super().__init__(id, auto_start=False)
        self.set_simulation_communication(_namespace)

        info = {
            "type": "CAMERA",
            "brand": "picamera",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": name,
            "place": conf["place"],
            "id": id,
            "enabled": True,
            "orientation": float(conf["orientation"]),
            "hz": conf["hz"],
            "queue_size": 0,
            "mode": package["mode"],
            "namespace": package["namespace"],
            "device_name": package["device_name"],
            "actors": package["actors"],
            "categorization": {
                "host_type": "robot",
                "place": _pack.split(".")[-1],
                "category": _category,
                "class": _class,
                "subclass": [_subclass],
                "name": name
            }
        }

        self.info = info
        self.width = conf['width']
        self.height = conf['height']
        self.name = info["name"]
        self.base_topic = info["base_topic"]
        self.derp_data_key = info["base_topic"] + ".raw"
        self.range = 80 if 'range' not in conf else conf['range']
        self.fov = 60 if 'fov' not in conf else conf['fov']
        self.env_properties = package["env_properties"]

        self.set_tf_communication(package)

        # tf handling
        tf_package = {
            "type": "robot",
            "subtype": {
                "category": _category,
                "class": _class,
                "subclass": [_subclass]
            },
            "pose": conf["pose"],
            "base_topic": info['base_topic'],
            "name": self.name,
            "range": self.range,
            "namespace": _namespace,
            "properties": {
                "fov": self.fov,
                'ambient_luminosity': self.env_properties['luminosity']
            }
        }
        tf_package['host'] = package['device_name']
        tf_package['host_type'] = 'robot'
        if 'host' in conf:
            tf_package['host'] = conf['host']
            tf_package['host_type'] = 'pan_tilt'


        self.publisher = self.commlib_factory.getPublisher(
            topic = self.base_topic + ".data"
        )

        # merge actors
        self.actors = []
        for i in info["actors"]:
            for h in info["actors"][i]:
                k = h
                h["type"] = i
                self.actors.append(k)

        if self.info["mode"] == "simulation":
            self.robot_pose_sub = self.commlib_factory.getSubscriber(
                topic = self.info['namespace'] + '.' + self.info['device_name'] + ".pose.inernal",
                callback = self.robot_pose_update
            )

        self.enable_rpc_server = self.commlib_factory.getRPCService(
            callback = self.enable_callback,
            rpc_name = self.base_topic + ".enable"
        )
        self.disable_rpc_server = self.commlib_factory.getRPCService(
            callback = self.disable_callback,
            rpc_name = self.base_topic + ".disable"
        )

        self.commlib_factory.run()
        
        self.tf_declare_rpc.call(tf_package)

        # The images
        self.images = {
            "barcodes": "barcode.jpg",
            "humans": "faces.jpg",
            "qrs": "qr_code.png",
            "texts": "testocr.png",
            "colors": "dog.jpg",
            "empty": "empty.png",
            "superman": "all.png"
        }

    def robot_pose_update(self, message):
        self.robot_pose = message

    def enable_callback(self, _):
        self.info["enabled"] = True
        self.sensor_read_thread = threading.Thread(target = self.sensor_read)
        self.sensor_read_thread.start()
        return {"enabled": True}

    def disable_callback(self, message):
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)
        self.logger.info("Sensor %s started", self.name)

        if self.info["enabled"]:
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info("Camera {} reads with {} Hz".format(self.info["id"], self.info["hz"]))

    def stop(self):
        self.commlib_factory.stop()

    def sensor_read(self):
        self.logger.info("camera {} sensor read thread started".format(self.info["id"]))
        width = self.width
        height = self.height

        while self.info["enabled"]:
            time.sleep(1.0 / self.info["hz"])
            dirname = os.path.dirname(__file__) + "/../.."
            data = None

            if self.info["mode"] == "mock":
                with open(dirname + '/resources/all.png', "rb") as f:
                    fdata = f.read()
                    b64 = base64.b64encode(fdata)
                    data = b64.decode()

            elif self.info["mode"] == "simulation":
                # Ask tf for proximity sound sources or humans
                res = self.tf_affection_rpc.call({
                    'name': self.name
                })

                # Get the closest:
                clos = None
                clos_d = 100000.0
                for x in res:
                    if res[x]['distance'] < clos_d:
                        clos = x
                        clos_d = res[x]['distance']

                if clos is None:
                    cl_type = None
                else:
                    cl_type = res[clos]['type']

                # print(self.name, cl_type)

                if cl_type is None:
                    img = "all.png"
                elif cl_type == "human":
                    img = random.choice(["face.jpg", "face_inverted.jpg"])
                elif cl_type == "qr":
                    try:
                        im = qrcode.make(res[clos]["info"]["message"])
                    except: # pylint: disable=bare-except
                        self.logger.error("QR creator could not produce string or qrcode library is not installed")
                    im.save(dirname + "/resources/qr_tmp.png")
                    img = "qr_tmp.png"
                elif cl_type == "barcode":
                    img = "barcode.jpg"
                elif cl_type == 'color':
                    img = 'col_tmp.png'
                    tmp = np.zeros((height, width, 3), np.uint8)
                    tmp[:] = (
                        res[clos]['info']["b"],
                        res[clos]['info']["g"],
                        res[clos]['info']["r"]
                    )
                    cv2.imwrite(dirname + "/resources/" + img, tmp) # pylint: disable=no-member
                elif cl_type == "text":
                    img = 'txt_temp.png'
                    try:
                        image = np.zeros((height, width, 3), dtype=np.uint8)
                        # Define the text and its properties
                        final_text = res[clos]['info']["text"]
                        font = cv2.FONT_HERSHEY_SIMPLEX # pylint: disable=no-member
                        font_scale = 2
                        color = (255, 255, 255)  # White color
                        thickness = 3

                        # Calculate text size and position to center it
                        # Also adjust to text size
                        x = -1
                        while x < 0:
                            (text_width, text_height), _ = cv2.getTextSize(final_text, font, font_scale, thickness) # pylint: disable=no-member
                            x = (width - text_width) // 2
                            y = (height + text_height) // 2
                            if x < 0:
                                font_scale -= 0.1
                                thickness = thickness - 1 if thickness > 1 else 1

                        # Draw the text on the image
                        cv2.putText(image, final_text, (x, y), font, font_scale, color, thickness, lineType=cv2.LINE_AA) # pylint: disable=no-member

                        # Save the image to a file
                        cv2.imwrite(dirname + "/resources/" + img, image) # pylint: disable=no-member
                    except Exception as e: # pylint: disable=broad-except
                        self.logger.error(f"CameraController: Error with text image generation: {str(e)}")

                # print(f"CameraController: Published image {cl_type}")

                with open(dirname + "/resources/" + img, "rb") as f:
                    fdata = f.read()
                    b64 = base64.b64encode(fdata)
                    data = b64.decode()

                    # Publishing value:
                    self.publisher.publish({
                        "value": {
                            "timestamp": time.time(),
                            "format": "RGB",
                            "per_rows": True,
                            "width": width,
                            "height": height,
                            "image": str(data)
                        },
                        "timestamp": time.time()
                    })
                    # print(f"CameraController: Published image {cl_type}")
