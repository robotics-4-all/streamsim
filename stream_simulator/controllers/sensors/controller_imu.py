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
from stream_simulator.connectivity import CommlibFactory
from stream_simulator.base_classes import BaseThing

class ImuController(BaseThing):
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
        _class = "imu"
        _subclass = "accel_gyro_magne_temp"
        _pack = package["name"]

        info = {
            "type": "IMU",
            "brand": "icm_20948",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": name,
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
            "device_name": package["device_name"],
            "categorization": {
                "host_type": "robot",
                "place": _pack.split(".")[-1],
                "category": _category,
                "class": _class,
                "subclass": ['acceleration', 'gyroscope', 'magnetometer'],
                "name": name
            }
        }

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]
        self.base_topic = info["base_topic"]
        self.derp_data_key = info["base_topic"] + ".raw"
        self.robot = _pack.split(".")[-1]
        self.prev_robot_pose = None

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

        if self.info["mode"] == "real":
            from pidevices import ICM_20948
            from motion_calibration import IMUCalibrator
            from motion_calibration.exception import CalibrationFileInvalid, CalibrationFileNotFound 

            path = "../stream_simulator/settings/imu_settings.json"
            
            try:
                self._calibrator = IMUCalibrator(path_to_settings=path)
            except CalibrationFileNotFound as err:
                self.logger.error(err)

            self._sensor = ICM_20948(self.conf["bus"])
            
        if self.info["mode"] == "simulation":
            self.robot_pose_sub = CommlibFactory.getSubscriber(
                broker = "redis",
                topic = self.info['namespace'] + '.' + self.info['device_name'] + ".pose",
                callback = self.robot_pose_update
            )

            self.robot_pose = {
                "x": 0,
                "y": 0,
                "theta": 0
            }

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

    def robot_pose_update(self, message, meta):
        if self.prev_robot_pose == None:
            self.prev_robot_pose = message
            self.prev_robot_pose['timestamp'] = time.time()
        else:
            self.prev_robot_pose = self.robot_pose

        self.robot_pose = message
        self.robot_pose['timestamp'] = time.time()

    def sensor_read(self):
        self.logger.info("IMU {} sensor read thread started".format(self.info["id"]))
        period = 1 / self.info["hz"]

        while self.info["enabled"]:
            time.sleep(period)
            
            if self.info["mode"] == "mock":
                val = {
                    "acceleration": {
                        "x": 1,
                        "y": 1,
                        "z": 1
                    },
                    "gyroscope": {
                        "yaw": random.uniform(0.3, -0.3),
                        "pitch": random.uniform(0.3, -0.3),
                        "roll": random.uniform(0.3, -0.3)
                    },
                    "magnetometer": {
                        "yaw": random.uniform(0.3, -0.3),
                        "pitch": random.uniform(0.3, -0.3),
                        "roll": random.uniform(0.3, -0.3)
                    }
                }

            elif self.info["mode"] == "simulation":
                moving = 0
                if time.time() - self.robot_pose['timestamp'] < 1.5:
                    # this means the pose is old and the robot has stopped
                    # print("moving")
                    moving = 1
                try:
                    val = {
                        "acceleration": {
                            "x": random.uniform(0.03, -0.03) + moving * 0.1,
                            "y": random.uniform(0.03, -0.03),
                            "z": random.uniform(0.03, -0.03)
                        },
                        "gyroscope": {
                            "yaw": random.uniform(0.03, -0.03),
                            "pitch": random.uniform(0.03, -0.03),
                            "roll": random.uniform(0.03, -0.03)
                        },
                        "magnetometer": {
                            "yaw": self.robot_pose["theta"] + random.uniform(0.03, -0.03),
                            "pitch": random.uniform(0.03, -0.03),
                            "roll": random.uniform(0.03, -0.03)
                        }
                    }
                    # import pprint
                    # pprint.pprint(val)
                    # print("")
                except:
                    self.logger.warning("Pose not got yet..")
            else: # The real deal
                data = self._sensor.read()
                
                try:
                    val = self._calibrator.convert(data=data)
                except CalibrationFileNotFound as err:
                    self.logger.warning(err)
                    val = data

            # Publish data to sensor stream
            self.publisher.publish({
                "data": val,
                "timestamp": time.time()
            })

            # Storing value:
            r = CommlibFactory.derp_client.lset(
                self.derp_data_key,
                [{
                    "data": val,
                    "timestamp": time.time()
                }]
            )

        self.logger.info("IMU {} sensor read thread stopped".format(self.info["id"]))

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
        self.logger.info("IMU {} stops reading".format(self.info["id"]))
        return {"enabled": False}

    def start(self):
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        if self.info["mode"] == "simulation":
            self.robot_pose_sub.run()

        if self.info["enabled"]:
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info("IMU {} reads with {} Hz".format(self.info["id"], self.info["hz"]))

            if self.info["mode"] == "real":
                self._sensor.start()

    def stop(self):
        self.info["enabled"] = False
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()
        if self.info["mode"] == "simulation":
            self.robot_pose_sub.stop()
        elif self.info["mode"] == 'real':
            self._sensor.stop()