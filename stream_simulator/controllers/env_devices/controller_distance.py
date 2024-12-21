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
        allowed_states (list): List of allowed states for the sensor.
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
        _name = conf["name"]
        _pack = package["base"]
        _place = conf["place"]
        _namespace = package["namespace"]
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

        self.robots_poses = {}
        self.robots_subscribers = {}
        self.constant_value = None
        self.random_min = None
        self.random_max = None
        self.triangle_min = None
        self.triangle_max = None
        self.triangle_step = None
        self.normal_std = None
        self.normal_mean = None
        self.sinus_dc = None
        self.sinus_amp = None
        self.sinus_step = None

        self.info = info
        self.name = info["name"]
        self.base_topic = info["base_topic"]
        self.hz = info['conf']['hz']
        self.mode = info["mode"]
        self.operation = info['conf']['operation']
        self.operation_parameters = info['conf']['operation_parameters']
        self.place = info["conf"]["place"]
        self.pose = info["conf"]["pose"]
        self.derp_data_key = info["base_topic"] + ".raw"
        self.map = package["map"]
        self.resolution = package["resolution"]
        self.max_range = info['conf']['max_range']
        self.get_device_groups_rpc_topic = package["namespace"] + ".get_device_groups"
        self.allowed_states = ["enabled", "disabled"]

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

        self.get_tf = self.commlib_factory.getRPCClient(
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
        self.set_enable_disable_rpcs(self.base_topic, self.enable_callback, self.disable_callback)
        self.set_mode_get_set_rpcs(self.base_topic, self.set_mode_callback, self.get_mode_callback)

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

    def get_mode_callback(self, _):
        """
        Callback function to retrieve the current operation mode and its parameters.

        Args:
            _ (Any): Placeholder argument, not used in the function.

        Returns:
            dict: A dictionary containing the current operation mode and its associated parameters.
                  The dictionary has the following structure:
                  {
                      "mode": <current_operation_mode>,
                      "parameters": <parameters_for_current_operation_mode>
        """
        return {
                "mode": self.operation,
                "parameters": self.operation_parameters[self.operation]
        }

    def set_mode_callback(self, message):
        """
        Callback function to set the operation mode based on the provided message.
        Parameters:
        message (dict): A dictionary containing the mode information. 
            Expected keys:
            - "mode" (str): The mode to set. Possible values are "triangle", "sinus", or other.
        Returns:
        dict: An empty dictionary.
        Behavior:
        - If the mode is "triangle", sets self.prev to the minimum value of the 
            "triangle" operation parameters and self.way to 1.
        - If the mode is "sinus", sets self.prev to 0.
        - For any other mode, sets self.prev to None.
        - Updates self.operation to the provided mode.
        """
        if message["mode"] == "triangle":
            self.prev = self.operation_parameters["triangle"]['min']
            self.way = 1
        elif message["mode"] == "sinus":
            self.prev = 0
        else:
            self.prev = None

        self.operation = message["mode"]
        return {}

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
        get_devices_rpc = self.commlib_factory.getRPCClient(
            rpc_name = self.get_device_groups_rpc_topic
        )

        res = get_devices_rpc.call({}, timeout=5)

        # create subscribers
        for r in res['robots']:
            self.robots_subscribers[r] = self.commlib_factory.getSubscriber(
                topic = f"robot.{r}.pose", # get poses from all robots
                callback = self.robot_pose_callback
            )
            # self.robots_subscribers[r].run()

        self.logger.info("Sensor %s read thread started", self.name)

        # Operation parameters
        self.constant_value = self.operation_parameters["constant"]['value']
        self.random_min = self.operation_parameters["random"]['min']
        self.random_max = self.operation_parameters["random"]['max']
        self.triangle_min = self.operation_parameters["triangle"]['min']
        self.triangle_max = self.operation_parameters["triangle"]['max']
        self.triangle_step = self.operation_parameters["triangle"]['step']
        self.normal_std = self.operation_parameters["normal"]['std']
        self.normal_mean = self.operation_parameters["normal"]['mean']
        self.sinus_dc = self.operation_parameters["sinus"]['dc']
        self.sinus_amp = self.operation_parameters["sinus"]['amplitude']
        self.sinus_step = self.operation_parameters["sinus"]['step']

        while self.info["enabled"]:
            time.sleep(1.0 / self.hz)

            val = None
            if self.mode == "mock":
                if self.operation == "constant":
                    val = self.constant_value
                elif self.operation == "random":
                    val = random.uniform(
                        self.random_min,
                        self.random_max
                    )
                elif self.operation == "normal":
                    val = random.gauss(
                        self.normal_mean,
                        self.normal_std
                    )
                elif self.operation == "triangle":
                    val = self.prev + self.way * self.triangle_step
                    if val >= self.triangle_max or val <= self.triangle_min:
                        self.way *= -1
                    self.prev = val
                elif self.operation == "sinus":
                    val = self.sinus_dc + self.sinus_amp * math.sin(self.prev)
                    self.prev += self.sinus_step
                else:
                    self.logger.warning("Unsupported operation: %s", self.operation)

            elif self.mode == "simulation":
                # Get pose of the sensor (in case it is on a pan-tilt)
                pp = self.get_tf.call({
                    "name": self.name
                })
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

                val = d * self.resolution

            val += random.uniform(-0.02, 0.02)
            # Publishing value:
            self.publisher.publish({
                "value": val,
                "timestamp": time.time()
            })
            # print(val)

    def enable_callback(self, _):
        """
        Enables the callback by setting the 'enabled' flag to True and starting the 
        sensor read thread.
        Args:
            _ (Any): Placeholder argument, not used in the method.
        Returns:
            dict: A dictionary indicating that the callback has been enabled with 
            the key 'enabled' set to True.
        """
        self.info["enabled"] = True

        # self.enable_rpc_server.run()
        # self.disable_rpc_server.run()
        # self.get_mode_rpc_server.run()
        # self.set_mode_rpc_server.run()

        self.sensor_read_thread = threading.Thread(target = self.sensor_read)
        self.sensor_read_thread.start()

        return {"enabled": True}

    def disable_callback(self, _):
        """
        Disables the callback by setting the "enabled" status to False.

        Args:
            message (dict): The message received (not used in this method).

        Returns:
            dict: A dictionary indicating that the "enabled" status is now False.
        """
        self.info["enabled"] = False
        return {"enabled": False}

    def get_callback(self, _):
        """
        Callback function to handle incoming messages.

        Args:
            message (Any): The incoming message to be processed.

        Returns:
            dict: A dictionary containing the current state.
        """
        return {"state": self.state}

    def set_callback(self, message):
        """
        Sets the state of the device based on the provided message.
        Args:
            message (dict): A dictionary containing the state information. 
                            It must have a key "state" with the desired state as its value.
        Raises:
            Exception: If the provided state is not in the list of allowed states.
        Returns:
            dict: A dictionary containing the updated state of the device.
        """
        state = message["state"]
        if state not in self.allowed_states:
            raise Exception(f"{self.name} does not allow {state} state") # pylint: disable=broad-exception-raised

        self.state = state
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

        # self.enable_rpc_server.run()
        # self.disable_rpc_server.run()
        # self.get_mode_rpc_server.run()
        # self.set_mode_rpc_server.run()

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
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()
        self.get_mode_rpc_server.stop()
        self.set_mode_rpc_server.stop()
