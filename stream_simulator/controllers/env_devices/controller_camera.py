"""
File that contains the camera controller.
"""

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
    EnvCameraController is a class that simulates a camera sensor in an environment. 
    It inherits from BaseThing.
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

        super().__init__(conf["name"], auto_start=False)

        _type = "CAMERA"
        _category = "sensor"
        _class = "visual"
        _subclass = "camera"

        info = self.generate_info(conf, package, _type, _category, _class, _subclass)
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
        self.generating_images = False

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
        detection_type = message['detection'] # to be detected
        return self.tf_detection_rpc_client.call({
            'name': self.name,
            # face, gender, age, emotion, motion, qr, barcode, text, color, robot
            'type': detection_type,
        })

    def set_communication_layer(self, package):
        """
        Configures the communication layer for the camera controller.

        This method sets up various communication channels required for the camera
        controller to function properly within the simulation environment. It 
        initializes the simulation communication, transform communication, data 
        publisher, and enable/disable RPCs.

        Args:
            package (dict): A dictionary containing configuration parameters. 
                            Expected keys include:
                            - "namespace": The namespace for simulation communication.
        """
        self.set_simulation_communication(package["namespace"])
        self.set_tf_communication(package)
        self.set_data_publisher(self.base_topic)

    def sensor_read(self):
        """
        Reads sensor data and publishes it at a specified frequency.
        This method continuously reads data from a sensor and publishes it. T
        he behavior of the method
        depends on the mode of the sensor, which can be either "mock" or "simulation".
        In "mock" mode:
            - Reads a predefined image file and encodes it in base64 format.
        In "simulation" mode:
            - Calls a remote procedure to get information about nearby objects.
            - Determines the closest object and its type (e.g., human, QR code, 
            barcode, color, text).
            - Generates an image based on the type of the closest object:
                - For humans, selects a random face image.
                - For QR codes, generates a QR code image from the provided message.
                - For barcodes, uses a predefined barcode image.
                - For colors, creates an image filled with the specified color.
                - For text, generates an image with the specified text centered.
            - Encodes the generated image in base64 format.
        The method publishes the encoded image data along with metadata such as 
        timestamp, format, width, and height.
        Raises:
            Exception: If there is an error generating the text image in "simulation" mode.
        Logs:
            - Information about the start of the sensor read thread.
            - Errors related to QR code generation and text image generation.
        """
        self.logger.info("Sensor %s read thread started", self.name)
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

                # print("Closest: ", clos, clos_d, cl_type)

                # types: qr, barcode, color, text, human
                if cl_type is None:
                    img = "all.jpg"
                elif cl_type == "human":
                    img = random.choice(["face.jpg", "face_inverted.jpg"])
                elif cl_type == "qr":
                    try:
                        im = qrcode.make(affections[clos]["info"]["message"])
                    except: # pylint: disable=bare-except
                        self.logger.error(\
                            "QR creator could not produce string or qrcode \
                                library is not installed")
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
                            (text_width, text_height), _ = \
                                cv2.getTextSize(final_text, font, font_scale, thickness)
                            x = (width - text_width) // 2
                            y = (height + text_height) // 2
                            if x < 0:
                                font_scale -= 0.1
                                thickness = thickness - 1 if thickness > 1 else 1

                        # Draw the text on the image
                        # pylint: disable=no-member
                        cv2.putText(image, final_text, (x, y), font, \
                            font_scale, color, thickness, lineType=cv2.LINE_AA)

                        # Save the image to a file
                        cv2.imwrite(dirname + "/resources/" + img, image) # pylint: disable=no-member

                    except Exception as e: # pylint: disable=broad-except
                        self.logger.error("CameraController: Error with \
                            text image generation: %s", str(e))

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

        self.stopped = True

    def start(self):
        """
        Starts the sensor and waits for the simulator to start.
        This method logs the initial state of the sensor and enters a loop, 
        waiting for the simulator to start. Once the simulator has started, 
        it logs the sensor's start state. If the sensor is enabled, it starts 
        a new thread to read sensor data.
        Attributes:
            simulator_started (bool): Flag indicating if the simulator has started.
            info (dict): Dictionary containing sensor information, including 
                         whether the sensor is enabled.
            sensor_read_thread (threading.Thread): Thread for reading sensor data.
        """
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)
        self.logger.info("Sensor %s started", self.name)

        if self.info["enabled"] and "generate_images" in self.info and self.info["generate_images"]:
            self.generating_images = True
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()

    def stop(self):
        """
        Stops the camera controller by disabling the camera and stopping the RPC servers.

        This method sets the "enabled" flag in the info dictionary to False, 
        indicating that the camera is no longer active.
        It also stops the RPC servers responsible for enabling and disabling the camera.
        """
        self.info["enabled"] = False
        self.logger.warning("Sensor %s stopping", self.name)
        while not self.stopped and self.generating_images:
            time.sleep(0.1)
        self.logger.warning("Sensor %s stopped", self.name)
