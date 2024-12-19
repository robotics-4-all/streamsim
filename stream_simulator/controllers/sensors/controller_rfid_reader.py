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

class RfidReaderController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        id = "d_rfid_reader_" + str(BaseThing.id + 1)
        name = id
        if 'name' in conf:
            name = conf['name']
        _category = "sensor"
        _class = "rf"
        _subclass = "rfid_reader"
        _pack = package["name"]
        _namespace = package["namespace"]

        super().__init__(id)
        self.set_simulation_communication(_namespace)

        info = {
            "type": "RFID_READER",
            "brand": "unknown",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": name,
            "place": conf["place"],
            "id": id,
            "enabled": True,
            "orientation": float(conf["orientation"]),
            "hz": conf["hz"],
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
        
        self.tf_declare_rpc.call(tf_package)

        self.publisher = self.commlib_factory.getPublisher(
            topic = self.base_topic + ".data"
        )
        self.enable_rpc_server = self.commlib_factory.getRPCService(
            callback = self.enable_callback,
            rpc_name = self.base_topic + ".enable"
        )
        self.disable_rpc_server = self.commlib_factory.getRPCService(
            callback = self.disable_callback,
            rpc_name = self.base_topic + ".disable"
        )

    def sensor_read(self):
        self.logger.info("RFID reader {} sensor read thread started".format(self.info["id"]))
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

        self.logger.info("RFID reader {} sensor read thread stopped".format(self.info["id"]))

    def enable_callback(self, message):
        self.info["enabled"] = True
        self.info["hz"] = message["hz"]

        self.sensor_read_thread = threading.Thread(target = self.sensor_read)
        self.sensor_read_thread.start()
        return {"enabled": True}

    def disable_callback(self, message):
        self.info["enabled"] = False
        self.logger.info("Sensor {} stops reading".format(self.info["id"]))
        return {"enabled": False}

    def start(self):
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)
        self.logger.info("Sensor %s started", self.name)

        if self.info["enabled"]:
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()

    def stop(self):
        self.info["enabled"] = False
        self.commlib_factory.stop()
