"""
File that contains the humidifier controller.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging

from stream_simulator.base_classes import BaseThing

class EnvHumidifierController(BaseThing):
    """
    EnvHumidifierController is a controller class for managing an environmental humidifier device.
    Attributes:
        logger (logging.Logger): Logger for the controller.
        info (dict): Information about the humidifier including type, base_topic, name, place, 
            enabled status, mode, configuration, and categorization.
        pose (dict): Pose information from the configuration.
        name (str): Name of the humidifier.
        base_topic (str): Base topic for communication.
        place (str): Place where the humidifier is located.
        humidity (float): Current humidity level.
        range (dict): Range of the humidifier.
        host (str): Host information if available.
    Methods:
        __init__(conf=None, package=None): Initializes the EnvHumidifierController with the given 
            configuration and package.
        set_communication_layer(package): Sets up the communication layer for the controller.
        enable_callback(message): Callback to enable the humidifier.
        disable_callback(message): Callback to disable the humidifier.
        get_callback(message): Callback to get the current humidity level.
        set_callback(message): Callback to set the humidity level.
        start(): Starts the humidifier controller.
        stop(): Stops the humidifier controller.
    """
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        super().__init__(conf["name"], auto_start=False)

        _type = "HUMIDIFIER"
        _category = "actuator"
        _class = "env"
        _subclass = "humidifier"

        info = self.generate_info(conf, package, _type, _category, _class, _subclass)

        self.info = info
        self.pose = info["conf"]["pose"]
        self.name = info["name"]
        self.base_topic = info["base_topic"]
        self.place = info["conf"]["place"]
        self.humidity = info['conf']['humidity']
        self.range = info['conf']['range']

        # tf handling
        tf_package = {
            "type": _class,
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
        Configures the communication layer for the humidifier controller.

        This method sets up various communication channels and RPCs (Remote Procedure Calls) 
        required for the humidifier controller to function properly within the simulation 
        environment.

        Args:
            package (dict): A dictionary containing configuration details. 
                            Expected keys include:
                            - "namespace": The namespace for the simulation communication.
        """
        self.set_simulation_communication(package["namespace"])
        self.set_tf_communication(package)
        self.set_data_publisher(self.base_topic)
        self.set_effector_set_get_rpcs(self.base_topic, self.set_callback, self.get_callback)

    def get_callback(self, _):
        """
        Callback function to retrieve the current humidity level.

        Args:
            _ (Any): Placeholder argument, not used in the function.

        Returns:
            dict: A dictionary containing the current humidity level with the key 'humidity'.
        """
        return {"humidity": self.humidity}

    def set_callback(self, message):
        """
        Sets the callback for handling humidity messages.
        Args:
            message (dict): A dictionary containing the humidity data.
        Returns:
            dict: An empty dictionary.
        """
        self.humidity = message["humidity"]
        self.publisher.publish({
            "humidity": self.humidity
        })

        return {}

    def start(self):
        """
        Starts the sensor and waits for the simulator to start.
        This method logs a message indicating that the sensor is waiting to start.
        It then enters a loop, sleeping for 1 second at a time, until the simulator
        has started. Once the simulator has started, it logs another message indicating
        that the sensor has started.
        Note: The RPC server methods are currently commented out.
        """
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)
        self.logger.info("Sensor %s started", self.name)

    def stop(self):
        """
        Stops the humidifier by disabling its functionality and stopping all associated RPC servers.

        This method performs the following actions:
        - Sets the "enabled" status of the humidifier to False.
        - Stops the enable RPC server.
        - Stops the disable RPC server.
        - Stops the get RPC server.
        - Stops the set RPC server.
        """
        self.info["enabled"] = False
        self.get_rpc_server.stop()
        self.set_rpc_server.stop()
