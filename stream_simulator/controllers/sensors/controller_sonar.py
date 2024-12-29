"""
File that contains the sonar controller.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import math
import logging
import threading
import random

from stream_simulator.base_classes import BaseThing

class SonarController(BaseThing):
    """
    SonarController is a class that simulates a sonar sensor for a robot. It inherits from 
    BaseThing and manages the initialization, configuration, and operation of the sonar sensor, 
    including communication with other components and handling sensor data.
    Attributes:
        logger (logging.Logger): Logger for the sonar controller.
        info (dict): Information and configuration of the sonar sensor.
        name (str): Name of the sonar sensor.
        map (numpy.ndarray): Map data for the environment.
        base_topic (str): Base topic for communication.
        derp_data_key (str): Key for raw data communication.
        publisher (Publisher): Publisher for sensor data.
        enable_rpc_server (RPCService): RPC service for enabling the sensor.
        disable_rpc_server (RPCService): RPC service for disabling the sensor.
        robot_pose_sub (Subscriber): Subscriber for robot pose updates (simulation mode).
        get_tf_rpc (RPCClient): RPC client for getting transform data (simulation mode).
        robot_pose (dict): Current pose of the robot.
        commlib_factory (CommLibFactory): Communication library factory.
        sensor_read_thread (threading.Thread): Thread for reading sensor data.
    Methods:
        __init__(conf=None, package=None): Initializes the SonarController with the given
            configuration and package.
        robot_pose_update(message): Updates the robot pose based on the received message.
        sensor_read(): Reads sensor data and publishes it at the configured frequency.
        enable_callback(message): Callback to enable the sensor and start reading data.
        disable_callback(message): Callback to disable the sensor and stop reading data.
        start(): Starts the sensor and begins reading data when the simulator is started.
        stop(): Stops the sensor and communication library.
    """
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        id_ = "d_sonar_" + str(BaseThing.id + 1)
        name = id_
        if 'name' in conf:
            name = conf['name']
        _category = "sensor"
        _class = "distance"
        _subclass = "sonar"
        _pack = package["name"]
        _namespace = package["namespace"]

        super().__init__(id_, auto_start=False)
        self.set_simulation_communication(_namespace)

        info = {
            "type": "SONAR",
            "brand": "sonar",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": name,
            "place": conf["place"],
            "id": id_,
            "enabled": True,
            "orientation": float(conf["orientation"]),
            "hz": conf["hz"],
            "queue_size": 100,
            "mode": package["mode"],
            "namespace": package["namespace"],
            "max_range": conf["max_range"],
            "device_name": package["device_name"],
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
        self.name = info['name']
        self.map = package["map"]
        self.base_topic = info["base_topic"]
        self.derp_data_key = info["base_topic"] + ".raw"

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
            "namespace": _namespace,
        }
        tf_package['host'] = package['device_name']
        tf_package['host_type'] = 'robot'
        if 'host' in conf:
            tf_package['host'] = conf['host']
            tf_package['host_type'] = 'pan_tilt'

        self.tf_declare_rpc.call(tf_package)

        self.publisher = self.commlib_factory.getPublisher(
            topic = self.base_topic + ".data"
        )

        # print(self.info)

        if self.info["mode"] == "simulation":
            self.robot_pose_sub = self.commlib_factory.getSubscriber(
                topic = self.info['namespace'] + '.' + self.info['device_name'] + ".pose.internal",
                callback = self.robot_pose_update
            )

            self.get_tf_rpc = self.commlib_factory.getRPCClient(
                rpc_name = self.info['namespace'] + ".tf.get_tf"
            )

        self.robot_pose = None

        # Start commlib factory due to robot subscriptions (msub)
        self.commlib_factory.run()

        self.sensor_read_thread = None

    def robot_pose_update(self, message):
        """
        Updates the robot's pose with the given message.

        Args:
            message (dict): A dictionary containing the robot's pose information.
        """
        self.robot_pose = message

    def sensor_read(self):
        """
        Reads sensor data in a loop and publishes the distance value.
        This method runs in a loop, reading the sensor data at a frequency specified
        by `self.info["hz"]`. It supports two modes: "mock" and "simulation".
        In "mock" mode, it generates a random distance value between 10 and 30.
        In "simulation" mode, it calculates the distance based on the sensor's position
        and orientation, and the map data. It uses the `get_tf_rpc` service to get the
        sensor's position and orientation, and then calculates the distance to the nearest
        obstacle in the map.
        The calculated distance is then published along with a timestamp.
        If an error occurs during the sensor read process, a warning is logged.
        The loop continues until `self.info["enabled"]` is set to False.
        Logs:
            - Debug: When the sensor read thread starts and stops.
            - Warning: If an error occurs during the sensor read process.
        Publishes:
            - A dictionary containing the distance and timestamp.
        Raises:
            - None
        """
        self.logger.debug("Sonar %s sensor read thread started", self.info["id"])
        while self.info["enabled"]:
            time.sleep(1.0 / self.info["hz"])
            if self.robot_pose is None:
                continue

            val = 0
            if self.info["mode"] == "mock":
                val = float(random.uniform(30, 10))
            elif self.info["mode"] == "simulation":
                try:
                    # Get the place of the sensor from tf
                    res = self.get_tf_rpc.call({
                        "name": self.info["name"]
                    })
                    ths = res['theta']
                    # Calculate distance
                    d = 1
                    originx = res["x"] / self.robot_pose["resolution"]
                    originy = res["y"] / self.robot_pose["resolution"]
                    tmpx = originx
                    tmpy = originy
                    # print("Sonar: ", originx, originy)
                    limit = self.info["max_range"] / self.robot_pose["resolution"]
                    while self.map[int(tmpx), int(tmpy)] == 0 and d < limit:
                        d += 1
                        tmpx = originx + d * math.cos(ths)
                        tmpy = originy + d * math.sin(ths)
                    val = d * self.robot_pose["resolution"] + random.uniform(-0.03, 0.03)
                    if val > self.info["max_range"]:
                        val = self.info["max_range"]
                    if val < 0:
                        val = 0
                except Exception as e: # pylint: disable=broad-except
                    self.logger.warning("Error in sonar %s sensor read thread: %s", \
                        self.name, str(e))

            # Publishing value:
            self.publisher.publish({
                "distance": val,
                "timestamp": time.time()
            })
            # self.logger.info("Sonar reads: %f",  val)

        self.logger.debug("Sonar %s sensor read thread stopped", self.info["id"])

    def start(self):
        """
        Starts the sensor and begins reading data if enabled.
        This method logs the initial state of the sensor and waits for the simulator to start.
        Once the simulator has started, it checks if the sensor is enabled. If enabled, it starts
        a new thread to read sensor data at the specified frequency.
        Logs:
            - "Sensor {name} waiting to start" before the simulator starts.
            - "Sensor {name} started" after the simulator has started.
            - "Sonar {id} reads with {hz} Hz" if the sensor is enabled and reading data.
        Attributes:
            self.logger (Logger): Logger instance for logging sensor status.
            self.simulator_started (bool): Flag indicating if the simulator has started.
            self.info (dict): Dictionary containing sensor configuration, including:
                - "enabled" (bool): Flag indicating if the sensor is enabled.
                - "id" (str): Sensor identifier.
                - "hz" (int): Frequency at which the sensor reads data.
            self.sensor_read_thread (Thread): Thread instance for reading sensor data.
        """
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)
        self.logger.info("Sensor %s started", self.name)

        if self.info["enabled"]:
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info("Sonar %s reads with %s Hz", self.info["id"], self.info["hz"])

    def stop(self):
        """
        Stops the sonar controller by disabling it and stopping the communication library.

        This method sets the "enabled" flag in the info dictionary to False and calls the
        stop method on the commlib_factory to halt any ongoing communication processes.
        """
        self.info["enabled"] = False
        self.commlib_factory.stop()
