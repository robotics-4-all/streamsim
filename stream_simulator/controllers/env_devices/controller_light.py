"""
File that contains the light controller.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging

from stream_simulator.base_classes import BaseThing

class EnvLightController(BaseThing):
    """
    EnvLightController is a class that manages the control of environmental light devices.
    Attributes:
        logger (logging.Logger): Logger instance for logging information.
        info (dict): Information about the light device including type, base_topic, name, place, 
            enabled status, mode, configuration, and categorization.
        pose (dict): Pose information of the light device.
        name (str): Name of the light device.
        base_topic (str): Base topic for communication.
        place (str): Place where the light device is located.
        luminosity (float): Luminosity level of the light device.
        color (dict): Color information of the light device in RGBA format.
        range (float): Range of the light device.
        host (str): Host information if available.
    Methods:
        __init__(conf=None, package=None):
            Initializes the EnvLightController with the given configuration and package.
        set_communication_layer(package):
            Sets up the communication layer for the light device.
        enable_callback(message):
            Callback function to enable the light device.
        disable_callback(message):
            Callback function to disable the light device.
        get_callback(message):
            Callback function to get the current state of the light device.
        set_callback(message):
            Callback function to set the state of the light device.
        start():
            Starts the light device and waits for the simulator to start.
        stop():
            Stops the light device and its associated RPC servers.
    """
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        super().__init__(conf["name"], auto_start=False)

        _type = "LIGHTS"
        _category = "actuator"
        _class = "visual"
        _subclass = "leds"

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

        self.info = info
        self.pose = info["conf"]["pose"]
        self.name = info["name"]
        self.base_topic = info["base_topic"]
        self.place = info["conf"]["place"]
        self.luminosity = info['conf']['luminosity']
        self.color = {
            'r': 255,
            'g': 255,
            'b': 255,
            'a': self.luminosity * 255.0 / 100
        }
        self.range = info["conf"]["range"]

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
            "range": self.range,
            "properties": {
                "color": self.color,
                "luminosity": self.luminosity
            }
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
        Configures the communication layer for the light controller.

        This method sets up various communication channels and RPCs (Remote Procedure Calls) 
        required for the light controller to function within the simulation environment.

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
        Returns a dictionary containing the current color and luminosity of the light.

        Args:
            _ (Any): Unused parameter.

        Returns:
            dict: A dictionary with keys "color" and "luminosity" representing the current state 
            of the light.
        """
        return {
            "color": self.color,
            "luminosity": self.luminosity
        }

    def set_callback(self, message):
        """
        Sets the callback for handling incoming messages to update the light controller's state.
        Args:
            message (dict): A dictionary containing the new values for the light controller. 
                            Expected keys are "r", "g", "b" for color components and "luminosity" 
                            for brightness.
        Updates:
            self.color (dict): Updates the 'r', 'g', 'b' values in the color dictionary.
            self.luminosity (float): Updates the luminosity value.
            self.color['a'] (float): Updates the alpha value based on the luminosity.
        Notifies:
            Sends a notification to the UI with the type "effector_command" and the updated 
            message data.
        Publishes:
            Publishes the updated message to the relevant topic.
        Returns:
            dict: An empty dictionary.
        """
        if "r" in message:
            self.color['r'] = message["r"]
        if "g" in message:
            self.color['g'] = message["g"]
        if "b" in message:
            self.color['b'] = message["b"]
        if "luminosity" in message:
            self.luminosity = message["luminosity"]
            self.color['a'] = self.luminosity * 255.0 / 100.0

        self.commlib_factory.notify_ui(
            type_ = "effector_command",
            data = {
                "name": self.name,
                "value": message
            }
        )
        self.publisher.publish(message)

        return {}

    def start(self):
        """
        Starts the sensor and waits for the simulator to start.
        This method logs a message indicating that the sensor is waiting to start.
        It then enters a loop, repeatedly checking if the simulator has started,
        and sleeps for 1 second between checks. Once the simulator has started,
        it logs a message indicating that the sensor has started.
        Note: The RPC server related lines are currently commented out.
        """
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)
        self.logger.info("Sensor %s started", self.name)

    def stop(self):
        """
        Stops the light controller by disabling it and stopping all associated RPC servers.

        This method performs the following actions:
        1. Sets the "enabled" status of the light controller to False.
        2. Stops the RPC server responsible for enabling the light.
        3. Stops the RPC server responsible for disabling the light.
        4. Stops the RPC server responsible for getting the light status.
        5. Stops the RPC server responsible for setting the light status.
        """
        self.info["enabled"] = False
        self.get_rpc_server.stop()
        self.set_rpc_server.stop()
