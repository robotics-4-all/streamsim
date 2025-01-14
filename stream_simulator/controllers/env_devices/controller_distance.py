"""
File that contains the controller for the distance sensor.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import math
import logging
import threading
import random

from stream_simulator.base_classes import BaseThing

class EnvDistanceController(BaseThing):
    """
    EnvDistanceController is a class that simulates a distance sensor in an environment. 
    It inherits from BaseThing.
    Attributes:
        logger (logging.Logger): Logger for the controller.
        robots_poses (dict): Dictionary to store the poses of robots.
        info (dict): Information about the sensor.
        name (str): Name of the sensor.
        base_topic (str): Base topic for communication.
        hz (int): Frequency of sensor readings.
        mode (str): Mode of operation.
        operation (str): Type of operation.
        operation_parameters (dict): Parameters for the operation.
        place (str): Place where the sensor is located.
        pose (dict): Pose of the sensor.
        derp_data_key (str): Key for raw data.
        map (np.array): Map of the environment.
        resolution (float): Resolution of the map.
        max_range (float): Maximum range of the sensor.
        get_device_groups_rpc_topic (str): RPC topic to get device groups.
        host (str): Host of the sensor.
        get_tf (RPCClient): RPC client to get the transform.
        sensor_read_thread (threading.Thread): Thread for reading sensor data.
    Methods:
        __init__(conf=None, package=None): Initializes the EnvDistanceController.
        set_communication_layer(package): Sets up the communication layer.
        robot_pose_callback(message): Callback for robot pose updates.
        get_mode_callback(message): Callback to get the current mode.
        set_mode_callback(message): Callback to set the mode.
        sensor_read(): Reads sensor data and publishes it.
        enable_callback(message): Callback to enable the sensor.
        disable_callback(message): Callback to disable the sensor.
        get_callback(message): Callback to get the current state.
        set_callback(message): Callback to set the state.
        start(): Starts the sensor.
        stop(): Stops the sensor.
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

        _type = "DISTANCE"
        _category = "sensor"
        _class = "distance"
        _subclass = "sonar"
        
        self.robots_poses = {}
        self.robots_subscribers = {}

        info = self.generate_info(conf, package, _type, _category, _class, _subclass)
        self.info = info
        self.name = info["name"]
        self.base_topic = info["base_topic"]
        self.hz = info['conf']['hz']
        self.mode = info["mode"]
        self.operation = info['conf']['operation'] if 'operation' in info['conf'] else None
        self.operation_parameters = info['conf']['operation_parameters'] \
            if 'operation_parameters' in info['conf'] else None
        self.place = info["conf"]["place"]
        self.pose = info["conf"]["pose"]
        self.derp_data_key = info["base_topic"] + ".raw"
        self.map = package["map"]
        self.resolution = package["resolution"]
        self.max_range = info['conf']['max_range']
        self.get_device_groups_rpc_topic = package["namespace"] + ".get_device_groups"

        # tf handling
        tf_package = {
            "type": "env",
            "subtype": {
                "category": _category,
                "class": _class,
                "subclass": [_subclass]
            },
            "pose": self.pose,
            "base_topic": self.base_topic,
            "name": self.name
        }

        self.host = None
        if 'host' in info['conf']:
            self.host = info['conf']['host']
            tf_package['host'] = self.host
            # No other host type is available for env_devices
            tf_package['host_type'] = 'pan_tilt'

        self.set_communication_layer(package)

        self.get_tf = self.commlib_factory.get_rpc_client(
            rpc_name = package["namespace"] + ".tf.get_tf"
        )

        self.commlib_factory.run()

        self.tf_declare_rpc.call(tf_package)

        if self.operation == "triangle":
            self.prev = self.operation_parameters["triangle"]['min']
            self.way = 1
        elif self.operation == "sinus":
            self.prev = 0
        else:
            self.prev = None

        self.sensor_read_thread = None
        self.state = "enabled"
        self.mock_parameters = {}

    def set_communication_layer(self, package):
        """
        Configures the communication layer for the simulation environment.

        This method sets up various communication channels and RPCs (Remote Procedure Calls)
        required for the simulation environment to function correctly.

        Args:
            package (dict): A dictionary containing configuration details for the communication
                            layer. Expected keys include:
                            - "namespace": The namespace for the simulation communication.
                            - Other keys required by set_tf_communication and other methods.

        Methods called:
            - set_simulation_communication(namespace): Sets up the simulation 
            communication using the provided namespace.
            - set_tf_communication(package): Configures the TF (Transform) communication 
            using the provided package.
            - set_data_publisher(base_topic): Sets up the data publisher using the base topic.
            - set_enable_disable_rpcs(base_topic, enable_callback, disable_callback):
            Configures the enable/disable RPCs.
            - set_mode_get_set_rpcs(base_topic, set_mode_callback, get_mode_callback):
            Configures the mode get/set RPCs.
        """
        self.set_simulation_communication(package["namespace"])
        self.set_tf_communication(package)
        self.set_data_publisher(self.base_topic)

    def robot_pose_callback(self, message):
        """
        Callback function to update the pose of a robot.

        Args:
            message (dict): A dictionary containing the robot's pose information.
                - 'name' (str): The name of the robot, expected to be in the format 
                    'prefix.robot_name'.
                - 'x' (float): The x-coordinate of the robot's position.
                - 'y' (float): The y-coordinate of the robot's position.

        Updates:
            self.robots_poses (dict): A dictionary where the key is the robot's
            name and the value is another dictionary
            containing the 'x' and 'y' coordinates of the robot's position, 
            adjusted by the resolution.
        """
        nm = message['name'].split(".")[-1]
        if nm not in self.robots_poses:
            self.robots_poses[nm] = {
                'x': 0,
                'y': 0
            }
        self.robots_poses[nm]['x'] = message['x'] / self.resolution
        self.robots_poses[nm]['y'] = message['y'] / self.resolution

    def sensor_read(self):
        """
        Reads sensor data and publishes it at a specified frequency.
        This method performs the following steps:
        1. Retrieves all devices and checks if pan-tilts exist.
        2. Creates subscribers for each robot to get their poses.
        3. Logs the start of the sensor read thread.
        4. Initializes operation parameters for different modes of operation.
        5. Continuously reads sensor data at the specified frequency (`self.hz`).
        Depending on the mode (`self.mode`), the sensor data is generated differently:
        - "mock": Generates sensor data based on the specified operation type 
          (constant, random, normal, triangle, sinus).
        - "simulation": Simulates sensor data based on the sensor's pose and the 
          positions of robots and obstacles in the map.
        The generated sensor data is then published with a small random noise added.
        Parameters:
        None
        Returns:
        None
        """
        # Get all devices and check pan-tilts exist
        get_devices_rpc = self.commlib_factory.get_rpc_client(
            rpc_name = self.get_device_groups_rpc_topic
        )

        res = get_devices_rpc.call({}, timeout=5)

        # create subscribers
        for r in res['robots']:
            self.robots_subscribers[r] = self.commlib_factory.get_subscriber(
                topic = f"robot.{r}.pose", # get poses from all robots
                callback = self.robot_pose_callback
            )
            # self.robots_subscribers[r].run()

        self.logger.info("Sensor %s read thread started", self.name)

        # Operation parameters
        if self.mode == "mock":
            self.mock_parameters = {
                "constant_value": self.operation_parameters["constant"]['value'],
                "random_min": self.operation_parameters["random"]['min'],
                "random_max": self.operation_parameters["random"]['max'],
                "triangle_min": self.operation_parameters["triangle"]['min'],
                "triangle_max": self.operation_parameters["triangle"]['max'],
                "triangle_step": self.operation_parameters["triangle"]['step'],
                "normal_std": self.operation_parameters["normal"]['std'],
                "normal_mean": self.operation_parameters["normal"]['mean'],
                "sinus_dc": self.operation_parameters["sinus"]['dc'],
                "sinus_amp": self.operation_parameters["sinus"]['amplitude'],
                "sinus_step": self.operation_parameters["sinus"]['step']
            }

        while self.info["enabled"]:
            time.sleep(1.0 / self.hz)

            val = None
            if self.mode in ["mock"]:
                if self.operation == "constant":
                    val = self.mock_parameters['constant_value']
                elif self.operation == "random":
                    val = random.uniform(
                        self.mock_parameters['random_min'],
                        self.mock_parameters['random_max']
                    )
                elif self.operation == "normal":
                    val = random.gauss(
                        self.mock_parameters['normal_mean'],
                        self.mock_parameters['normal_std']
                    )
                elif self.operation == "triangle":
                    val = self.prev + self.way * self.mock_parameters['triangle_step']
                    if val >= self.mock_parameters['triangle_max'] or \
                        val <= self.mock_parameters['triangle_min']:
                        self.way *= -1
                    self.prev = val
                elif self.operation == "sinus":
                    val = self.mock_parameters['sinus_dc'] + \
                        self.mock_parameters['sinus_amp'] * math.sin(self.prev)
                    self.prev += self.mock_parameters['sinus_step']
                else:
                    self.logger.warning("Unsupported operation: %s", self.operation)

            elif self.mode == "simulation":
                # Get pose of the sensor (in case it is on a pan-tilt)
                pp = self.get_tf.call({
                    "name": self.name
                })
                # print(pp)
                xx = pp['x'] / self.resolution
                yy = pp['y'] / self.resolution
                th = pp['theta']

                d = 1
                tmpx = int(xx)
                tmpy = int(yy)
                limit = self.max_range / self.resolution
                robot = False
                while self.map[int(tmpx), int(tmpy)] == 0 and d < limit and robot is False:
                    d += 1
                    tmpx = xx + d * math.cos(th)
                    tmpy = yy + d * math.sin(th)

                    # Check robots atan2
                    for r, pose in self.robots_poses.items():
                        dd = math.sqrt(
                            math.pow(tmpy - pose['y'], 2) + \
                            math.pow(tmpx - pose['x'], 2)
                        )
                        # print(dd, 0.5 / self.resolution)
                        if dd < (0.5 / self.resolution):
                            print(d * self.resolution)
                            robot = True

                    if int(tmpx) < 0 or int(tmpy) < 0 or int(tmpx) >= self.map.shape[0] or \
                        int(tmpy) >= self.map.shape[1]:
                        val = limit
                        break

                val = d * self.resolution

            val += random.uniform(-0.02, 0.02)
            # Publishing value:
            self.publisher.publish({
                "value": val,
                "timestamp": time.time()
            })

    def get_callback(self, _):
        """
        Callback function to handle incoming messages.

        Args:
            message (Any): The incoming message to be processed.

        Returns:
            dict: A dictionary containing the current state.
        """
        return {"state": self.state}

    def start(self):
        """
        Starts the sensor and waits for the simulator to start.
        This method logs the initial state of the sensor and enters a loop, 
        waiting for the simulator to start. Once the simulator has started, 
        it logs that the sensor has started. If the sensor is enabled, it 
        starts a new thread to read sensor data.
        Attributes:
            self.logger (Logger): Logger instance for logging information.
            self.name (str): Name of the sensor.
            self.simulator_started (bool): Flag indicating if the simulator has started.
            self.info (dict): Dictionary containing sensor information, including 
                              whether the sensor is enabled.
            self.sensor_read_thread (Thread): Thread for reading sensor data.
        """
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)
        self.logger.info("Sensor %s started", self.name)

        if self.info["enabled"]:
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()

    def stop(self):
        """
        Stops the controller by disabling it and stopping all RPC servers.

        This method sets the "enabled" flag to False and stops the following RPC servers:
        - enable_rpc_server
        - disable_rpc_server
        - get_mode_rpc_server
        - set_mode_rpc_server
        """
        self.info["enabled"] = False
