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

class EnvAreaAlarmController(BaseThing):
    def __init__(self,
                 conf = None,
                 package = None
                 ):

        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        super(self.__class__, self).__init__(conf["name"])

        _type = "AREA_ALARM"
        _category = "sensor"
        _class = "alarm"
        _subclass = "area_alarm"
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

        self.tf_declare_rpc.call(tf_package)

    def set_communication_layer(self, package):
        self.set_tf_communication(package)
        self.set_data_publisher(self.base_topic)
        self.set_enable_disable_rpcs(self.base_topic, self.enable_callback, self.disable_callback)
        self.set_triggers_publisher(self.base_topic)

    def sensor_read(self):
        self.logger.info(f"Sensor {self.name} read thread started")
        prev = None
        triggers = 0

        while self.info["enabled"]:
            time.sleep(1.0 / self.hz)

            val = None
            if self.mode == "mock":
                val = random.choice([None, "gn_robot_1"])
            elif self.mode == "simulation":
                res = self.commlib_factory.get_tf_affection.call({
                    'name': self.name
                })
                val = [x for x in res]

            # Publishing value:
            self.publisher.publish({
                "value": val,
                "timestamp": time.time()
            })
            # print(f"{Fore.GREEN}Sensor {self.name} value: {val}{Style.RESET_ALL}")

            if prev == None and val not in [None, []]:
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

    def enable_callback(self, message):
        self.info["enabled"] = True

        self.sensor_read_thread = threading.Thread(target = self.sensor_read)
        self.sensor_read_thread.start()

        return {"enabled": True}

    def disable_callback(self, message):
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        if self.info["enabled"]:
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()

    def stop(self):
        self.info["enabled"] = False
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()
