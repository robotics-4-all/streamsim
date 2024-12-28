"""
File that contains the TOF controller.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import math
import logging
import threading
import random

from stream_simulator.base_classes import BaseThing

class TofController(BaseThing):
    """
    TofController is a class that simulates a Time-of-Flight (TOF) sensor.
    Attributes:
        logger (logging.Logger): Logger for the controller.
        info (dict): Information about the TOF sensor.
        name (str): Name of the TOF sensor.
        map (Any): Map data for the sensor.
        base_topic (str): Base topic for communication.
        derp_data_key (str): Key for raw data communication.
        tf_declare_rpc (Any): RPC client for declaring TF.
        publisher (Any): Publisher for sensor data.
        enable_rpc_server (Any): RPC server for enabling the sensor.
        disable_rpc_server (Any): RPC server for disabling the sensor.
        robot_pose_sub (Any): Subscriber for robot pose updates (simulation mode).
        get_tf_rpc (Any): RPC client for getting TF data (simulation mode).
        sensor_read_thread (threading.Thread): Thread for reading sensor data.
        robot_pose (Any): Current pose of the robot.
    Methods:
        __init__(conf=None, package=None): Initializes the TOF controller.
        robot_pose_update(message): Updates the robot pose.
        sensor_read(): Reads sensor data and publishes it.
        enable_callback(message): Enables the sensor and starts reading data.
        disable_callback(message): Disables the sensor.
        start(): Starts the sensor.
        stop(): Stops the sensor.
    """
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        id_ = "d_tof_" + str(BaseThing.id + 1)
        name = id_
        if 'name' in conf:
            name = conf['name']
        _category = "sensor"
        _class = "distance"
        _subclass = "tof"
        _pack = package["name"]
        _namespace = package["namespace"]

        super().__init__(id_, auto_start=False)
        self.set_simulation_communication(_namespace)

        info = {
            "type": "TOF",
            "brand": "vl53l1x",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": "tof_" + str(id_),
            "place": conf["place"],
            "id": id_,
            "enabled": True,
            "orientation": float(conf["orientation"]),
            "hz": conf["hz"],
            "queue_size": 100,
            "mode": package["mode"],
            "speak_mode": package["speak_mode"],
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
        self.name = info["name"]
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
        tf_package['host'] = package['device_name'] if 'host' not in conf else conf['host']
        tf_package['host_type'] = 'robot' if 'host' not in conf else 'pan_tilt'

        self.tf_declare_rpc.call(tf_package)

        self.publisher = self.commlib_factory.getPublisher(
            topic = self.base_topic + ".data"
        )

        if self.info["mode"] == "simulation":
            self.robot_pose_sub = self.commlib_factory.getSubscriber(
                topic = self.info['namespace'] + '.' + self.info['device_name'] + ".pose.internal",
                callback = self.robot_pose_update,
                old_way=True
            )

            self.get_tf_rpc = self.commlib_factory.getRPCClient(
                rpc_name = self.info['namespace'] + ".tf.get_tf"
            )

        self.sensor_read_thread = None
        self.robot_pose = None

        # Start commlib factory due to robot subscriptions (msub)
        self.commlib_factory.run()

    def robot_pose_update(self, message):
        """
        Updates the robot's pose with the given message.

        Args:
            message: The new pose information to update the robot's pose.
        """
        self.robot_pose = message

    def sensor_read(self):
        """
        Reads sensor data in a separate thread and publishes the distance value.
        This method continuously reads data from the sensor based on the specified mode
        ("mock" or "simulation") and publishes the distance value at a rate defined by
        the sensor's frequency (hz). The method runs in a loop until the sensor is disabled.
        In "mock" mode, the distance value is randomly generated within a specified range.
        In "simulation" mode, the distance is calculated based on the sensor's position and
        orientation in the simulated environment.
        The method logs the start and stop of the sensor read thread, as well as any warnings
        if the sensor's pose is not available.
        Raises:
            Exception: If there is an error in retrieving the sensor's pose in simulation mode.
        Publishes:
            dict: A dictionary containing the distance value and the current timestamp.
        """
        self.logger.info("TOF %s sensor read thread started", self.info["id"])
        while self.info["enabled"]:
            time.sleep(1.0 / self.info["hz"])

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
                    limit = self.info["max_range"] / self.robot_pose["resolution"]
                    while self.map[int(tmpx), int(tmpy)] == 0 and d < limit:
                        d += 1
                        tmpx = originx + d * math.cos(ths)
                        tmpy = originy + d * math.sin(ths)
                    val = d * self.robot_pose["resolution"]
                except: # pylint: disable=bare-except
                    self.logger.warning("Pose not got yet..")

            # Publishing value:
            self.publisher.publish({
                "distance": val,
                "timestamp": time.time()
            })
            # self.logger.info("TOF %s sensor read: %f", self.info["id"], val)

        self.logger.info("TOF %s sensor read thread stopped", self.info["id"])

    def start(self):
        """
        Starts the sensor and begins reading data if enabled.
        This method logs the initial state of the sensor and waits for the simulator to start.
        Once the simulator has started, it logs that the sensor has started.
        If the sensor is enabled, it starts a new thread to read sensor data at the specified 
        frequency.
        Attributes:
            simulator_started (bool): Indicates whether the simulator has started.
            info (dict): Contains sensor configuration, including 'enabled', 'id', and 'hz'.
            sensor_read_thread (threading.Thread): The thread that reads sensor data.
        """
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)
        self.logger.info("Sensor %s started", self.name)

        if self.info["enabled"]:
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info("TOF %s reads with %s Hz", self.info["id"], self.info["hz"])

    def stop(self):
        """
        Stops the sensor by disabling it and stopping the communication library.

        This method sets the "enabled" flag in the info dictionary to False and 
        calls the stop method on the commlib_factory to halt any ongoing communication.
        """
        self.info["enabled"] = False
        self.commlib_factory.stop()
