"""
This file contains the controller class for an IMU sensor.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging
import threading
import random

from stream_simulator.base_classes import BaseThing

class ImuController(BaseThing):
    """
    ImuController is a class that simulates an Inertial Measurement Unit (IMU) sensor.
    Attributes:
        logger (logging.Logger): Logger for the controller.
        info (dict): Dictionary containing sensor information and configuration.
        name (str): Name of the sensor.
        base_topic (str): Base topic for communication.
        derp_data_key (str): Key for raw data communication.
        robot (str): Name of the robot.
        prev_robot_pose (dict): Previous pose of the robot.
        publisher (Publisher): Publisher for sensor data.
        robot_pose_sub (Subscriber): Subscriber for robot pose updates.
        enable_rpc_server (RPCService): RPC service to enable the sensor.
        disable_rpc_server (RPCService): RPC service to disable the sensor.
    Methods:
        __init__(conf=None, package=None): Initializes the IMU controller with configuration and 
        package details.
        robot_pose_update(message): Updates the robot pose based on incoming messages.
        sensor_read(): Reads sensor data and publishes it at a specified frequency.
        enable_callback(message): Callback to enable the sensor and start reading data.
        disable_callback(message): Callback to disable the sensor and stop reading data.
        start(): Starts the sensor and begins reading data if enabled.
        stop(): Stops the sensor and communication.
    """
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        id_ = "d_imu_" + str(BaseThing.id + 1)
        name = id_
        if 'name' in conf:
            name = conf['name']
        _category = "sensor"
        _class = "imu"
        _subclass = "accel_gyro_magne_temp"
        _pack = package["name"]
        _namespace = package["namespace"]

        super().__init__(id_, auto_start=False)
        self.set_simulation_communication(_namespace)

        info = {
            "type": "IMU",
            "brand": "icm_20948",
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
            "device_name": package["device_name"],
            "categorization": {
                "host_type": "robot",
                "place": _pack.split(".")[-1],
                "category": _category,
                "class": _class,
                "subclass": ['acceleration', 'gyroscope', 'magnetometer'],
                "name": name
            }
        }

        self.info = info
        self.name = info["name"]
        self.base_topic = info["base_topic"]
        self.derp_data_key = info["base_topic"] + ".raw"
        self.robot = _pack.split(".")[-1]
        self.prev_robot_pose = None

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
            "namespace": _namespace
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

        if self.info["mode"] == "simulation":
            self.robot_pose_sub = self.commlib_factory.getSubscriber(
                topic = self.info['namespace'] + '.' + self.info['device_name'] + ".pose.internal",
                callback = self.robot_pose_update
            )
            # self.robot_pose_sub.run()

            self.robot_pose = {
                "x": 0,
                "y": 0,
                "theta": 0
            }

        # Start commlib factory due to robot subscriptions (msub)
        self.commlib_factory.run()

        self.sensor_read_thread = None

    def robot_pose_update(self, message):
        """
        Updates the robot's pose with the given message.
        If this is the first update, the previous robot pose is set to the current message
        and a timestamp is added. For subsequent updates, the previous robot pose is updated
        to the current robot pose before setting the new pose and timestamp.
        Args:
            message (dict): A dictionary containing the robot's pose information.
        """
        if self.prev_robot_pose is None:
            self.prev_robot_pose = message
            self.prev_robot_pose['timestamp'] = time.time()
        else:
            self.prev_robot_pose = self.robot_pose

        self.robot_pose = message
        self.robot_pose['timestamp'] = time.time()

    def sensor_read(self):
        """
        Reads sensor data at a specified frequency and publishes it to a sensor stream.
        This method runs in a loop while the sensor is enabled. Depending on the mode specified 
        in the sensor's configuration, it either generates mock data or simulates sensor data based 
        on the robot's pose.
        Mock mode:
            Generates constant acceleration values and random gyroscope and magnetometer values.
        Simulation mode:
            Generates random acceleration, gyroscope, and magnetometer values. If the robot is 
            moving, the acceleration values are adjusted accordingly.
        The generated sensor data is published to a sensor stream with a timestamp.
        Raises:
            None
        Logs:
            - Info: When the sensor read thread starts and stops.
            - Warning: If the robot's pose is not available in simulation mode.
        Returns:
            None
        """
        self.logger.info("IMU %s sensor read thread started", self.info["id"])
        while self.info["enabled"]:
            time.sleep(1.0 / self.info["hz"])
            val = {}

            if self.info["mode"] == "mock":
                val = {
                    "acceleration": {
                        "x": 1,
                        "y": 1,
                        "z": 1
                    },
                    "gyroscope": {
                        "yaw": random.uniform(0.3, -0.3),
                        "pitch": random.uniform(0.3, -0.3),
                        "roll": random.uniform(0.3, -0.3)
                    },
                    "magnetometer": {
                        "yaw": random.uniform(0.3, -0.3),
                        "pitch": random.uniform(0.3, -0.3),
                        "roll": random.uniform(0.3, -0.3)
                    }
                }

            elif self.info["mode"] == "simulation":
                try:
                    moving = 0
                    if time.time() - self.robot_pose['timestamp'] < 1.5:
                        # this means the pose is old and the robot has stopped
                        # print("moving")
                        moving = 1
                    val = {
                        "acceleration": {
                            "x": random.uniform(0.03, -0.03) + moving * 0.1,
                            "y": random.uniform(0.03, -0.03),
                            "z": random.uniform(0.03, -0.03)
                        },
                        "gyroscope": {
                            "yaw": random.uniform(0.03, -0.03),
                            "pitch": random.uniform(0.03, -0.03),
                            "roll": random.uniform(0.03, -0.03)
                        },
                        "magnetometer": {
                            "yaw": self.robot_pose["theta"] + random.uniform(0.03, -0.03),
                            "pitch": random.uniform(0.03, -0.03),
                            "roll": random.uniform(0.03, -0.03)
                        }
                    }
                except: # pylint: disable=bare-except
                    self.logger.warning("Pose not got yet..")

            # Publish data to sensor stream
            self.publisher.publish({
                "data": val,
                "timestamp": time.time()
            })

        self.logger.info("IMU %s sensor read thread stopped", self.info["id"])

    def start(self):
        """
        Starts the IMU sensor.
        This method logs the initial state of the sensor and waits for the simulator to start.
        Once the simulator has started, it checks if the sensor is enabled. If enabled, it starts
        a new thread to read sensor data at the specified frequency.
        Logging:
            Logs the waiting state of the sensor.
            Logs when the sensor has started.
            Logs the sensor's reading frequency if enabled.
        Threading:
            Starts a new thread to read sensor data if the sensor is enabled.
        """
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)
        self.logger.info("Sensor %s started", self.name)

        if self.info["enabled"]:
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info("IMU %s reads with %s Hz", self.info["id"], self.info["hz"])

    def stop(self):
        """
        Stops the IMU controller by disabling it and stopping the communication library.

        This method sets the "enabled" flag in the info dictionary to False, indicating
        that the IMU controller is no longer active. It also stops the communication
        library factory to cease any ongoing communication processes.
        """
        self.info["enabled"] = False
        self.commlib_factory.stop()
