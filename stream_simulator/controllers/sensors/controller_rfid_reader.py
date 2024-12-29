"""
File that contains the RFID reader controller.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging
import threading
import random

from stream_simulator.base_classes import BaseThing

class RfidReaderController(BaseThing):
    """
    Controller class for an RFID reader sensor.
    Attributes:
        logger (logging.Logger): Logger instance for logging messages.
        info (dict): Dictionary containing sensor information and configuration.
        name (str): Name of the RFID reader.
        base_topic (str): Base topic for communication.
        derp_data_key (str): Key for raw data communication.
        range (int): Range of the RFID reader.
        fov (int): Field of view of the RFID reader.
        publisher (Publisher): Publisher instance for publishing sensor data.
        enable_rpc_server (RPCService): RPC service for enabling the sensor.
        disable_rpc_server (RPCService): RPC service for disabling the sensor.
    Methods:
        __init__(conf=None, package=None): Initializes the RFID reader controller with the 
            given configuration and package.
        sensor_read(): Reads sensor data and publishes it at the specified frequency.
        enable_callback(message): Callback function to enable the sensor.
        disable_callback(message): Callback function to disable the sensor.
        start(): Starts the sensor and its reading thread.
        stop(): Stops the sensor and its communication.
    """
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        id_ = "d_rfid_reader_" + str(BaseThing.id + 1)
        name = id_
        if 'name' in conf:
            name = conf['name']
        _category = "sensor"
        _class = "rf"
        _subclass = "rfid_reader"
        _pack = package["name"]
        _namespace = package["namespace"]

        super().__init__(id_, auto_start=False)
        self.set_simulation_communication(_namespace)

        info = {
            "type": "RFID_READER",
            "brand": "unknown",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": name,
            "place": conf["place"],
            "id": id_,
            "enabled": True,
            "orientation": float(conf["orientation"]),
            "hz": conf["hz"],
            "mode": package["mode"],
            "namespace": package["namespace"],
            "device_name": package["device_name"],
            "categorization": {
                "host_type": "robot",
                "place": _pack.split(".")[-1],
                "category": _category,
                "class": _class,
                "subclass": [_subclass],
                "name": name
            }
        }

        self.info = info
        self.name = info["name"]
        self.base_topic = info["base_topic"]
        self.derp_data_key = info["base_topic"] + ".raw"
        self.range = 150 if 'range' not in conf else conf['range']
        self.fov = 180 if 'fov' not in conf else conf['fov']

        self.set_tf_communication(package)

        # tf handling
        tf_package = {
            "type": "robot",
            "subtype": {
                "category": _category,
                "class": _class,
                "subclass": [_subclass]
            },
            "pose": conf["pose"],
            "base_topic": info['base_topic'],
            "name": self.name,
            "range": self.range,
            "namespace": _namespace,
            "properties": {
                "fov": self.fov
            }
        }
        tf_package['host'] = package['device_name']
        tf_package['host_type'] = 'robot'
        if 'host' in conf:
            tf_package['host'] = conf['host']
            tf_package['host_type'] = 'pan_tilt'

        self.publisher = self.commlib_factory.getPublisher(
            topic = self.base_topic + ".data"
        )

        self.commlib_factory.run()

        self.tf_declare_rpc.call(tf_package)

        self.sensor_read_thread = None

    def sensor_read(self):
        """
        Reads data from the RFID sensor and publishes it at a specified frequency.
        This method runs in a loop, reading data from the RFID sensor based on the mode specified 
            in the sensor's info.
        It supports two modes:
        - "mock": Generates random RFID tags.
        - "simulation": Retrieves RFID tags from a remote service.
        The read data is published to a specified publisher and, if any tags are detected, a 
            notification is sent to the UI.
        The loop runs until the sensor is disabled.
        Logs are generated when the sensor read thread starts and stops.
        Args:
            None
        Returns:
            None
        """
        self.logger.info("RFID reader %s sensor read thread started", self.info["id"])
        while self.info["enabled"]:
            time.sleep(1.0 / self.info["hz"])

            val = {'tags': {}}
            tags = {}
            if self.info["mode"] == "mock":
                if random.uniform(0, 10) < 3:
                    tags["RF432423"] = "lorem_ipsum"
            elif self.info["mode"] == "simulation":
                # Ask tf for proximity sound sources or humans
                res = self.tf_affection_rpc.call({
                    'name': self.name
                })
                for t in res:
                    tags[res[t]['info']['id']] = res[t]['info']['message']

            # Publishing value:
            val['tags'] = tags
            self.publisher.publish({
                "data": val,
                "timestamp": time.time()
            })

            # print(Fore.CYAN + f"RFID {self.info['id']} read: {val}" + Style.RESET_ALL)

            if len(tags) > 0:
                self.commlib_factory.notify_ui(
                    type_ = "rfid_tags",
                    data = {
                        "name": self.name,
                        "value": {
                            "tags": tags
                        }
                    }
                )

        self.logger.info("RFID reader %s sensor read thread stopped", self.info["id"])

    def start(self):
        """
        Starts the RFID sensor.
        This method logs the initial state of the sensor and waits for the simulator to start.
        Once the simulator has started, it logs that the sensor has started.
        If the sensor is enabled, it starts a new thread to read from the sensor.
        Attributes:
            self.logger (Logger): Logger instance to log sensor states.
            self.name (str): Name of the sensor.
            self.simulator_started (bool): Flag indicating if the simulator has started.
            self.info (dict): Dictionary containing sensor configuration, including the 'enabled' 
                key.
            self.sensor_read_thread (Thread): Thread instance for reading sensor data.
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
        Stops the RFID reader by disabling it and stopping the communication library.

        This method sets the "enabled" flag in the info dictionary to False, indicating
        that the RFID reader is no longer active. It also calls the stop method on the
        commlib_factory to halt any ongoing communication processes.
        """
        self.info["enabled"] = False
        self.commlib_factory.stop()
