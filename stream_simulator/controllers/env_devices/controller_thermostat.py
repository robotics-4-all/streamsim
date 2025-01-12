"""
This file contains the controller class for an environmental thermostat.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import time

from stream_simulator.base_classes import BaseThing

class EnvThermostatController(BaseThing):
    """
    EnvThermostatController is a class that represents a thermostat controller in an environment 
    simulation.
    Attributes:
        logger (logging.Logger): Logger instance for logging messages.
        info (dict): Dictionary containing thermostat information and configuration.
        pose (dict): Pose information of the thermostat.
        name (str): Name of the thermostat.
        base_topic (str): Base topic for communication.
        place (str): Place where the thermostat is located.
        temperature (float): Current temperature setting of the thermostat.
        range (tuple): Temperature range of the thermostat.
        host (str): Host information if available.
    Methods:
        __init__(conf=None, package=None): Initializes the EnvThermostatController with 
        configuration and package.
        set_communication_layer(package): Sets up the communication layer for the thermostat.
        enable_callback(_): Callback function to enable the thermostat.
        disable_callback(_): Callback function to disable the thermostat.
        get_callback(_): Callback function to get the current temperature.
        set_callback(message): Callback function to set a new temperature.
        start(): Starts the thermostat controller.
        stop(): Stops the thermostat controller.
    """
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        super().__init__(conf["name"], auto_start=False)

        _type = "THERMOSTAT"
        _category = "actuator"
        _class = "env"
        _subclass = "thermostat"

        info = self.generate_info(conf, package, _type, _category, _class, _subclass)

        self.info = info
        self.pose = info["conf"]["pose"]
        self.name = info["name"]
        self.base_topic = info["base_topic"]
        self.place = info["conf"]["place"]
        self.temperature = info['conf']['temperature']
        self.range = info['conf']['range']

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
            "name": self.name,
            "range": self.range
        }

        self.host = None
        if 'host' in info['conf']:
            self.host = info['conf']['host']
            tf_package['host'] = self.host
            # No other host type is available for env_devices
            tf_package['host_type'] = 'pan_tilt'

        self.set_communication_layer(package)
        self.commlib_factory.run()

        self.tf_declare_rpc.call(tf_package)

    def set_communication_layer(self, package):
        """
        Configures the communication layer for the thermostat controller.

        This method sets up various communication channels and RPCs (Remote Procedure Calls) 
        required for the thermostat controller to function properly within the simulation 
        environment.

        Args:
            package (dict): A dictionary containing configuration details for setting up 
                            communication. Expected keys include:
                            - "namespace": The namespace for the simulation communication.
                            - Other keys required by the specific communication setup methods.

        Returns:
            None
        """
        self.set_simulation_communication(package["namespace"])
        self.set_tf_communication(package)
        self.set_effector_set_get_rpcs(self.base_topic, self.set_callback, self.get_callback)
        self.set_data_publisher(self.base_topic)

    def get_callback(self, _):
        """
        Retrieves the current temperature as a callback.

        Args:
            _ (Any): Placeholder argument, not used in the method.

        Returns:
            dict: A dictionary containing the current temperature with the key 'temperature'.
        """
        return {"temperature": self.temperature}

    def set_callback(self, message):
        """
        Sets the callback for the thermostat controller.
        This method updates the thermostat's temperature based on the incoming message,
        publishes the message to the publisher, and notifies the UI with the updated
        temperature information.
        Args:
            message (dict): A dictionary containing the temperature information. 
                            Expected to have a key "temperature" with its corresponding value.
        Returns:
            dict: An empty dictionary.
        """
        self.temperature = message["temperature"]
        self.publisher.publish(message)

        return {}

    def start(self):
        """
        Starts the thermostat sensor.
        This method logs a message indicating that the sensor is waiting to start.
        It then enters a loop, checking if the simulator has started. Once the 
        simulator has started, it logs another message indicating that the sensor 
        has started.
        Note:
            The method currently contains commented-out lines for enabling, 
            disabling, getting, and setting the RPC server, which are not executed.
        """
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)
        self.logger.info("Sensor %s started", self.name)

    def stop(self):
        """
        Stops the thermostat controller by disabling it and stopping all associated RPC servers.

        This method performs the following actions:
        - Sets the "enabled" status in the info dictionary to False.
        - Stops the enable RPC server.
        - Stops the disable RPC server.
        - Stops the get RPC server.
        - Stops the set RPC server.
        """
        self.info["enabled"] = False
        self.get_rpc_server.stop()
        self.set_rpc_server.stop()
