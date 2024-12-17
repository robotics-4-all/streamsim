#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging
import threading
import random
import os
import base64
import numpy as np
import qrcode
import cv2

from stream_simulator.base_classes import BaseThing

class EnvCameraController(BaseThing):
    """
    EnvCameraController is a class that simulates a camera sensor in an environment. It inherits from BaseThing.
    Attributes:
        logger (logging.Logger): Logger instance for logging information.
        info (dict): Dictionary containing camera information and configuration.
        width (int): Width of the camera image.
        height (int): Height of the camera image.
        name (str): Name of the camera.
        base_topic (str): Base topic for communication.
        hz (int): Frequency at which the camera operates.
        mode (str): Mode of operation (e.g., "mock", "simulation").
        place (str): Place where the camera is located.
        pose (dict): Pose of the camera.
        derp_data_key (str): Key for raw data.
        range (int): Range of the camera.
        fov (int): Field of view of the camera.
        env_properties (dict): Environmental properties.
        host (str): Host information.
        images (dict): Dictionary of image resources.
    Methods:
        __init__(conf=None, package=None):
            Initializes the EnvCameraController with the given configuration and package.
        set_communication_layer(package):
            Sets up the communication layer for the camera.
        sensor_read():
            Reads data from the sensor and publishes it.
        enable_callback(message):
            Callback function to enable the camera.
        disable_callback(message):
            Callback function to disable the camera.
        start():
            Starts the camera and its RPC servers.
        stop():
            Stops the camera and its RPC servers.
    """
    def __init__(self,
                 conf = None,
                 package = None
                 ):

        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        super().__init__(conf["name"])

        _type = "CAMERA"
        _category = "sensor"
        _class = "visual"
        _subclass = "camera"
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
        self.env_properties = package['env']

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
                "fov": self.fov,
                'ambient_luminosity': self.env_properties['luminosity']
            }
        }

        self.host = None
        if 'host' in info['conf']:
            self.host = info['conf']['host']
            tf_package['host'] = self.host
            # No other host type is available for env_devices
            tf_package['host_type'] = 'pan_tilt'

        self.set_communication_layer(package)

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

    def set_communication_layer(self, package):
        self.set_tf_communication(package)
        self.set_data_publisher(self.base_topic)
        self.set_enable_disable_rpcs(
            self.base_topic,
            self.enable_callback,
            self.disable_callback
        )

    def sensor_read(self):
        self.logger.info(f"Sensor %s read thread started", self.name)
        width = self.width
        height = self.height

        while self.info["enabled"]:
            time.sleep(1.0 / self.hz)
            dirname = os.path.dirname(__file__) + "/../.."
            data = None

            if self.mode == "mock":
                with open(dirname + '/resources/all.png', "rb") as f:
                    fdata = f.read()
                    b64 = base64.b64encode(fdata)
                    data = b64.decode()
            elif self.mode == "simulation":
                # Ask tf for proximity sound sources or humans
                res = self.tf_affection_rpc.call({
                    'name': self.name
                })
                # print("Affections: ", res)

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

                # print("Closest: ", clos, clos_d, cl_type)

                # types: qr, barcode, color, text, human
                if cl_type is None:
                    img = "all.jpg"
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

                    except Exception as e:
                        self.logger.error("CameraController: Error with text image generation: %s", str(e))

                # print("Image: ", img)

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

    def enable_callback(self, message):
        self.info["enabled"] = True
        self.sensor_read_thread = threading.Thread(target = self.sensor_read)
        self.sensor_read_thread.start()

        return {"enabled": True}

    def disable_callback(self, message):
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
