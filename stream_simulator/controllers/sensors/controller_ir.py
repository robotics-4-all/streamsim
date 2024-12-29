"""
File that contains the IR controller.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import math
import logging
import threading
import random

from stream_simulator.base_classes import BaseThing

class IrController(BaseThing):
    """
    IrController is a class that simulates an infrared (IR) sensor controller.
    Attributes:
        logger (logging.Logger): Logger for the controller.
        info (dict): Information about the IR sensor.
        name (str): Name of the IR sensor.
        map (np.array): Map data for the simulation.
        base_topic (str): Base topic for communication.
        derp_data_key (str): Key for raw data communication.
        publisher (Publisher): Publisher for sensor data.
        enable_rpc_server (RPCService): RPC service to enable the sensor.
        disable_rpc_server (RPCService): RPC service to disable the sensor.
        robot_pose_sub (Subscriber): Subscriber for robot pose updates.
        get_tf_rpc (RPCClient): RPC client to get transformation data.
        commlib_factory (CommlibFactory): Communication library factory.
        robot_pose (dict): Current pose of the robot.
        sensor_read_thread (threading.Thread): Thread for reading sensor data.
    Methods:
        __init__(conf=None, package=None): Initializes the IR controller with configuration and 
        package information.
        robot_pose_update(message): Updates the robot pose based on the received message.
        sensor_read(): Reads the sensor data and publishes it.
        enable_callback(message): Callback to enable the sensor.
        disable_callback(message): Callback to disable the sensor.
        start(): Starts the sensor controller.
        stop(): Stops the sensor controller.
    """
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        id_ = "d_ir_" + str(BaseThing.id + 1)
        name = id_
        if 'name' in conf:
            name = conf['name']
        _category = "sensor"
        _class = "distance"
        _subclass = "ir"
        _pack = package["name"]
        _namespace = package["namespace"]

        super().__init__(id_, auto_start=False)
        self.set_simulation_communication(_namespace)

        info = {
            "type": "IR",
            "brand": "ir",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": name,
            "place": conf["place"],
            "id": "id_" + str(id_),
            "enabled": True,
            "orientation": float(conf["orientation"]),
            "hz": conf["hz"],
            "queue_size": 100,
            "mode": package["mode"],
            "namespace": package["namespace"],
            "device_name": package["device_name"],
            "max_range": conf["max_range"],
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

            self.get_tf_rpc = self.commlib_factory.getRPCClient(
                rpc_name = self.info['namespace'] + ".tf.get_tf"
            )

        # Start commlib factory due to robot subscriptions (msub)
        self.commlib_factory.run()

        self.robot_pose = None
        self.sensor_read_thread = None

    def robot_pose_update(self, message):
        """
        Updates the robot's pose with the given message.

        Args:
            message: The new pose information to update the robot's pose.
        """
        self.robot_pose = message

    def sensor_read(self):
        """
        Reads sensor data in a loop and publishes the distance value.
        This method runs in a loop while the sensor is enabled. It reads the sensor data
        at a frequency specified by the sensor's "hz" parameter. Depending on the mode
        ("mock" or "simulation"), it either generates a mock value or calculates the
        distance based on the sensor's position and orientation.
        In "mock" mode, it generates a random distance value between 10 and 30.
        In "simulation" mode, it calculates the distance to the nearest obstacle using
        the sensor's position and orientation obtained from a transformation service.
        The calculated or generated distance value is then published along with a timestamp.
        Raises:
            Exception: If there is an error in obtaining the sensor's position and orientation.
        Logs:
            Info: When the sensor read thread starts and stops.
            Warning: If the sensor's position and orientation are not obtained.
        """
        self.logger.info("Ir %s sensor read thread started", self.info["id"])
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
                    val = d * self.robot_pose["resolution"] + random.uniform(-0.03, 0.03)
                except: # pylint: disable=bare-except
                    self.logger.warning("Pose not got yet..")

            # Publishing value:
            self.publisher.publish({
                "distance": val,
                "timestamp": time.time()
            })
            # self.logger.info("Ir %s sensor read: %f", self.info["id"], val)

        self.logger.info("Ir %s sensor read thread stopped", self.info["id"])

    def start(self):
        """
        Starts the sensor and begins reading data if enabled.
        This method logs the initial state of the sensor and waits for the simulator to start.
        Once the simulator has started, it checks if the sensor is enabled. If enabled, it starts
        a new thread to read sensor data at the specified frequency.
        Logging:
            Logs the waiting state of the sensor.
            Logs when the sensor has started.
            Logs the sensor reading frequency if enabled.
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
            self.logger.info("Ir %s reads with %s Hz", self.info["id"], self.info["hz"])

    def stop(self):
        """
        Stops the IR sensor controller by disabling it and stopping the communication library.

        This method sets the "enabled" flag in the info dictionary to False and calls the
        stop method on the commlib_factory to halt any ongoing communication processes.
        """
        self.info["enabled"] = False
        self.commlib_factory.stop()
