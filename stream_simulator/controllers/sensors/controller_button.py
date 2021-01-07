#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random

from commlib.logger import Logger
from stream_simulator.connectivity import CommlibFactory
from stream_simulator.base_classes import BaseThing

class ButtonController(BaseThing):
    def __init__(self, conf = None, package = None):
        super(self.__class__, self).__init__()

        id = "d_" + str(BaseThing.id)
        name = "button_" + str(id)
        if 'name' in conf:
            name = conf['name']
            id = name

        info = {
            "type": "BUTTON",
            "brand": "simple",
            "base_topic": package["name"] + ".sensor.button.tactile_switch." + str(id),
            "name": name,
            "place": conf["place"],
            "id": id,
            "enabled": True,
            "orientation": conf["orientation"],
            "hz": 1,
            "mode": package["mode"],
            "speak_mode": package["speak_mode"],
            "namespace": package["namespace"],
            "sensor_configuration": conf["sensor_configuration"],
            "device_name": package["device_name"],
            "endpoints":{
                "enable": "rpc",
                "disable": "rpc",
                "data": "publisher"
            },
            "data_models": {
                "data": ["data"]
            }
        }

        self.info = info
        self.name = info["name"]

        # tf handling
        tf_package = {
            "type": "robot",
            "subtype": "button",
            "pose": conf["pose"],
            "base_topic": info['base_topic'],
            "name": self.name
        }
        tf_package['host'] = package['device_name']
        tf_package['host_type'] = 'robot'
        if 'host' in conf:
            tf_package['host'] = conf['host']
            tf_package['host_type'] = 'pan_tilt'
        package["tf_declare"].call(tf_package)
