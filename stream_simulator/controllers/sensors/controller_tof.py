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

class TofController(BaseThing):
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
        _class = "distance"
        _subclass = "tof"
        _pack = package["name"]

        info = {
            "type": "TOF",
            "brand": "vl53l1x",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}.{id}",
            "name": "tof_" + str(id),
            "place": conf["place"],
            "id": id,
            "enabled": True,
            "orientation": conf["orientation"],
            "hz": conf["hz"],
            "queue_size": 100,
            "mode": package["mode"],
            "speak_mode": package["speak_mode"],
            "namespace": package["namespace"],
            "sensor_configuration": conf["sensor_configuration"],
            "max_range": conf["max_range"],
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
        self.map = package["map"]
        self.base_topic = info["base_topic"]
        self.derp_data_key = info["base_topic"] + ".raw"

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
        package["tf_declare"].call(tf_package)

        self.publisher = CommlibFactory.getPublisher(
            broker = "redis",
            topic = self.base_topic + ".data"
        )
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

        if self.info["mode"] == "real":
            from pidevices.sensors.vl53l1x import VL53L1X
            self.sensor = VL53L1X(bus=1)
        if self.info["mode"] == "simulation":
            self.robot_pose_sub = CommlibFactory.getSubscriber(
                broker = "redis",
                topic = self.info['namespace'] + '.' + self.info['device_name'] + ".pose",
                callback = self.robot_pose_update
            )

    def robot_pose_update(self, message, meta):
        self.robot_pose = message

    def sensor_read(self):
        self.logger.info("TOF {} sensor read thread started".format(self.info["id"]))
        while self.info["enabled"]:
            time.sleep(1.0 / self.info["hz"])

            val = 0
            if self.info["mode"] == "mock":
                val = float(random.uniform(30, 10))
            elif self.info["mode"] == "simulation":
                try:
                    ths = self.robot_pose["theta"] + self.info["orientation"] / 180.0 * math.pi
                    # Calculate distance
                    d = 1
                    originx = self.robot_pose["x"] / self.robot_pose["resolution"]
                    originy = self.robot_pose["y"] / self.robot_pose["resolution"]
                    tmpx = originx
                    tmpy = originy
                    limit = self.info["max_range"] / self.robot_pose["resolution"]
                    while self.map[int(tmpx), int(tmpy)] == 0 and d < limit:
                        d += 1
                        tmpx = originx + d * math.cos(ths)
                        tmpy = originx + d * math.cos(ths)
                    val = d * self.robot_pose["resolution"]
                except:
                    self.logger.warning("Pose not got yet..")
            else: # The real deal
                val = self.sensor.read()

            # Publishing value:
            self.publisher.publish({
                "distance": val,
                "timestamp": time.time()
            })

            # Storing value:
            r = CommlibFactory.derp_client.lset(
                self.derp_data_key,
                [{
                    "distance": val,
                    "timestamp": time.time()
                }]
            )

        self.logger.info("TOF {} sensor read thread stopped".format(self.info["id"]))

    def enable_callback(self, message, meta):
        self.info["enabled"] = True
        self.info["hz"] = message["hz"]
        self.info["queue_size"] = message["queue_size"]

        self.memory = self.info["queue_size"] * [0]
        self.sensor_read_thread = threading.Thread(target = self.sensor_read)
        self.sensor_read_thread.start()
        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        self.logger.info("TOF {} stops reading".format(self.info["id"]))
        return {"enabled": False}

    def start(self):
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        if self.info["mode"] == "simulation":
            self.robot_pose_sub.run()

        if self.info["enabled"]:
            self.memory = self.info["queue_size"] * [0]
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info("TOF {} reads with {} Hz".format(self.info["id"], self.info["hz"]))

    def stop(self):
        self.info["enabled"] = False
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()

        if self.info["mode"] == "simulation":
            self.robot_pose_sub.stop()
