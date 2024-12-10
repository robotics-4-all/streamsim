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

class EnvPanTiltController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        super().__init__(conf["name"])

        _type = "PAN_TILT"
        _category = "actuator"
        _class = "motion"
        _subclass = "pan_tilt"

        _name = conf["name"]
        _pack = package["base"]
        _place = conf["place"]
        _namespace = package["namespace"]
        id = "d_" + str(BaseThing.id)
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
        self.mode = info['conf']['mode']

        self.place = info["conf"]["place"]
        self.pan = 0
        self.tilt = 0
        self.limits = info['conf']['limits']
        # Turn to rads
        self.limits['pan']['min'] *= math.pi / 180.0
        self.limits['pan']['max'] *= math.pi / 180.0
        self.limits['tilt']['min'] *= math.pi / 180.0
        self.limits['tilt']['max'] *= math.pi / 180.0
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

        self.tf_declare_rpc.call(tf_package)

        self.operation = info['conf']['operation']
        self.operation_parameters = info['conf']['operation_parameters']

    def set_communication_layer(self, package):
        self.set_tf_communication(package)
        self.set_enable_disable_rpcs(self.base_topic, self.enable_callback, self.disable_callback)
        self.set_effector_set_get_rpcs(self.base_topic, self.set_callback, self.get_callback)
        self.set_data_publisher(self.base_topic)
        self.set_mode_get_set_rpcs(self.base_topic, self.set_mode_callback, self.get_mode_callback)

    def set_mode_callback(self, message):
        self.operation = message["mode"]
        return {}
    
    def get_mode_callback(self, message):
        return {
            "mode": self.operation,
            "parameters": self.operation_parameters[self.operation]
        }

    # Only for mock mode
    def thread_fun(self):
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

    def enable_callback(self, message):
        self.info["enabled"] = True

        self.enable_rpc_server.run()
        self.disable_rpc_server.run()
        self.get_rpc_server.run()
        self.set_subscriber.run()

        if self.mode == "mock":
            self.data_thread = threading.Thread(target = self.thread_fun)
            self.data_thread.start()

        return {"enabled": True}

    def disable_callback(self, message):
        self.info["enabled"] = False
        return {"enabled": False}

    def get_callback(self, message):
        return {
            'pan': self.pan,
            'tilt': self.tilt
        }

    def set_callback(self, message):
        self.pan = message['pan']
        self.tilt = message['tilt']
        self.publisher.publish({
            'pan': self.pan,
            'tilt': self.tilt,
            'name': self.name
        })
        return {}

    def start(self):
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()
        self.get_rpc_server.run()
        self.set_rpc_server.run()

        if self.mode == "mock":
            if self.info['enabled']:
                self.data_thread = threading.Thread(target = self.thread_fun)
                self.data_thread.start()

    def stop(self):
        self.info["enabled"] = False
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()
        self.get_rpc_server.stop()
        self.set_rpc_server.stop()
