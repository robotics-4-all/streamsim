"""
This file contains the controller class for an environmental relay.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import time
import threading

from stream_simulator.base_classes import BaseThing

class EnvRelayController(BaseThing):
    """
    EnvRelayController is a class that represents a relay controller in an environment simulation.
    Attributes:
        logger (logging.Logger): Logger instance for logging messages.
        info (dict): Dictionary containing information about the relay controller.
        name (str): Name of the relay controller.
        base_topic (str): Base topic for communication.
        state (str): Current state of the relay controller.
        allowed_states (list): List of allowed states for the relay controller.
        place (str): Place where the relay controller is located.
        pose (dict): Pose information of the relay controller.
        host (str): Host information for the relay controller.
        commlib_factory (CommlibFactory): Communication library factory instance.
    Methods:
        __init__(conf=None, package=None):
            Initializes the EnvRelayController instance with the given configuration and package.
        set_communication_layer(package):
            Sets up the communication layer for the relay controller.
        enable_callback(message):
            Callback function to enable the relay controller.
        disable_callback(message):
            Callback function to disable the relay controller.
        get_callback(message):
            Callback function to get the current state of the relay controller.
        set_callback(message):
            Callback function to set the state of the relay controller.
        start():
            Starts the relay controller.
        stop():
            Stops the relay controller.
    """
    def __init__(self, conf = None, package = None):
        self.logger = logging.getLogger(conf["name"]) if package['logger'] is None \
            else package['logger']

        super().__init__(conf["name"], auto_start=False)

        _type = "RELAY"
        _category = "actuator"
        _class = "switch"
        _subclass = "relay"

        info = self.generate_info(conf, package, _type, _category, _class, _subclass)

        self.pose = info["conf"]["pose"]

        self.info = info
        self.name = info["name"]
        self.base_topic = info["base_topic"]

        self.state = info["conf"]["initial_state"]
        self.allowed_states = info["conf"]["states"]
        self.place = info["conf"]["place"]
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
            "name": self.name
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
            self.set_value(step['state'])
            sleep = step['duration']
            while sleep > 0 and self.active: # to be preemptable
                time.sleep(0.1)
                sleep -= 0.1

        self.stopped = True
        self.logger.warning("Relay %s automation stops", self.name)

    def set_communication_layer(self, package):
        """
        Configures the communication layer for the environment devices controller.

        This method sets up various communication channels and RPCs (Remote Procedure Calls) 
        required for the simulation environment. It initializes the communication for 
        simulation, transformation, enabling/disabling functionalities, effector set/get 
        operations, and data publishing.

        Args:
            package (dict): A dictionary containing configuration details. Expected keys include:
                - "namespace": The namespace for the simulation communication.
                - Other keys required for setting up transformation communication and RPCs.
        """
        self.set_simulation_communication(package["namespace"])
        self.set_tf_communication(package)
        self.set_tf_distance_calculator_rpc(package)
        self.set_state_publisher_internal(package["namespace"])

        # Since it is an effector, we need to set the command subscriber
        self.set_command_subscriber(self.base_topic, self.set_callback)
        self.set_state_publisher(self.base_topic)

    def set_callback(self, message):
        """
        Sets the callback for handling relay state changes.
        Args:
            message (dict): A dictionary containing the state information. 
                            Expected to have a key "state" with the desired state value.
        Returns:
            dict: A dictionary containing the current state of the relay.
        Raises:
            None
        Logs:
            Critical: If the provided state is not in the allowed states, logs a critical message.
        Actions:
            - Notifies the UI with the effector command and state change.
            - Publishes the message to the publisher.
            - Updates the internal state of the relay.
        """
        if self.automation is not None:
            self.logger.info("Relay %s is automated, ignoring set command", self.name)
            return {"state": "automated"}
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
                    self.logger.info("Relay %s is too far from %s", self.name, message["initiator"])
                    self.state_publisher.publish({"state": self.state})
                    return {"state": self.state}

        self.logger.info("Relay %s set to %s", self.name, message["state"])
        self.set_value(message["state"])
        self.state_publisher.publish({"state": self.state})
        self.state_publisher_internal.publish({"state": self.state, 'origin': self.name})
        self.logger.info("Relay %s state published", self.name)
        return {"state": self.state}

    def set_value(self, value):
        """
        Sets the relay state to the given value.

        Args:
            value (str): The value to set the relay state to.
        """
        if value not in self.allowed_states:
            self.logger.critical("Relay %s does not allow %s state", self.name, value)
        else:
            self.state = value
            self.logger.info("Relay %s set to %s", self.name, value)

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
        Stops the relay controller by disabling it and stopping all associated RPC servers.

        This method performs the following actions:
        1. Sets the "enabled" status in the info dictionary to False.
        2. Stops the enable RPC server.
        3. Stops the disable RPC server.
        4. Stops the get RPC server.
        5. Stops the set RPC server.
        """
        self.info["enabled"] = False
        # Stopping the thread
        if self.automation is not None:
            self.active = False
            while not self.stopped:
                time.sleep(0.1)
        self.logger.info("Relay %s stopped", self.name)
