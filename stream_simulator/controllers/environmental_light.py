"""
File that contains the light controller.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging
import threading

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

        info = self.generate_info(conf, package, _type, _category, _class, _subclass)

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
        self.automation = info["conf"]["automation"] if "automation" in info["conf"] else None
        self.proximity_mode = info["conf"]["proximity_mode"] \
            if "proximity_mode" in info["conf"] else False
        self.proximity_distance = info["conf"]["proximity_distance"] \
            if "proximity_distance" in info["conf"] and self.proximity_mode else 0

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

        if self.automation is not None:
            self.logger.warning("Relay %s is automated", self.name)
            self.stopped = False
            self.active = True
            self.automation_thread = threading.Thread(target = self.automation_thread_loop)
            self.automation_thread.start()

    def automation_thread_loop(self):
        """
        Manages the automation loop for the relay device.
        This method runs in a separate thread and controls the relay based on the 
        predefined automation steps. It supports reversing the steps and looping 
        through them based on the configuration.
        """
        self.logger.warning("Relay %s automation starts", self.name)
        self.stopped = False
        automation_steps = self.automation["steps"]
        step_index = -1
        reverse_mode = False
        while self.active:
            step_index += 1
            if step_index >= len(automation_steps):
                if self.automation["reverse"] and reverse_mode is False:
                    automation_steps.reverse()
                    step_index = 1
                    reverse_mode = True
                elif self.automation["reverse"] and reverse_mode is True:
                    if self.automation["loop"]:
                        automation_steps.reverse()
                        step_index = 1
                        reverse_mode = False
                    else:
                        self.active = False
                        break
                elif self.automation["reverse"] is False and self.automation["loop"]:
                    step_index = 0
                else:
                    self.active = False
                    break
            step = automation_steps[step_index]
            self.set_callback(step['state'])
            sleep = step['duration']
            while sleep > 0 and self.active: # to be preemptable
                time.sleep(0.1)
                sleep -= 0.1

        self.stopped = True
        self.logger.warning("Light %s automation stops", self.name)

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
        self.set_tf_distance_calculator_rpc(package)
        self.set_effector_set_get_rpcs(self.base_topic, None, self.get_callback)
        self.set_state_publisher_internal(package["namespace"])
        # Since it is an effector, we need to set the command subscriber
        self.set_command_subscriber(self.base_topic, self.set_callback)
        self.set_state_publisher(self.base_topic)

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
        if self.proximity_mode:
            # Check if we have an initiator in the message
            allowed_distance = self.proximity_distance
            if self.proximity_distance == 0:
                allowed_distance = 0.5
            if "initiator" in message:
                # Check his pose
                real_dist = self.tf_distance_calculator_rpc.call(
                    {"initiator": message["initiator"], "target": self.name}
                )
                if real_dist['distance'] is None or real_dist['distance'] > allowed_distance:
                    self.logger.info("Light %s is too far from %s", self.name, message["initiator"])
                    return {'state': {
                        "r": self.color['r'],
                        "g": self.color['g'],
                        "b": self.color['b'],
                        "luminosity": self.luminosity
                    }}

        if "r" in message:
            self.color['r'] = message["r"]
        if "g" in message:
            self.color['g'] = message["g"]
        if "b" in message:
            self.color['b'] = message["b"]
        if "luminosity" in message:
            self.luminosity = message["luminosity"]
            self.color['a'] = self.luminosity * 255.0 / 100.0

        self.state_publisher.publish({'state': message})
        self.state_publisher_internal.publish({"state": message, 'origin': self.name})
        self.logger.info("{%s: New lights command: %s", self.name, message)

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
        if self.automation is not None:
            self.active = False
            while not self.stopped:
                time.sleep(0.1)
        self.commlib_factory.stop()
