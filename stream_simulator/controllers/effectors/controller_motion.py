#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random

from colorama import Fore, Style

from stream_simulator.base_classes import BaseThing

class MotionController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        self.resolution = 0
        id = "d_skid_steering_" + str(BaseThing.id + 1)
        name = id
        if 'name' in conf:
            name = conf['name']
        _category = "actuator"
        _class = "motion"
        _subclass = "twist"
        _pack = package["name"]
        _namespace = package["namespace"]

        super().__init__(id)

        info = {
            "type": "SKID_STEER",
            "brand": "twist",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": name,
            "place": conf["place"],
            "id": id,
            "enabled": True,
            "orientation": float(conf["orientation"]),
            "queue_size": 0,
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

        self.set_tf_communication(package)
        self.set_simulation_communication(_namespace)

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
            "namespace": _namespace
        }
        tf_package['host'] = package['device_name']
        tf_package['host_type'] = 'robot'
        
        self.tf_declare_rpc.call(tf_package)

        self._linear = 0
        self._angular = 0

        self.vel_sub = self.commlib_factory.getSubscriber(
            topic = self.base_topic + ".set",
            callback = self.cmd_vel
        )
        self.motion_duration_sub = self.commlib_factory.getRPCService(
            rpc_name = self.base_topic + ".move.duration",
            callback = self.move_duration_callback
        )
        self.motion_distance_sub = self.commlib_factory.getRPCService(
            rpc_name = self.base_topic + ".move.distance",
            callback = self.move_distance_callback
        )
        self.turn_sub = self.commlib_factory.getRPCService(
            rpc_name = self.base_topic + ".move.turn",
            callback = self.turn_callback
        )
        self.enable_rpc_server = self.commlib_factory.getRPCService(
            callback = self.enable_callback,
            rpc_name = self.base_topic + ".enable"
        )
        self.disable_rpc_server = self.commlib_factory.getRPCService(
            callback = self.disable_callback,
            rpc_name = self.base_topic + ".disable"
        )

    def enable_callback(self, message):
        self.info["enabled"] = True
        return {"enabled": True}

    def disable_callback(self, message):
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)
        self.logger.info("Sensor %s started", self.name)

    def stop(self):
        self.commlib_factory.stop()

    def move_duration_callback(self, message):
        """
        Callback function to handle movement duration messages.
        Args:
            message (dict): A dictionary containing movement parameters:
                - 'linear' (float or str): Linear movement value.
                - 'angular' (float or str): Angular movement value.
                - 'duration' (float or str): Duration for the movement.
        Raises:
            ValueError: If 'linear', 'angular', or 'duration' are not valid float values.
        Logs:
            Error: If the message is wrongly formatted.
        """
        try:
            response = message

            # Checks for types
            try:
                float(response['linear'])
                float(response['angular'])
                float(response['duration'])
            except Exception as exe: # pylint: disable=broad-exception-caught
                if not response['linear'].isdigit():
                    raise ValueError("Linear is no integer nor float") from exe
                if not response['angular'].isdigit():
                    raise ValueError("Angular is no integer nor float") from exe
                if not response['duration'].isdigit():
                    raise ValueError("Angular is no integer nor float") from exe

            self._linear = response['linear']
            self._angular = response['angular']
            motion_started = time.time()
            while True:
                if time.time() - motion_started >= response["duration"]:
                    self._linear = 0
                    self._angular = 0
                    break
                time.sleep(0.05)
        except Exception as e: # pylint: disable=broad-exception-caught
            self.logger.error("%s: move_duration is wrongly formatted: %s - %s", self.name, str(e.__class__), str(e))
            return {"status": "failed"}

        return {"status": "done"}

    def move_distance_callback(self, message):
        try:
            response = message

            # Checks for types
            try:
                float(response['linear'])
                float(response['distance'])
            except Exception as exe: # pylint: disable=broad-exception-caught
                if not response['linear'].isdigit():
                    raise ValueError("Linear is no integer nor float") from exe
                if not response['distance'].isdigit():
                    raise ValueError("Distance is no integer nor float") from exe

            self._linear = response['linear']
            self._angular = 0
            print("time to sleep is: ", response["distance"] / response["linear"])
            time.sleep(response["distance"] / response["linear"])
            self._linear = 0
        except Exception as e: # pylint: disable=broad-exception-caught
            self.logger.error("%s: move_duration is wrongly formatted: %s - %s", self.name, str(e.__class__), str(e))
            return {"status": "failed"}

        return {"status": "done"}

    def turn_callback(self, message):
        try:
            response = message

            # Checks for types
            try:
                float(response['angular'])
                float(response['angle'])
            except Exception as exe: # pylint: disable=broad-exception-caught
                if not response['angular'].isdigit():
                    raise ValueError("Angular is no integer nor float") from exe
                if not response['angle'].isdigit():
                    raise ValueError("Angle is no integer nor float") from exe

            self._linear = 0
            self._angular = response['angular']
            print("time to sleep is: ", response["angle"] / response["angular"])
            time.sleep(response["angle"] / response["angular"])
            self._angular = 0
        except Exception as e: # pylint: disable=broad-exception-caught
            self.logger.error("%s: turn is wrongly formatted: %s - %s", self.name, str(e.__class__), str(e))
            return {"status": "failed"}

        return {"status": "done"}

    def cmd_vel(self, message):
        try:
            response = message

            # Checks for types
            try:
                float(response['linear'])
                float(response['angular'])
            except: # pylint: disable=bare-except
                if not response['linear'].isdigit():
                    raise Exception("Linear is no integer nor float")
                if not response['angular'].isdigit():
                    raise Exception("Angular is no integer nor float")

            self._linear = response['linear']
            self._angular = response['angular']
            self._raw = response['raw']
        except Exception as e:
            self.logger.error("{}: cmd_vel is wrongly formatted: {} - {}".format(self.name, str(e.__class__), str(e)))
