"""
This file is a controller for a pan-tilt device in the simulation environment.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import math
import logging
import threading

from stream_simulator.base_classes import BaseThing

class EnvPanTiltController(BaseThing):
    """
    EnvPanTiltController is a class that controls a pan-tilt device in a simulated environment.
    Attributes:
        logger (logging.Logger): Logger for the controller.
        pose (dict): Pose configuration of the device.
        info (dict): Information about the device.
        name (str): Name of the device.
        base_topic (str): Base topic for communication.
        mode (str): Operation mode of the device.
        place (str): Place where the device is located.
        pan (float): Current pan angle.
        tilt (float): Current tilt angle.
        limits (dict): Limits for pan and tilt angles.
        pan_range (float): Range of pan angles.
        tilt_range (float): Range of tilt angles.
        pan_dc (float): Direct current component of the pan angle.
        host (str): Host information.
        operation (str): Current operation mode.
        operation_parameters (dict): Parameters for the current operation mode.
    Methods:
        __init__(conf=None, package=None): Initializes the controller with configuration and 
            package.
        set_communication_layer(package): Sets up the communication layer for the controller.
        set_mode_callback(message): Callback to set the operation mode.
        get_mode_callback(_): Callback to get the current operation mode.
        thread_fun(): Function to run in a separate thread for mock mode.
        enable_callback(message): Callback to enable the device.
        disable_callback(_): Callback to disable the device.
        get_callback(_): Callback to get the current pan and tilt angles.
        set_callback(message): Callback to set the pan and tilt angles.
        start(): Starts the controller.
        stop(): Stops the controller.
    """
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        super().__init__(conf["name"], auto_start=False)

        _type = "PAN_TILT"
        _category = "actuator"
        _class = "motion"
        _subclass = "pan_tilt"

        info = self.generate_info(conf, package, _type, _category, _class, _subclass)

        self.pose = info["conf"]["pose"]

        self.info = info
        self.name = info["name"]
        self.base_topic = info["base_topic"]
        self.mode = info['conf']['mode']

        self.place = info["conf"]["place"]
        self.pan = 0
        self.tilt = 0
        self.limits = info['conf']['limits']
        # Turn to rads
        self.limits['pan']['min'] = float(self.limits['pan']['min']) * math.pi / 180.0
        self.limits['pan']['max'] = float(self.limits['pan']['max']) * math.pi / 180.0
        self.limits['tilt']['min'] = float(self.limits['tilt']['min']) * math.pi / 180.0
        self.limits['tilt']['max'] = float(self.limits['tilt']['max']) * math.pi / 180.0
        self.pan_range = \
            self.limits['pan']['max'] - self.limits['pan']['min']
        self.tilt_range = \
            self.limits['tilt']['max'] - self.limits['tilt']['min']
        self.pan_dc = \
            (self.limits['pan']['max'] + self.limits['pan']['min'])/2.0

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

        self.operation = info['conf']['operation']
        self.operation_parameters = info['conf']['operation_parameters']

        self.prev = 0
        self.hz = 0
        self.sinus_step = 0
        self.data_thread = None

    def set_communication_layer(self, package):
        """
        Configures the communication layer for the pan-tilt controller.

        This method sets up various communication channels and RPCs (Remote Procedure Calls) 
        required for the operation of the pan-tilt controller. It includes setting up 
        simulation communication, transform communication, enable/disable RPCs, effector 
        set/get RPCs, data publishing, and mode get/set RPCs.

        Args:
            package (dict): A dictionary containing configuration parameters. Expected keys 
                            include "namespace" and other necessary parameters for setting 
                            up communication.

        Raises:
            KeyError: If required keys are missing in the package dictionary.
        """
        self.set_simulation_communication(package["namespace"])
        self.set_tf_communication(package)
        self.set_effector_set_get_rpcs(self.base_topic, self.set_callback, self.get_callback)
        self.set_data_publisher(self.base_topic)

    # Only for mock mode
    def thread_fun(self):
        """
        Thread function to control the pan and tilt movements based on sinusoidal operation.
        This function runs in a loop while the 'enabled' flag in the 'info' dictionary is True.
        It updates the 'pan' value based on a sinusoidal function with parameters defined in
        'operation_parameters'. The updated 'pan' and 'tilt' values, along with the device 'name',
        are published at each iteration.
        Attributes:
            prev (float): Previous value of the sinusoidal function.
            hz (float): Frequency of the sinusoidal function.
            sinus_step (float): Step increment for the sinusoidal function.
        Behavior:
            - Sleeps for a duration based on the frequency 'hz'.
            - Updates the 'pan' value using a sinusoidal function.
            - Publishes the 'pan', 'tilt', and 'name' values.
        """
        self.prev = 0
        self.hz = self.operation_parameters['sinus']['hz']
        self.sinus_step = self.operation_parameters['sinus']['step']
        while self.info['enabled']:
            if self.operation == "sinus":
                time.sleep(1.0 / self.hz)
                self.pan = self.pan_dc + self.pan_range / 2.0 * math.sin(self.prev)
                self.prev += self.sinus_step

            self.publisher.publish({
                'pan': self.pan,
                'tilt': self.tilt,
                'name': self.name
            })

    def get_callback(self, _):
        """
        Retrieves the current pan and tilt values.

        Args:
            _ (Any): Placeholder argument, not used in the function.

        Returns:
            dict: A dictionary containing the current 'pan' and 'tilt' values.
        """
        return {
            'pan': self.pan,
            'tilt': self.tilt
        }

    def set_callback(self, message):
        """
        Sets the pan and tilt values from the given message and publishes the updated values.

        Args:
            message (dict): A dictionary containing 'pan' and 'tilt' keys with their respective 
            values.

        Returns:
            dict: An empty dictionary.
        """
        self.pan = message['pan']
        self.tilt = message['tilt']
        self.publisher.publish({
            'pan': self.pan,
            'tilt': self.tilt,
            'name': self.name
        })
        print("Set: ", self.pan, self.tilt)
        return {}

    def start(self):
        """
        Starts the sensor and initializes the data thread if in mock mode.
        This method logs the sensor's status, waits for the simulator to start,
        and then logs that the sensor has started. If the sensor is in "mock" mode
        and is enabled, it starts a new thread to handle data processing.
        Attributes:
            self.logger (Logger): Logger instance for logging sensor status.
            self.name (str): Name of the sensor.
            self.simulator_started (bool): Flag indicating if the simulator has started.
            self.mode (str): Mode of the sensor, expected to be "mock" for this method to start 
                the data thread.
            self.info (dict): Dictionary containing sensor information, including the 'enabled' 
                status.
            self.data_thread (Thread): Thread instance for handling data processing.
        """
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)
        self.logger.info("Sensor %s started", self.name)

        if self.mode == "mock":
            if self.info['enabled']:
                self.data_thread = threading.Thread(target = self.thread_fun)
                self.data_thread.start()

    def stop(self):
        """
        Stops the pan-tilt controller by disabling it and stopping all associated RPC servers.

        This method performs the following actions:
        1. Sets the "enabled" flag in the info dictionary to False.
        2. Stops the enable RPC server.
        3. Stops the disable RPC server.
        4. Stops the get RPC server.
        5. Stops the set RPC server.
        """
        self.info["enabled"] = False
        self.get_rpc_server.stop()
        self.set_rpc_server.stop()
