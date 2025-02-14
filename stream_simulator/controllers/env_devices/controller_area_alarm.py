"""
File that contains the environment area alarm controller.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging
import threading
import random

from stream_simulator.base_classes import BaseThing

class EnvAreaAlarmController(BaseThing):
    """
    EnvAreaAlarmController is a class that represents an environmental area alarm controller.
    Attributes:
        logger (logging.Logger): Logger instance for logging messages.
        info (dict): Information about the alarm controller.
        name (str): Name of the alarm controller.
        base_topic (str): Base topic for communication.
        hz (int): Frequency of sensor readings.
        mode (str): Mode of operation (e.g., "mock" or "simulation").
        place (str): Place where the alarm controller is located.
        pose (dict): Pose information of the alarm controller.
        range (float): Range of the alarm controller.
        derp_data_key (str): Key for raw data.
        host (str): Host information if available.
        sensor_read_thread (threading.Thread): Thread for reading sensor data.
    Methods:
        __init__(conf=None, package=None):
            Initializes the EnvAreaAlarmController instance.
        set_communication_layer(package):
            Sets up the communication layer for the alarm controller.
        sensor_read():
            Reads sensor data and publishes it at a specified frequency.
        enable_callback(_):
            Callback to enable the alarm controller.
        disable_callback(message):
            Callback to disable the alarm controller.
        start():
            Starts the alarm controller.
        stop():
            Stops the alarm controller.
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

        # self.sensor_read_thread = None

        _type = "AREA_ALARM"
        _category = "sensor"
        _class = "alarm"
        _subclass = "area_alarm"

        info = self.generate_info(conf, package, _type, _category, _class, _subclass)
        self.info = info
        self.name = info["name"]
        self.base_topic = info["base_topic"]
        self.hz = info['conf']['hz']
        self.mode = info["mode"]
        self.place = info["conf"]["place"]
        self.pose = info["conf"]["pose"]
        self.range = info["conf"]["range"]
        self.derp_data_key = info["base_topic"] + ".raw"

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

        self.sensor_read_thread = None
        self.stopped = False

    def set_communication_layer(self, package):
        """
        Configures the communication layer for the controller area alarm.

        This method sets up various communication channels and publishers required
        for the controller area alarm to function properly. It initializes the 
        simulation communication, tf communication, data publisher, enable/disable 
        RPCs, and triggers publisher.

        Args:
            package (dict): A dictionary containing configuration details. It must 
                            include a "namespace" key for setting up the simulation 
                            communication.
        """
        self.set_tf_distance_calculator_rpc(package)
        self.set_simulation_communication(package["namespace"])
        self.set_tf_communication(package)
        self.set_data_publisher(self.base_topic)
        self.set_triggers_publisher(self.base_topic)
        self.set_sensor_state_interfaces(self.base_topic)
        self.logger.info("Communication done")

    def sensor_read(self):
        """
        Reads sensor data and publishes the values at a specified frequency.
        This method runs in a loop while the sensor is enabled. Depending on the mode,
        it either generates mock data or retrieves data from a simulation. The sensor
        values are published along with a timestamp. If a new value is detected, it 
        increments the trigger count and publishes the trigger count. Additionally, 
        it notifies the UI about the alarm triggers.
        Attributes:
            self.logger (Logger): Logger instance for logging information.
            self.name (str): Name of the sensor.
            self.info (dict): Dictionary containing sensor information, including 
                the enabled status.
            self.hz (float): Frequency at which the sensor reads data.
            self.mode (str): Mode of operation, either "mock" or "simulation".
            self.tf_affection_rpc (RPC): RPC instance for retrieving simulation data.
            self.publisher (Publisher): Publisher instance for publishing sensor values.
            self.publisher_triggers (Publisher): Publisher instance for publishing 
                trigger counts.
            self.commlib_factory (CommLibFactory): Factory instance for notifying the UI.
        Raises:
            None
        """
        self.logger.info("Sensor %s read thread started", self.name)
        prev = []
        triggers = 0

        while self.info["enabled"]:
            time.sleep(1.0 / self.hz)

            if self.state is None or self.state == "off":
                continue

            val = None
            if self.mode == "mock":
                val = random.choice([None, "gn_robot_1"])
            elif self.mode == "simulation":
                res = self.tf_affection_rpc.call({
                    'name': self.name
                })
                affections = res['affections']
                val = [x for x in affections]

            # Publishing value:
            self.publisher.publish({
                "value": val,
                "timestamp": time.time()
            })
            if not prev and val not in [None, []]:
                triggers += 1
                self.publisher_triggers.publish({
                    "value": triggers,
                    "timestamp": time.time(),
                    "trigger": val,
                    "name": self.name,
                })

            prev = val

        self.stopped = True

    def start(self):
        """
        Starts the sensor and its associated processes.
        This method logs the initial state of the sensor and waits for the simulator to start.
        Once the simulator is started, it logs the sensor's start state and, if the 
        sensor is enabled,
        it starts a new thread to read sensor data.
        Attributes:
            simulator_started (bool): Flag indicating whether the simulator has started.
            info (dict): Dictionary containing sensor information, including whether 
            it is enabled.
            sensor_read_thread (threading.Thread): Thread for reading sensor data.
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
        Stops the controller area alarm by disabling the RPC servers and updating the status.

        This method sets the "enabled" status to False and stops both the enable 
        and disable RPC servers.
        """
        self.info["enabled"] = False
        while not self.stopped:
            time.sleep(0.1)
        self.logger.warning("Sensor %s stopped", self.name)
