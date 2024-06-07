#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random
import abc

from colorama import Fore, Style

from stream_simulator.base_classes import BaseThing
from stream_simulator.connectivity import CommlibFactory

class BasicSensor(BaseThing):
    def __init__(self,
                 conf = None,
                 package = None,
                 _type = None,
                 _category = None,
                 _class = None,
                 _subclass = None):

        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        super(BasicSensor, self).__init__(conf["name"])

        self.set_tf_communication(package)

        _name = conf["name"]
        _pack = package["base"]
        _place = conf["place"]
        id = "d_" + str(BaseThing.id)
        info = {
            "type": _type,
            "base_topic": f"{_pack}.{_place}.{_category}.{_class}.{_subclass}.{_name}",
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
        self.operation = info['conf']['operation']
        self.operation_parameters = info['conf']['operation_parameters']
        self.place = info["conf"]["place"]
        self.pose = info["conf"]["pose"]
        self.derp_data_key = info["base_topic"] + ".raw"

        # Communication
        self.set_data_publisher(self.base_topic)
        self.set_enable_disable_rpcs(self.base_topic, self.enable_callback, self.disable_callback)
        self.set_mode_get_set_rpcs(self.base_topic, self.set_mode_callback, self.get_mode_callback)

        if self.mode == 'mock':
            if self.operation not in self.operation_parameters:
                self.logger.error(f"Operation parameters missing from {self.name}: {self.operation}")
                raise Exception(f"Operation parameters missing from {self.name}: {self.operation}")

        if self.operation == "triangle":
            self.prev = self.operation_parameters["triangle"]['min']
            self.way = 1
        elif self.operation == "sinus":
            self.prev = 0
        else:
            self.prev = None

        # Do not execute the factory yet, wait for the sensor to be initialized

    def get_mode_callback(self, message):
        return {
                "mode": self.operation,
                "parameters": self.operation_parameters[self.operation]
        }

    def set_mode_callback(self, message):
        if message["mode"] == "triangle":
            self.prev = self.operation_parameters["triangle"]['min']
            self.way = 1
        elif message["mode"] == "sinus":
            self.prev = 0
        else:
            self.prev = None

        self.operation = message["mode"]
        return {}

    def sensor_read(self):
        self.logger.info(f"Sensor {self.name} read thread started")
        # Operation parameters

        try:
            self.constant_value = self.operation_parameters["constant"]['value']
            self.random_min = self.operation_parameters["random"]['min']
            self.random_max = self.operation_parameters["random"]['max']
            self.triangle_min = self.operation_parameters["triangle"]['min']
            self.triangle_max = self.operation_parameters["triangle"]['max']
            self.triangle_step = self.operation_parameters["triangle"]['step']
            self.normal_std = self.operation_parameters["normal"]['std']
            self.normal_mean = self.operation_parameters["normal"]['mean']
            self.sinus_dc = self.operation_parameters["sinus"]['dc']
            self.sinus_amp = self.operation_parameters["sinus"]['amplitude']
            self.sinus_step = self.operation_parameters["sinus"]['step']
        except Exception as e:
            self.logger.warning(f"Missing operation parameters for {self.name}: {str(e)}. Change operation with caution!")

        while self.info["enabled"]:
            time.sleep(1.0 / self.hz)

            val = None
            if self.mode in ["mock"]:
                if self.operation == "constant":
                    val = self.constant_value
                elif self.operation == "random":
                    val = random.uniform(
                        self.random_min,
                        self.random_max
                    )
                elif self.operation == "normal":
                    val = random.gauss(
                        self.normal_mean,
                        self.normal_std
                    )
                elif self.operation == "triangle":
                    val = self.prev + self.way * self.triangle_step
                    if val >= self.triangle_max or val <= self.triangle_min:
                        self.way *= -1
                    self.prev = val
                elif self.operation == "sinus":
                    val = self.sinus_dc + self.sinus_amp * math.sin(self.prev)
                    self.prev += self.sinus_step
                else:
                    self.logger.warning(f"Unsupported operation: {self.operation}")

            elif self.mode == "simulation":
                val = self.get_simulation_value()

            # Publishing value:
            # self.logger.info(f"{self.name} - {val}")
            self.publisher.publish({
                "value": val,
                "timestamp": time.time()
            })

    @abc.abstractmethod
    def get_simulation_value(self):
        return None

    def enable_callback(self, message):
        self.info["enabled"] = True

        self.enable_rpc_server.run()
        self.disable_rpc_server.run()
        self.get_mode_rpc_server.run()
        self.set_mode_rpc_server.run()

        self.sensor_read_thread = threading.Thread(target = self.sensor_read)
        self.sensor_read_thread.start()

        return {"enabled": True}

    def disable_callback(self, message):
        self.info["enabled"] = False
        return {"enabled": False}

    def get_callback(self, message):
        return {"state": self.state}

    def set_callback(self, message):
        state = message["state"]
        if state not in self.allowed_states:
            raise Exception(f"{self.name} does not allow {state} state")

        self.state = state
        return {"state": self.state}

    def start(self):
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()
        self.get_mode_rpc_server.run()
        self.set_mode_rpc_server.run()

        if self.info["enabled"]:
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()

    def stop(self):
        self.info["enabled"] = False
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()
        self.get_mode_rpc_server.stop()
        self.set_mode_rpc_server.stop()
