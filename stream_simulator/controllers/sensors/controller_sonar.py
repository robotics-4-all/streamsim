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

class SonarController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        id = "d_sonar_" + str(BaseThing.id + 1)
        name = id
        if 'name' in conf:
            name = conf['name']
        _category = "sensor"
        _class = "distance"
        _subclass = "sonar"
        _pack = package["name"]
        _namespace = package["namespace"]

        super().__init__(id, auto_start=False)
        self.set_simulation_communication(_namespace)

        info = {
            "type": "SONAR",
            "brand": "sonar",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": name,
            "place": conf["place"],
            "id": id,
            "enabled": True,
            "orientation": float(conf["orientation"]),
            "hz": conf["hz"],
            "queue_size": 100,
            "mode": package["mode"],
            "speak_mode": package["speak_mode"],
            "namespace": package["namespace"],
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
        self.name = info['name']
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
            "name": self.name,
            "namespace": _namespace,
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
            rpc_name = self.base_topic  + ".enable"
        )
        self.disable_rpc_server = self.commlib_factory.getRPCService(
            callback = self.disable_callback,
            rpc_name = self.base_topic  + ".disable"
        )

        # print(self.info)

        if self.info["mode"] == "simulation":
            self.robot_pose_sub = self.commlib_factory.getSubscriber(
                topic = self.info['namespace'] + '.' + self.info['device_name'] + ".pose.internal",
                callback = self.robot_pose_update
            )

            self.get_tf_rpc = self.commlib_factory.getRPCClient(
                rpc_name = self.info['namespace'] + ".tf.get_tf"
            )

        self.robot_pose = None

        # Start commlib factory due to robot subscriptions (msub)
        self.commlib_factory.run()

    def robot_pose_update(self, message):
        self.robot_pose = message
        # print(Fore.CYAN + f"Sonar {self.info['id']} got robot pose: {self.robot_pose}" + Style.RESET_ALL)

    def sensor_read(self):
        self.logger.debug("Sonar %s sensor read thread started", self.info["id"])
        while self.info["enabled"]:
            time.sleep(1.0 / self.info["hz"])
            if self.robot_pose is None:
                continue

            val = 0
            if self.info["mode"] == "mock":
                val = float(random.uniform(30, 10))
            elif self.info["mode"] == "simulation":
                try:
                    # Get the place of the sensor from tf
                    res = self.get_tf_rpc.call({
                        "name": self.info["name"]
                    })
                    ths = res['theta']
                    # Calculate distance
                    d = 1
                    originx = res["x"] / self.robot_pose["resolution"]
                    originy = res["y"] / self.robot_pose["resolution"]
                    tmpx = originx
                    tmpy = originy
                    # print("Sonar: ", originx, originy)
                    limit = self.info["max_range"] / self.robot_pose["resolution"]
                    while self.map[int(tmpx), int(tmpy)] == 0 and d < limit:
                        d += 1
                        tmpx = originx + d * math.cos(ths)
                        tmpy = originy + d * math.sin(ths)
                    val = d * self.robot_pose["resolution"] + random.uniform(-0.03, 0.03)
                    if val > self.info["max_range"]:
                        val = self.info["max_range"]
                    if val < 0:
                        val = 0
                except Exception as e: # pylint: disable=broad-except
                    self.logger.warning("Error in sonar %s sensor read thread: %s", self.name, str(e))

            # Publishing value:
            self.publisher.publish({
                "distance": val,
                "timestamp": time.time()
            })
            # self.logger.info("Sonar reads: %f",  val)

        self.logger.debug("Sonar %s sensor read thread stopped", self.info["id"])

    def enable_callback(self, message):
        self.info["enabled"] = True
        self.info["hz"] = message["hz"]
        self.info["queue_size"] = message["queue_size"]

        self.memory = self.info["queue_size"] * [0]
        self.sensor_read_thread = threading.Thread(target = self.sensor_read)
        self.sensor_read_thread.start()
        return {"enabled": True}

    def disable_callback(self, message):
        self.info["enabled"] = False
        self.logger.info("Sonar {} stops reading".format(self.info["id"]))
        return {"enabled": False}

    def start(self):
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)
        self.logger.info("Sensor %s started", self.name)

        if self.info["enabled"]:
            self.memory = self.info["queue_size"] * [0]
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info("Sonar {} reads with {} Hz".format(self.info["id"], self.info["hz"]))

    def stop(self):
        self.info["enabled"] = False
        self.commlib_factory.stop()
