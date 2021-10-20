#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random

from colorama import Fore, Style

from commlib.logger import Logger
from stream_simulator.base_classes import BaseThing
from stream_simulator.connectivity import CommlibFactory

class EnvPanTiltController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = Logger(conf["name"])
        else:
            self.logger = package["logger"]

        super(self.__class__, self).__init__()

        _type = "PAN_TILT"
        _category = "actuator"
        _class = "motion"
        _subclass = "pan_tilt"

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

        package["tf_declare"].call(tf_package)

        self.operation = info['conf']['operation']
        self.operation_parameters = info['conf']['operation_parameters']

        self.enable_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.enable_callback,
            rpc_name = info["base_topic"] + ".enable"
        )
        self.disable_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.disable_callback,
            rpc_name = info["base_topic"] + ".disable"
        )
        self.set_subscriber = CommlibFactory.getSubscriber(
            broker = "redis",
            callback = self.set_callback,
            topic = info["base_topic"] + ".set"
        )
        self.data_publisher = CommlibFactory.getPublisher(
            topic = info["base_topic"] + ".data"
        )
        self.get_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.get_callback,
            rpc_name = info["base_topic"] + ".get"
        )
        self.set_operation_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.set_mode_callback,
            rpc_name = info["base_topic"] + ".set_mode"
        )

    def set_mode_callback(self, message, meta):
        self.operation = message["mode"]
        return {}

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

            self.data_publisher.publish({
                'pan': self.pan,
                'tilt': self.tilt,
                'name': self.name
            })

    def enable_callback(self, message, meta):
        self.info["enabled"] = True

        self.enable_rpc_server.run()
        self.disable_rpc_server.run()
        self.get_rpc_server.run()
        self.set_subscriber.run()

        if self.mode == "mock":
            self.data_thread = threading.Thread(target = self.thread_fun)
            self.data_thread.start()

        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        return {"enabled": False}

    def get_callback(self, message, meta):
        return {
            'pan': self.pan,
            'tilt': self.tilt
        }

    def set_callback(self, message, meta):
        self.pan = message['pan']
        self.tilt = message['tilt']
        self.data_publisher.publish({
            'pan': self.pan,
            'tilt': self.tilt,
            'name': self.name
        })
        return {}

    def start(self):
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()
        self.get_rpc_server.run()
        self.set_subscriber.run()

        if self.mode == "mock":
            if self.info['enabled']:
                self.data_thread = threading.Thread(target = self.thread_fun)
                self.data_thread.start()

    def stop(self):
        self.info["enabled"] = False
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()
        self.get_rpc_server.stop()
        self.set_subscriber.stop()
