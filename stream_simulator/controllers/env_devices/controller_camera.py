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
        self.range = 80 if 'range' not in conf else conf['range']
        self.fov = 60 if 'fov' not in conf else conf['fov']

        tf_package = {
            "type": "env",
            "subtype": {
                "category": _category,
                "class": _class,
                "subclass": [_subclass]
            },
            "pose": self.pose,
            "base_topic": self.base_topic,
            "name": self.name,
            "range": self.range,
            "properties": {
                "fov": self.fov
            }
        }

        self.host = None
        if 'host' in info['conf']:
            self.host = info['conf']['host']
            tf_package['host'] = self.host
            # No other host type is available for env_devices
            tf_package['host_type'] = 'pan_tilt'

        package["tf_declare"].call(tf_package)

        # The images
        self.images = {
            "barcodes": "barcode.jpg",
            "humans": "faces.jpg",
            "qrs": "qr_code.png",
            "texts": "testocr.png",
            "colors": "dog.jpg",
            "empty": "empty.png"
        }

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
            dirname = os.path.dirname(__file__) + "/../.."
            data = None

            if self.mode == "mock":
                im = cv2.imread(dirname + '/resources/all.png')
                im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
                image = cv2.resize(im, dsize=(width, height))
                data = [int(d) for row in image for c in row for d in c]
                data = base64.b64encode(bytes(data)).decode("ascii")
            elif self.mode == "simulation":
                # Ask tf for proximity sound sources or humans
                res = CommlibFactory.get_tf_affection.call({
                    'name': self.name
                })
                # import pprint
                # pprint.pprint(res)
                # print('\n')

                # Get the closest:
                clos = None
                clos_d = 100000.0
                for x in res:
                    if res[x]['distance'] < clos_d:
                        clos = x
                        clos_d = res[x]['distance']

                if clos == None:
                    cl_type = None
                else:
                    cl_type = res[clos]['type']

                if cl_type == None:
                    img = "all.png"
                elif cl_type == "human":
                    img = random.choice(["face.jpg", "face_inverted.jpg"])

                elif cl_type == "qr":
                    import qrcode
                    try:
                        im = qrcode.make(res[clos]["info"]["message"])
                    except Exception as e:
                        self.logger.error(f"QR creator could not produce string: {res[clos]['info']['message']} or qrcode library is not installed: {str(e)}")
                    im.save(dirname + "/resources/qr_tmp.png")
                    img = "qr_tmp.png"

                elif cl_type == "barcode":
                    img = "barcode.jpg"

                elif cl_type == 'color':
                    import numpy as np
                    img = 'col_tmp.png'
                    tmp = np.zeros((height, width, 3), np.uint8)
                    tmp[:] = (
                        res[clos]['info']["b"],
                        res[clos]['info']["g"],
                        res[clos]['info']["r"]
                    )
                    cv2.imwrite(dirname + "/resources/" + img, tmp)

                elif cl_type == "text":
                    import numpy as np
                    img = 'txt_temp.png'
                    try:
                        from PIL import Image, ImageDraw, ImageFont, ImageFilter
                        im  =  Image.new ( "RGB", (width,height), (255, 255, 255) )
                        draw  =  ImageDraw.Draw ( im )
                        final_text = res[clos]['info']["text"]
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
                        self.logger.error(f"CameraController: Error with text image generation: {str(e)}")

                im = cv2.imread(dirname + '/resources/' + img)
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
