"""
File that contains the linear Alarm controller.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging
import threading
import random

from stream_simulator.base_classes import BaseThing

class EnvLinearAlarmController(BaseThing):
    """
    EnvLinearAlarmController is a class that represents a linear alarm sensor in an environment 
    simulation.
    Attributes:
        info (dict): Information about the sensor including type, base_topic, name, place, mode, 
            and configuration.
        name (str): The name of the sensor.
        base_topic (str): The base topic for communication.
        hz (int): The frequency at which the sensor reads data.
        mode (str): The mode of the sensor, either "mock" or "simulation".
        place (str): The place where the sensor is located.
        pose (dict): The pose of the sensor.
        derp_data_key (str): The key for raw data.
        host (str): The host of the sensor, if available.
    Methods:
        __init__(conf=None, package=None):
            Initializes the EnvLinearAlarmController with the given configuration and package.
        set_communication_layer(package):
            Sets up the communication layer for the sensor.
        sensor_read():
            Reads data from the sensor and publishes it at the specified frequency.
        enable_callback(message):
            Enables the sensor and starts the sensor read thread.
        disable_callback(message):
            Disables the sensor.
        start():
            Starts the sensor and its communication layers.
        stop():
            Stops the sensor and its communication layers.
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

        _type = "LINEAR_ALARM"
        _category = "sensor"
        _class = "alarm"
        _subclass = "linear_alarm"

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
        self.name = info["name"]
        self.base_topic = info["base_topic"]
        self.hz = info['conf']['hz']
        self.mode = info["mode"]
        self.place = info["conf"]["place"]
        self.pose = info["conf"]["pose"]
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

        self.sensor_read_thread = None

    def set_communication_layer(self, package):
        """
        Configures the communication layer for the controller.

        This method sets up various communication channels required for the controller
        to function properly. It initializes simulation communication, transforms communication,
        data publishing, trigger publishing, and enables/disables RPCs.

        Args:
            package (dict): A dictionary containing configuration parameters. Expected keys:
                - "namespace": The namespace for simulation communication.
        """
        self.set_simulation_communication(package["namespace"])
        self.set_tf_communication(package)
        self.set_data_publisher(self.base_topic)
        self.set_triggers_publisher(self.base_topic)
        self.set_enable_disable_rpcs(self.base_topic, self.enable_callback, self.disable_callback)

    def sensor_read(self):
        """
        Reads sensor data in a separate thread and publishes the values.
        This method continuously reads data from the sensor at a specified frequency (`self.hz`).
        Depending on the mode (`self.mode`), it either generates mock data or retrieves data from 
        a simulation.
        The read values are then published along with a timestamp.
        If the sensor value changes from the previous read and is not None or empty, it increments 
        a trigger count, publishes the trigger count, and notifies the UI with an alarm.
        The method runs in a loop until `self.info["enabled"]` is set to False.
        Attributes:
            self (object): The instance of the class containing this method.
        Raises:
            None
        Returns:
            None
        """
        self.logger.info("Sensor %s read thread started", self.name)
        prev = 0
        triggers = 0
        while self.info["enabled"]:
            time.sleep(1.0 / self.hz)

            val = None
            if self.mode == "mock":
                val = random.choice([None, "gn_robot_1"])
            elif self.mode == "simulation":
                res = self.tf_affection_rpc.call({
                    'name': self.name
                })
                val = [x for x in res]

            # Publishing value:
            self.publisher.publish({
                "value": val,
                "timestamp": time.time()
            })
            # print(f"Sensor {self.name} value: {val}")

            if prev is not None and val not in [None, []]:
                triggers += 1
                self.publisher_triggers.publish({
                    "value": triggers,
                    "timestamp": time.time()
                })

                self.commlib_factory.notify_ui(
                    type_ = "alarm",
                    data = {
                        "name": self.name,
                        "triggers": triggers
                    }
                )

            prev = val

    def enable_callback(self, _):
        """
        Enables the callback by setting the 'enabled' flag to True and starting the sensor 
        read thread.
        Args:
            _ (Any): Placeholder argument, not used in the method.
        Returns:
            dict: A dictionary indicating that the callback has been enabled with the key 
            'enabled' set to True.
        """
        self.info["enabled"] = True

        # self.enable_rpc_server.run()
        # self.disable_rpc_server.run()

        self.sensor_read_thread = threading.Thread(target = self.sensor_read)
        self.sensor_read_thread.start()

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

    def start(self):
        """
        Starts the sensor and waits for the simulator to start.
        This method logs the initial state of the sensor and waits until the simulator
        has started. Once the simulator is started, it logs the sensor's start state.
        If the sensor is enabled, it starts a new thread to read sensor data.
        Attributes:
            simulator_started (bool): Flag indicating whether the simulator has started.
            info (dict): Dictionary containing sensor information, including the "enabled" status.
            sensor_read_thread (threading.Thread): Thread for reading sensor data.
        """
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)
        self.logger.info("Sensor %s started", self.name)

        # self.enable_rpc_server.run()
        # self.disable_rpc_server.run()

        if self.info["enabled"]:
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()

    def stop(self):
        """
        Stops the linear alarm controller by disabling the alarm and stopping the RPC servers.

        This method sets the "enabled" flag in the info dictionary to False, indicating that the
        linear alarm controller is no longer active. It also stops the enable and disable RPC 
        servers to prevent further remote procedure calls.

        Raises:
            Any exceptions raised by the stop methods of the RPC servers.
        """
        self.info["enabled"] = False
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()
