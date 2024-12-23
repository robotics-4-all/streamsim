"""
This file contains the controller class for an environmental relay.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import time

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

        self.pose = info["conf"]["pose"]

        self.info = info
        self.name = info["name"]
        self.base_topic = info["base_topic"]

        self.state = info["conf"]["initial_state"]
        self.allowed_states = info["conf"]["states"]
        self.place = info["conf"]["place"]

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
        self.set_enable_disable_rpcs(self.base_topic, self.enable_callback, self.disable_callback)
        self.set_effector_set_get_rpcs(self.base_topic, self.set_callback, self.get_callback)
        self.set_data_publisher(self.base_topic)

    def enable_callback(self, _):
        """
        Enables the callback by setting the "enabled" key in the info dictionary to True.
        Args:
            _ (Any): Placeholder argument, not used in the method.
        Returns:
            dict: A dictionary with the key "enabled" set to True.
        """
        self.info["enabled"] = True

        # self.enable_rpc_server.run()
        # self.disable_rpc_server.run()
        # self.get_rpc_server.run()
        # self.set_rpc_server.run()

        return {"enabled": True}

    def disable_callback(self, _):
        """
        Disables the callback by setting the "enabled" key in the info dictionary to False.

        Args:
            _ (Any): Unused parameter.

        Returns:
            dict: A dictionary with the "enabled" key set to False.
        """
        self.info["enabled"] = False
        return {"enabled": False}

    def get_callback(self, _):
        """
        Callback function that returns the current state of the relay.

        Args:
            _ (Any): Placeholder argument, not used in the function.

        Returns:
            dict: A dictionary containing the current state of the relay with the key 'state'.
        """
        return {"state": self.state}

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
        state = message["state"]
        if state not in self.allowed_states:
            self.logger.critical("Relay %s does not allow %s state", self.name, state)
            return {"state": self.state}

        self.commlib_factory.notify_ui(
            type_ = "effector_command",
            data = {
                "name": self.name,
                "value": {
                    "state": message["state"]
                }
            }
        )

        self.publisher.publish(message)
        self.state = state
        return {"state": self.state}

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

        # self.enable_rpc_server.run()
        # self.disable_rpc_server.run()
        # self.get_rpc_server.run()
        # self.set_rpc_server.run()

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
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()
        self.get_rpc_server.stop()
        self.set_rpc_server.stop()
