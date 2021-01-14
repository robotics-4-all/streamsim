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

class EncoderController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = Logger(conf["name"])
        else:
            self.logger = package["logger"]

        super(self.__class__, self).__init__()
        id = "d_" + str(BaseThing.id)
        name = id
        if 'name' in conf:
            name = conf['name']
        _category = "sensor"
        _class = "encoder"
        _subclass = "absolute"
        _pack = package["name"]

        info = {
            "type": "ENCODER",
            "brand": "simple",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}.{id}",
            "name": name,
            "place": conf["place"],
            "id": id,
            "enabled": True,
            "orientation": conf["orientation"],
            "hz": conf["hz"],
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
                "data": ["rpm"]
            }
        }

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]
        self.base_topic = info["base_topic"]
        self.derp_data_key = info["base_topic"] + ".raw"

        # tf handling
        tf_package = {
            "type": "robot",
            "subtype": "encoder",
            "pose": conf["pose"],
            "base_topic": info['base_topic'],
            "name": self.name
        }
        tf_package['host'] = package['device_name']
        tf_package['host_type'] = 'robot'
        package["tf_declare"].call(tf_package)

        self.publisher = CommlibFactory.getPublisher(
            broker = "redis",
            topic = self.base_topic + ".data"
        )

        if self.info["mode"] == "real":
            from pidevices import DfRobotWheelEncoderPiGPIO

            self.sensor = DfRobotWheelEncoderPiGPIO(gpio=self.conf["pin"],
                                                      pulses_per_rev = 10,
                                                      name=self.name,
                                                      max_data_length=self.conf["max_data_length"])

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

    def sensor_read(self):
        self.logger.info("Encoder {} sensor read thread started".format(self.info["id"]))
        period = 1.0 / self.info["hz"]

        while self.info["enabled"]:
            if self.info["mode"] == "mock":
                self.data = float(random.uniform(1000,2000))
            elif self.info["mode"] == "simulation":
                self.data = float(random.uniform(1000,2000))
            else: # The real deal
                self.data = self.sensor.read_rpm()

            time.sleep(period)

            # Publishing value:
            self.publisher.publish({
                "rpm": self.data,
                "timestamp": time.time()
            })

            # Storing value:
            r = CommlibFactory.derp_client.lset(
                self.derp_data_key,
                [{
                    "rpm": self.data,
                    "timestamp": time.time()
                }]
            )

        self.logger.info("Encoder {} sensor read thread stopped".format(self.info["id"]))

    def enable_callback(self, message, meta):
        self.info["enabled"] = True
        self.info["hz"] = message["hz"]
        self.info["queue_size"] = message["queue_size"]

        self.sensor_read_thread = threading.Thread(target = self.sensor_read)
        self.sensor_read_thread.start()
        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        self.logger.info("Encoder {} stops reading".format(self.info["id"]))
        return {"enabled": False}

    def start(self):
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        if self.info["enabled"]:
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info("Encoder {} reads with {} Hz".format(self.info["id"], self.info["hz"]))

            if self.info["mode"] == "real":
                self.sensor.start()

    def stop(self):
        self.info["enabled"] = False

        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()

        if self.info["mode"] == "real":
            self.sensor.stop()
