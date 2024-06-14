#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random

from stream_simulator.base_classes import BaseThing

class IrController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        id = "d_ir_" + str(BaseThing.id + 1)
        name = id
        if 'name' in conf:
            name = conf['name']
        _category = "sensor"
        _class = "distance"
        _subclass = "ir"
        _pack = package["name"]

        super(self.__class__, self).__init__(id)
        
        info = {
            "type": "IR",
            "brand": "ir",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": name,
            "place": conf["place"],
            "id": "id_" + str(id),
            "enabled": True,
            "orientation": conf["orientation"],
            "hz": conf["hz"],
            "queue_size": 100,
            "mode": package["mode"],
            "speak_mode": package["speak_mode"],
            "namespace": package["namespace"],
            "sensor_configuration": conf["sensor_configuration"],
            "device_name": package["device_name"],
            "max_range": conf["max_range"],
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
        self.map = package["map"]
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

        self.publisher = self.commlib_factory.getPublisher(
            topic = self.base_topic + ".data"
        )
        self.enable_rpc_server = self.commlib_factory.getRPCService(
            callback = self.enable_callback,
            rpc_name = info["base_topic"] + ".enable"
        )
        self.disable_rpc_server = self.commlib_factory.getRPCService(
            callback = self.disable_callback,
            rpc_name = info["base_topic"] + ".disable"
        )

        if self.info["mode"] == "simulation":
            self.robot_pose_sub = self.commlib_factory.getSubscriber(
                topic = self.info['namespace'] + '.' + self.info['device_name'] + ".pose.internal",
                callback = self.robot_pose_update
            )

    def robot_pose_update(self, message):
        self.robot_pose = message

    def sensor_read(self):
        self.logger.info("Ir {} sensor read thread started".format(self.info["id"]))
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
                        tmpy = originy + d * math.sin(ths)
                    val = d * self.robot_pose["resolution"]
                except:
                    self.logger.warning("Pose not got yet..")

            # Publishing value:
            self.publisher.publish({
                "distance": val,
                "timestamp": time.time()
            })

        self.logger.info("Ir {} sensor read thread stopped".format(self.info["id"]))

    def enable_callback(self, message):
        self.info["enabled"] = True
        self.info["hz"] = message["hz"]
        self.info["queue_size"] = message["queue_size"]

        self.sensor_read_thread = threading.Thread(target = self.sensor_read)
        self.sensor_read_thread.start()
        return {"enabled": True}

    def disable_callback(self, message):
        self.info["enabled"] = False
        self.logger.info("Ir {} stops reading".format(self.info["id"]))
        return {"enabled": False}

    def start(self):
        if self.info["enabled"]:
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info("Ir {} reads with {} Hz".format(self.info["id"], self.info["hz"]))

    def stop(self):
        self.info["enabled"] = False
        self.commlib_factory.stop()
