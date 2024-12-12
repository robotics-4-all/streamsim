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

class PanTiltController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        id = "d_pan_tilt_" + str(BaseThing.id + 1)
        name = id
        if 'name' in conf:
            name = conf['name']
        _category = "actuator"
        _class = "motion"
        _subclass = "pan_tilt"
        _pack = package["name"]
        super().__init__(id)

        info = {
            "type": "PAN_TILT",
            "brand": "pca9685",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": name,
            "place": conf["place"],
            "id": id,
            "enabled": True,
            "orientation": conf["orientation"],
            "mode": package["mode"],
            "speak_mode": package["speak_mode"],
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
        self.conf = info["sensor_configuration"]
        self.base_topic = info["base_topic"]
        self.derp_data_key = info["base_topic"] + ".raw"

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
            "name": self.name
        }
        tf_package['host'] = package['device_name']
        tf_package['host_type'] = 'robot'
        if 'host' in conf:
            tf_package['host'] = conf['host']
            tf_package['host_type'] = 'pan_tilt'
        
        self.tf_declare_rpc.call(tf_package)

        # init values
        self._yaw = 0.0
        self._pitch = 0.0

        self.pan_tilt_set_sub = self.commlib_factory.getSubscriber(
            topic = self.base_topic + ".set",
            callback = self.pan_tilt_set_callback
        )
        self.pan_tilt_get_rpc_server = self.commlib_factory.getRPCService(
            callback = self.get_pan_tilt_callback,
            rpc_name = self.base_topic + ".get"
        )
        self.enable_rpc_server = self.commlib_factory.getRPCService(
            callback = self.enable_callback,
            rpc_name = self.base_topic + ".enable"
        )
        self.disable_rpc_server = self.commlib_factory.getRPCService(
            callback = self.disable_callback,
            rpc_name = self.base_topic + ".disable"
        )
        self.data_publisher = self.commlib_factory.getPublisher(
            topic = self.base_topic + ".data"
        )

    def enable_callback(self, message):
        self.info["enabled"] = True
        return {"enabled": True}

    def disable_callback(self, message):
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        pass

    def stop(self):
        self.commlib_factory.stop()

    def get_pan_tilt_callback(self, message):
        return {
            "pan": self._yaw,
            "tilt": self._pitch
        }


    def pan_tilt_set_callback(self, message):
        try:
            response = message
            self._yaw = response['pan']
            self._pitch = response['tilt']

            if self.info["mode"] == "mock":
                pass
            elif self.info["mode"] == "simulation":
                pass
          
            self.data_publisher.publish({
                'pan': self._yaw,
                'tilt': self._pitch,
                'name': self.name
            })

            self.logger.info("{}: New pan tilt command: {}, {}".format(self.name, self._yaw, self._pitch))
        except Exception as e:
            self.logger.error("{}: pan_tilt is wrongly formatted: {} - {}".format(self.name, str(e.__class__), str(e)))
