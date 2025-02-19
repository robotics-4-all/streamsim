"""
File that contains the ambient light controller.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import math
import logging
import threading
import random

from stream_simulator.base_classes import BaseThing

class EnvAmbientLightController(BaseThing):
    """
    EnvAmbientLightController is a class that simulates an ambient light sensor in an environment.
    Attributes:
        logger (logging.Logger): Logger for the controller.
        info (dict): Information about the sensor.
        name (str): Name of the sensor.
        base_topic (str): Base topic for communication.
        hz (float): Frequency of sensor readings.
        mode (str): Mode of operation.
        operation (str): Type of operation (e.g., constant, random, triangle, sinus).
        operation_parameters (dict): Parameters for the operation.
        place (str): Place where the sensor is located.
        pose (dict): Pose of the sensor.
        derp_data_key (str): Key for raw data.
        env_properties (dict): Environmental properties.
        host (str): Host information.
        prev (float): Previous value for certain operations.
        way (int): Direction for triangle operation.
        sensor_read_thread (threading.Thread): Thread for reading sensor data.
    Methods:
        __init__(conf=None, package=None): Initializes the controller with 
            configuration and package.
        set_communication_layer(package): Sets up the communication layer.
        get_mode_callback(message): Callback to get the current mode.
        set_mode_callback(message): Callback to set the mode.
        sensor_read(): Reads sensor data based on the operation mode.
        enable_callback(message): Enables the sensor.
        disable_callback(message): Disables the sensor.
        get_callback(message): Gets the current state.
        set_callback(message): Sets the state.
        start(): Starts the controller.
        stop(): Stops the controller.
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

        _type = "AMBIENT_LIGHT"
        _category = "sensor"
        _class = "visual"
        _subclass = "light_sensor"

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
        self.env_properties = package["env"]

        self.mock_parameters = {}

        self.tf_luminosity_rpc = None
        self.set_communication_layer(package)
        self.commlib_factory.run()

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


        self.tf_declare_rpc.call(tf_package)

        if self.operation == "triangle":
            self.prev = self.operation_parameters["triangle"]['min']
            self.way = 1
        elif self.operation == "sinus":
            self.prev = 0
        else:
            self.prev = None

        self.sensor_read_thread = None
        self.stopped = False
        self.state = conf['state'] if 'state' in conf else 'on'

    def set_communication_layer(self, package):
        """
        Configures the communication layer for the ambient light controller.

        This method sets up the necessary communication interfaces for the ambient light 
        controller, including TF communication, data publishing, and RPCs for enabling/
        disabling and mode setting/getting.

        Args:
            package (Any): The communication package to be used for setting 
            up the communication layer.
        """
        self.set_tf_distance_calculator_rpc(package)
        self.set_simulation_communication(package["namespace"])
        self.set_tf_communication(package)
        self.set_data_publisher(self.base_topic)
        self.set_sensor_state_interfaces(self.base_topic)

        self.tf_luminosity_rpc = self.commlib_factory.get_rpc_client(
            rpc_name = f"{package['namespace']}.tf.get_luminosity",
            auto_run = False
        )

    def sensor_read(self):
        """
        Reads sensor data and publishes the value at a specified frequency.
        This method operates in two modes: "mock" and "simulation". In "mock" mode, it generates
        sensor values based on predefined operation parameters such as constant, random, normal,
        triangle, and sinusoidal values. In "simulation" mode, it interacts with an external
        service to get environmental data and adjusts the luminosity based on the response.
        The method runs in a loop, reading sensor data and publishing it until the 
        sensor is disabled.
        Attributes:
            self.constant_value (float): Constant value for the sensor in "mock" mode.
            self.random_min (float): Minimum value for random generation in "mock" mode.
            self.random_max (float): Maximum value for random generation in "mock" mode.
            self.triangle_min (float): Minimum value for triangle wave generation in "mock" mode.
            self.triangle_max (float): Maximum value for triangle wave generation in "mock" mode.
            self.triangle_step (float): Step value for triangle wave generation in "mock" mode.
            self.normal_std (float): Standard deviation for normal distribution in "mock" mode.
            self.normal_mean (float): Mean value for normal distribution in "mock" mode.
            self.sinus_dc (float): DC offset for sinusoidal wave in "mock" mode.
            self.sinus_amp (float): Amplitude for sinusoidal wave in "mock" mode.
            self.sinus_step (float): Step value for sinusoidal wave in "mock" mode.
            self.hz (float): Frequency at which the sensor reads data.
            self.mode (str): Mode of operation, either "mock" or "simulation".
            self.operation (str): Type of operation for generating sensor values in "mock" mode.
            self.info (dict): Dictionary containing sensor status information.
            self.env_properties (dict): Dictionary containing environmental properties.
            self.publisher (object): Publisher object for publishing sensor data.
            self.logger (object): Logger object for logging information.
        Raises:
            Warning: If an unsupported operation is specified in "mock" mode.
        """
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

        val = None
        while self.info["enabled"]:
            time.sleep(1.0 / self.hz)

            if self.state is None or self.state == "off":
                continue

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
                res = self.tf_luminosity_rpc.call({
                    'name': self.name
                })
                val = res["luminosity"] + random.uniform(-0.25, 0.25)
                # print(val)

            # Publishing value:
            self.publisher.publish({
                "value": val,
                "timestamp": time.time()
            })

        self.stopped = True

    def get_callback(self, _):
        """
        Callback function to retrieve the current state.

        Args:
            _ (Any): Placeholder for an unused argument.

        Returns:
            dict: A dictionary containing the current state.
        """
        return {"state": self.state}

    def start(self):
        """
        Starts the ambient light controller by enabling and running the necessary RPC servers.
        This method performs the following actions:
        1. Runs the enable, disable, get_mode, and set_mode RPC servers.
        2. If the ambient light sensor is enabled, starts a new thread to read sensor data.
        Attributes:
            enable_rpc_server (RPCServer): Server to enable the ambient light sensor.
            disable_rpc_server (RPCServer): Server to disable the ambient light sensor.
            get_mode_rpc_server (RPCServer): Server to get the current mode of the 
                ambient light sensor.
            set_mode_rpc_server (RPCServer): Server to set the mode of the ambient 
                light sensor.
            info (dict): Dictionary containing the configuration and state of the 
                ambient light sensor.
            sensor_read_thread (threading.Thread): Thread to handle reading data 
                from the ambient light sensor.
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
        Stops the ambient light controller by disabling its functionality and 
        stopping all associated RPC servers.

        This method performs the following actions:
        - Sets the "enabled" status to False.
        - Stops the `enable_rpc_server`.
        - Stops the `disable_rpc_server`.
        - Stops the `get_mode_rpc_server`.
        - Stops the `set_mode_rpc_server`.
        """
        self.info["enabled"] = False
        while not self.stopped:
            time.sleep(0.1)
        self.logger.warning("Sensor %s stopped", self.name)
