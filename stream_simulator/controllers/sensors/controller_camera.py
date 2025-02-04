"""
File that contains the camera controller.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import base64
import time
import logging
import threading
import random
import numpy as np
import cv2
import qrcode

from stream_simulator.base_classes import BaseThing

class CameraController(BaseThing):
    """
    CameraController is a class that simulates a camera sensor in a robotic system. It inherits 
    from BaseThing and 
    initializes various configurations and communication channels for the camera sensor.
    Attributes:
        logger (logging.Logger): Logger for the camera controller.
        info (dict): Information about the camera sensor including type, brand, topic, name, 
        place, id, etc.
        width (int): Width of the camera image.
        height (int): Height of the camera image.
        name (str): Name of the camera sensor.
        base_topic (str): Base topic for communication.
        derp_data_key (str): Key for raw data communication.
        range (int): Range of the camera sensor.
        fov (int): Field of view of the camera sensor.
        env_properties (dict): Environmental properties from the package.
        publisher (Publisher): Publisher for camera data.
        actors (list): List of actors interacting with the camera.
        robot_pose_sub (Subscriber): Subscriber for robot pose updates.
        enable_rpc_server (RPCService): RPC service for enabling the camera.
        disable_rpc_server (RPCService): RPC service for disabling the camera.
        images (dict): Dictionary of image resources for different scenarios.
    Methods:
        robot_pose_update(message): Updates the robot pose based on the received message.
        enable_callback(_): Enables the camera sensor and starts the sensor read thread.
        disable_callback(message): Disables the camera sensor.
        start(): Starts the camera sensor and its communication channels.
        stop(): Stops the camera sensor and its communication channels.
        sensor_read(): Reads data from the camera sensor and publishes it based on the mode 
        (mock or simulation).
    """
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        id_ = "d_camera_" + str(BaseThing.id + 1)
        name = id_
        if 'name' in conf:
            name = conf['name']
        _category = "sensor"
        _class = "visual"
        _subclass = "camera"
        _pack = package["name"]
        _namespace = package["namespace"]

        super().__init__(id_, auto_start=False)
        self.set_simulation_communication(_namespace)

        info = {
            "type": "CAMERA",
            "brand": "picamera",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": name,
            "place": conf["place"],
            "id": id_,
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


        self.publisher = self.commlib_factory.get_publisher(
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
            self.robot_pose_sub = self.commlib_factory.get_subscriber(
                topic = self.info['namespace'] + '.' + self.info['device_name'] + ".pose.internal",
                callback = self.robot_pose_update
            )

        self.detection_rpc = self.commlib_factory.get_rpc_service(
            broker = "redis",
            rpc_name = self.base_topic + ".detect",
            callback = self.detection_callback,
            auto_run = False,
        )

        self.tf_detection_rpc_client = self.commlib_factory.get_rpc_client(
            rpc_name=package["tf_detect_rpc_topic"]
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

        self.robot_pose = None
        self.sensor_read_thread = None
        self.stopped = False

    def detection_callback(self, message):
        """
        Callback function for handling detection messages.

        Args:
            message (dict): A dictionary containing the detection message. 
                            It must have a 'detection' key indicating the type of detection.

        Returns:
            None

        The function sends a request to the tf_detection_rpc_client with the detection type 
        and the name of the current instance. The response from the client is printed.
        """
        self.logger.critical("CameraController: Detection callback: %s", message)
        detection_type = message['detection'] # to be detected
        return self.tf_detection_rpc_client.call({
            'name': self.name,
            # face, gender, age, emotion, motion, qr, barcode, text, color, robot
            'type': detection_type,
        })

    def robot_pose_update(self, message):
        """
        Updates the robot's pose with the given message.

        Args:
            message: The new pose information for the robot.
        """
        self.robot_pose = message

    def start(self):
        """
        Starts the sensor and initiates the sensor read thread if enabled.
        This method logs the sensor's waiting status and continuously checks if the simulator 
        has started.
        Once the simulator is started, it logs the sensor's start status. If the sensor is enabled, 
        it creates and starts a new thread for reading sensor data and logs the reading frequency.
        Attributes:
            self.logger (Logger): Logger instance for logging information.
            self.name (str): Name of the sensor.
            self.simulator_started (bool): Flag indicating if the simulator has started.
            self.info (dict): Dictionary containing sensor configuration, including 'enabled', 
            'id', and 'hz'.
            self.sensor_read_thread (Thread): Thread instance for reading sensor data.
        """
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)
        self.logger.info("Sensor %s started", self.name)

        if self.info["enabled"] and "generate_images" in self.info and self.info["generate_images"]:
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info("Camera %s reads with %s Hz", self.info['id'], self.info['hz'])

    def stop(self):
        """
        Stops the communication library factory.

        This method halts any ongoing processes or communications managed by the
        commlib_factory instance.
        """
        self.info["enabled"] = False
        while not self.stopped:
            time.sleep(0.1)
        self.logger.warning("Sensor %s stopped", self.name)
        self.commlib_factory.stop()

    def sensor_read(self):
        """
        Reads sensor data and publishes it at a specified frequency.
        This method continuously reads data from the sensor based on the mode specified in the 
        sensor's info.
        It supports two modes: "mock" and "simulation". In "mock" mode, it reads a predefined 
        image file.
        In "simulation" mode, it interacts with a TensorFlow service to get proximity information 
        about sound sources or humans, and generates corresponding images (e.g., QR codes, barcodes, 
        colored images, or text images).
        The generated or read image is then encoded in base64 and published with metadata including 
        timestamp, format, width, and height.
        Raises:
            Exception: If there is an error generating a text image in "simulation" mode.
        Note:
            This method runs in a loop until the sensor is disabled.
        """
        self.logger.info("camera %s sensor read thread started", self.info["id"])
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
                affections = res['affections']

                # Get the closest:
                clos = None
                clos_d = 100000.0
                for x in affections:
                    if affections[x]['distance'] < clos_d:
                        clos = x
                        clos_d = affections[x]['distance']

                if clos is None:
                    cl_type = None
                else:
                    cl_type = affections[clos]['type']

                # print(self.name, cl_type)

                if cl_type is None:
                    img = "all.png"
                elif cl_type == "human":
                    img = random.choice(["face.jpg", "face_inverted.jpg"])
                elif cl_type == "qr":
                    try:
                        im = qrcode.make(affections[clos]["info"]["message"])
                    except: # pylint: disable=bare-except
                        self.logger.error("QR creator could not produce string or qrcode library \
                            is not installed")
                    im.save(dirname + "/resources/qr_tmp.png")
                    img = "qr_tmp.png"
                elif cl_type == "barcode":
                    img = "barcode.jpg"
                elif cl_type == 'color':
                    img = 'col_tmp.png'
                    tmp = np.zeros((height, width, 3), np.uint8)
                    tmp[:] = (
                        affections[clos]['info']["b"],
                        affections[clos]['info']["g"],
                        affections[clos]['info']["r"]
                    )
                    cv2.imwrite(dirname + "/resources/" + img, tmp) # pylint: disable=no-member
                elif cl_type == "text":
                    img = 'txt_temp.png'
                    try:
                        image = np.zeros((height, width, 3), dtype=np.uint8)
                        # Define the text and its properties
                        final_text = affections[clos]['info']["text"]
                        font = cv2.FONT_HERSHEY_SIMPLEX # pylint: disable=no-member
                        font_scale = 2
                        color = (255, 255, 255)  # White color
                        thickness = 3

                        # Calculate text size and position to center it
                        # Also adjust to text size
                        x = -1
                        while x < 0:
                            # pylint: disable=no-member
                            (text_width, text_height), _ = cv2.getTextSize(final_text, font, \
                                font_scale, thickness)
                            x = (width - text_width) // 2
                            y = (height + text_height) // 2
                            if x < 0:
                                font_scale -= 0.1
                                thickness = thickness - 1 if thickness > 1 else 1

                        # Draw the text on the image # pylint: disable=no-member
                        cv2.putText(image, final_text, (x, y), font, font_scale, color, \
                            thickness, lineType=cv2.LINE_AA)

                        # Save the image to a file # pylint: disable=no-member
                        cv2.imwrite(dirname + "/resources/" + img, image)
                    except Exception as e: # pylint: disable=broad-except
                        self.logger.error("CameraController: Error with text image generation: %s",
                                          str(e))

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

        self.stopped = True
