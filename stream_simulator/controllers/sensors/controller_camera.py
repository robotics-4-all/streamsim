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
from os.path import expanduser
import base64

from colorama import Fore, Style

from commlib.logger import Logger
from stream_simulator.connectivity import CommlibFactory
from stream_simulator.base_classes import BaseThing

class CameraController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = Logger(conf["name"])
        else:
            self.logger = package["logger"]

        super(self.__class__, self).__init__()
        id = "d_" + str(BaseThing.id)
        name = "camera_" + str(id)
        if 'name' in conf:
            name = conf['name']
            id = name
            
        info = {
            "type": "CAMERA",
            "brand": "picamera",
            "base_topic": package["name"] + ".sensor.visual.camera." + str(id),
            "name": name,
            "place": conf["place"],
            "id": id,
            "enabled": True,
            "orientation": conf["orientation"],
            "hz": conf["hz"],
            "queue_size": 0,
            "mode": package["mode"],
            "namespace": package["namespace"],
            "sensor_configuration": conf["sensor_configuration"],
            "device_name": package["device_name"],
            "actors": package["actors"],
            "endpoints":{
                "enable": "rpc",
                "disable": "rpc",
                "data": "publisher"
            },
            "data_models": {
                "data": {"data":
                    ["format", "per_rows", "width", "height", "image"]
                }
            }
        }

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]
        self.base_topic = info["base_topic"]
        self.derp_data_key = info["base_topic"] + ".raw"

        # tf handling
        tf_package = {
            "type": "robot",
            "subtype": "camera",
            "pose": conf["pose"],
            "base_topic": info['base_topic'],
            "name": self.name
        }
        tf_package['host'] = package['device_name']
        tf_package['host_type'] = 'robot'
        if 'host' in conf:
            tf_package['host'] = conf['host']
            tf_package['host_type'] = 'pan_tilt'
        package["tf_declare"].call(tf_package)

        self.publisher = CommlibFactory.getPublisher(
            broker = "redis",
            topic = self.base_topic + ".data"
        )

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
        if self.info["mode"] == "simulation":
            self.robot_pose_sub = CommlibFactory.getSubscriber(
                broker = "redis",
                topic = self.info['namespace'] + '.' + self.info['device_name'] + ".pose",
                callback = self.robot_pose_update
            )
            self.robot_pose_sub.run()

        self.video_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.video_callback,
            rpc_name = info["base_topic"] + ".video"
        )
        self.enable_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.enable_callback,
            rpc_name = info["base_topic"] + ".enable"
        )
        self.disable_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.disable_callback,
            rpc_name = info["base_topic"] + ".disable"
        )

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

    def robot_pose_update(self, message, meta):
        self.robot_pose = message

    def enable_callback(self, message, meta):
        self.info["enabled"] = True
        self.sensor_read_thread = threading.Thread(target = self.sensor_read)
        self.sensor_read_thread.start()
        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()
        self.video_rpc_server.run()

        if self.info["enabled"]:
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info("Camera {} reads with {} Hz".format(self.info["id"], self.info["hz"]))

    def stop(self):
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()
        self.video_rpc_server.stop()

    def writeImageToFile(self, path = None, image = None, w = None, h = None):
        try:
            from PIL import Image
            imgdata = list(base64.b64decode(image.encode("ascii")))
            img = Image.new('RGB', [w, h], 255)
            data = img.load()
            cnt = 0
            for line in range(0, h):
                for column in range(0, w):
                    data[column, line] = (
                        imgdata[cnt + 0],
                        imgdata[cnt + 1],
                        imgdata[cnt + 2]
                    )
                    cnt += 3
            img.save(path)
        except Exception as e:
            self.logger.error(str(e))

    def video_callback(self, message, meta):
        self.logger.info(f"Video requested with input {message}")
        duration = message["duration"]
        width = 640
        height = 480
        # Wait till time passes
        now = time.time()
        curr_img = self.image_counter

        self.logger.info(f"Generating images")
        while time.time() - now < duration:
            self.writeImageToFile(
                path = expanduser("~") + f"/img_{self.image_counter}_motion.jpg",
                image = self.img["image"],
                w = width,
                h = height
            )
            while curr_img == self.image_counter:
                time.sleep(0.1)
            curr_img = self.image_counter

        self.logger.info(f"Creating the video")
        # Write the video
        import cv2
        import os
        image_folder = expanduser("~")
        video_name = expanduser("~") + '/video_motion_detection.avi'

        images = [img for img in os.listdir(image_folder) if img.endswith("_motion.jpg")]
        frame = cv2.imread(os.path.join(image_folder, images[0]))
        height, width, layers = frame.shape
        video = cv2.VideoWriter(video_name, 0, 3,  (int(width/4),int(height/4)))
        for image in images:
            i = cv2.imread(os.path.join(image_folder, image))
            i = cv2.resize(i, (int(width/4),int(height/4)))
            video.write(i)
        cv2.destroyAllWindows()
        video.release()

        # Load video and send it as base64 string
        self.logger.info(f"Encoding")
        import base64
        data = open(video_name, "rb").read()
        enc_data = base64.b64encode(data)
        print(len(enc_data))

        self.logger.info(f"Cleaning up images")
        dir = expanduser("~")
        os.system(f"cd {dir} && rm *_motion.jpg")

        self.logger.info(f"Sending it")

        return {"data": enc_data.decode('ascii')}

    def sensor_read(self):
        self.logger.info("camera {} sensor read thread started".format(self.info["id"]))
        self.image_counter = 0
        while self.info["enabled"]:
            time.sleep(1.0 / self.info["hz"])
            self.img = self.get_image({"width": 640, "height": 480})
            self.image_counter += 1
            # Publishing value:
            self.publisher.publish({
                "data": self.img,
                "timestamp": time.time()
            })

            # Storing value:
            r = CommlibFactory.derp_client.lset(
                self.derp_data_key,
                [{
                    "data": self.img,
                    "timestamp": time.time()
                }]
            )

    def get_image(self, message):
        self.logger.debug("Robot {}: get image callback: {}".format(self.name, message))
        try:
            width = message["width"]
            height = message["height"]
        except Exception as e:
            self.logger.error("{}: Malformed message for image get: {} - {}".format(self.name, str(e.__class__), str(e)))
            return {}

        if self.info["mode"] == "mock":
            dirname = os.path.dirname(__file__) + "/../.."
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
                "texts": [],
                "superman": []
            }
            closest = "empty"
            closest_dist = 1000000000000
            closest_full = None

            for h in self.actors:
                if h["type"] not in ["humans", "superman", "qrs", "barcodes", "colors", "texts"]:
                    continue

                xx = h["x"] * reso
                yy = h["y"] * reso
                d = math.hypot(xx - x, yy - y)
                self.logger.debug("dist to {}: {}".format(h["id"], d))
                if d <= 2.0:
                    # In range - check if in the same semi-plane
                    xt = x + math.cos(th) * d
                    yt = y + math.sin(th) * d
                    thres = d * 1.4142
                    self.logger.debug("\tThres to {}: {} / {}".format(h["id"], math.hypot(xt - xx, yt - yy), thres))
                    if math.hypot(xt - xx, yt - yy) < thres:
                        # We got a winner!
                        findings[h["type"]].append(h)
                        if d < closest_dist:
                            closest = h["type"]
                            closest_full = h

            for i in findings:
                for j in findings[i]:
                    self.logger.debug("Camera detected: " + str(j))
            self.logger.debug("Closest detection: {}".format(closest))

            img = self.images[closest]

            dirname = os.path.dirname(__file__) + "/../.."

            cl_f = closest_full
            if closest == "empty":
                cl_f = "empty"
            CommlibFactory.derp_client.lset(
                self.info["namespace"] + "." + self.info["device_name"] + ".detect.source",
                [cl_f]
            )
            self.logger.debug(f"Derp me updated with {cl_f}")

            # Special handle for humans
            if closest == "humans":
                if closest_full["move"] == 0:
                    img = "face.jpg"
                else:
                    img = random.choice(["face.jpg", "face_inverted.jpg"])

            # Special handle for superman
            if closest == "superman":
                img = "all.png"

            # Special handle for barcodes
            if closest == "barcodes":
                img = "barcode.jpg"

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
                try:
                    im = qrcode.make(closest_full["message"])
                    im.save(dirname + "/resources/temp.png")
                    img = "temp.png"
                except:
                    self.logger.error(f"QR creator could not produce string: {closest_full['message']} or qrcode library is not installed")
                    img = self.images[closest]

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
            "timestamp": time.time(),
            "format": "RGB",
            "per_rows": True,
            "width": width,
            "height": height,
            "image": data
        }
        self.logger.debug(f"Camera controller sends {len(data)} bytes")
        return ret
