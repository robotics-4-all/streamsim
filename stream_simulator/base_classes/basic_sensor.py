"""
File that contains the BasicSensor class.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import math
import logging
import threading
import random
import abc

from stream_simulator.base_classes import BaseThing

class BasicSensor(BaseThing):
    """
    BasicSensor is a class that represents a basic sensor with various 
    operational modes and configurations.
    Attributes:
        logger (logging.Logger): Logger instance for logging sensor activities.
        info (dict): Dictionary containing sensor information and configuration.
        name (str): Name of the sensor.
        base_topic (str): Base topic for sensor communication.
        hz (float): Frequency at which the sensor operates.
        mode (str): Operational mode of the sensor.
        operation (str): Type of operation the sensor performs.
        operation_parameters (dict): Parameters for the sensor's operation.
        place (str): Location of the sensor.
        pose (dict): Pose information of the sensor.
        derp_data_key (str): Key for raw data communication.
        prev (float): Previous value for certain operations.
        way (int): Direction for the triangle operation.
        sensor_read_thread (threading.Thread): Thread for reading sensor data.
    Methods:
        __init__(conf, package, _type, _category, _class, _subclass):
            Initializes the BasicSensor with the given configuration and package.
        get_mode_callback(message):
            Callback to get the current mode and parameters of the sensor.
        set_mode_callback(message):
            Callback to set the mode and parameters of the sensor.
        sensor_read():
            Reads sensor data based on the current mode and operation.
        get_simulation_value():
            Abstract method to get the simulation value for the sensor.
        enable_callback(message):
            Callback to enable the sensor.
        disable_callback(message):
            Callback to disable the sensor.
        get_callback(message):
            Callback to get the current state of the sensor.
        set_callback(message):
            Callback to set the state of the sensor.
        start():
            Starts the sensor and its communication servers.
        stop():
            Stops the sensor and its communication servers.
    """
    def __init__(self,
                 conf = None,
                 package = None,
                 _type = None,
                 _category = None,
                 _class = None,
                 _subclass = None):

        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        super().__init__(conf["name"], auto_start=False)
        super().set_conf(conf)

        self.set_tf_communication(package)
        self.set_simulation_communication(package["namespace"])
        self.set_tf_distance_calculator_rpc(package)
        
        _simname = package["namespace"]
        _name = conf["name"]
        _pack = package["base"]
        _place = conf["place"]

        info = {
            "type": _type,
            "base_topic": f"{_simname}.{_pack}.{_place}.{_category}.{_class}.{_subclass}.{_name}",
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

        self.set_sensor_state_interfaces(info["base_topic"])

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

        self.mock_parameters = {}

        # Communication
        self.set_data_publisher(self.base_topic)

        if self.mode == 'mock':
            if self.operation not in self.operation_parameters:
                self.logger.error("Operation parameters missing from %s: %s",
                                  self.name, self.operation)
                raise Exception( # pylint: disable=broad-exception-raised
                    f"Operation parameters missing from {self.name}: {self.operation}")

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

        self.commlib_factory.run()

    def get_mode_callback(self, _):
        """
        Callback function to get the current mode and its parameters.

        Args:
            _ (Any): Placeholder argument, not used in the function.

        Returns:
            dict: A dictionary containing the current mode and its associated parameters.
                - "mode" (str): The current operation mode.
                - "parameters" (dict): The parameters associated with the current operation mode.
        """
        return {
                "mode": self.operation,
                "parameters": self.operation_parameters[self.operation]
        }

    def set_mode_callback(self, message):
        """
        Sets the mode of the sensor based on the provided message.
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
        Reads sensor data based on the specified operation mode and parameters, and 
        publishes the value at a specified frequency.
        The method supports different operation modes such as "mock" and "simulation". 
        In "mock" mode, it generates values based on predefined operations like "constant", 
        "random", "normal", "triangle", and "sinus". In "simulation" mode, it retrieves 
        values from a simulation function.
        The method logs the start of the sensor read thread and any missing operation 
        parameters. It continuously reads and publishes sensor values while the sensor is 
        enabled.
        Raises:
            Exception: If there are missing operation parameters.
        Operations:
            - constant: Publishes a constant value.
            - random: Publishes a random value within a specified range.
            - normal: Publishes a value based on a normal distribution.
            - triangle: Publishes a value that oscillates in a triangular wave pattern.
            - sinus: Publishes a value based on a sinusoidal wave pattern.
        Logs:
            - Info: Start of the sensor read thread and published values.
            - Warning: Missing operation parameters or unsupported operations.
        Publishes:
            - A dictionary containing the sensor value and the current timestamp.
        """
        self.logger.info("Sensor %s read thread started", self.name)
        # Operation parameters

        if self.mode == "mock":
            try:
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
            except Exception as e: # pylint: disable=broad-exception-caught
                self.logger.warning(
                    "Missing operation parameters for %s: %s. Change operation with caution!", 
                    self.name, str(e))

        while self.info["enabled"]:
            time.sleep(1.0 / self.hz)
            print("Sensor read", self.state)

            if self.state is None or self.state == "off":
                continue

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
                val = self.get_simulation_value()

            self.publisher.publish({
                "value": val,
                "timestamp": time.time()
            })

        self.stopped = True

    @abc.abstractmethod
    def get_simulation_value(self):
        """
        Retrieve the simulation value for the sensor.

        Returns:
            None: This method currently returns None.
        """
        return None

    def enable_callback(self, _):
        """
        Enables the sensor by setting the "enabled" status to True and starting necessary 
        services and threads.
        Args:
            message (dict): A dictionary containing the message data (not used 
            in the current implementation).
        Returns:
            dict: A dictionary indicating that the sensor has been enabled with 
            the key "enabled" set to True.
        """
        self.info["enabled"] = True

        self.sensor_read_thread = threading.Thread(target = self.sensor_read)
        self.sensor_read_thread.start()

        return {"enabled": True}

    def disable_callback(self, _):
        """
        Disables the sensor callback by setting the "enabled" status to False.

        Args:
            _ (Any): Unused parameter.

        Returns:
            dict: A dictionary with the key "enabled" set to False.
        """
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        """
        Starts the sensor by enabling and running the necessary RPC servers and
        initiating the sensor read thread if the sensor is enabled.
        This method performs the following actions:
        1. Runs the enable RPC server.
        2. Runs the disable RPC server.
        3. Runs the get mode RPC server.
        4. Runs the set mode RPC server.
        5. If the sensor is enabled, starts a new thread to read sensor data.
        Attributes:
            info (dict): A dictionary containing sensor information, including
                         whether the sensor is enabled.
        """
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)

        if self.info["enabled"]:
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()

        self.logger.info("Sensor %s started", self.name)

    def stop(self):
        """
        Stops the sensor by disabling it and stopping all associated RPC servers.

        This method sets the sensor's "enabled" status to False and stops the following RPC servers:
        - enable_rpc_server
        - disable_rpc_server
        - get_mode_rpc_server
        - set_mode_rpc_server
        """
        self.info["enabled"] = False
        while not self.stopped:
            time.sleep(0.1)
        self.logger.warning("Sensor %s stopped", self.name)
        super().stop()
