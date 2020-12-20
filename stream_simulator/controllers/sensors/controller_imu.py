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

class ImuController:
    def __init__(self, info = None, logger = None):
        if logger is None:
            self.logger = Logger(info["name"])
        else:
            self.logger = logger

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]
        self.base_topic = info["base_topic"]
        self.derp_data_key = info["base_topic"] + ".raw"

        self.publisher = CommlibFactory.getPublisher(
            broker = "redis",
            topic = self.base_topic + ".data"
        )

        if self.info["mode"] == "real":
            from pidevices import ICM_20948
            from .imu_calibration import IMUCalibration

            self._sensor = ICM_20948(self.conf["bus"]) # connect to bus (1)
            self._imu_calibrator = IMUCalibration(calib_time=5, buf_size=5)
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
        self.robot_pose = message

    def sensor_read(self):
        self.logger.info("IMU {} sensor read thread started".format(self.info["id"]))
        while self.info["enabled"]:
            time.sleep(1.0 / self.info["hz"])

            if self.info["mode"] == "mock":
                val = {
                    "accel": {
                        "x": 1,
                        "y": 1,
                        "z": 1
                    },
                    "gyro": {
                        "yaw": random.uniform(0.3, -0.3),
                        "pitch": random.uniform(0.3, -0.3),
                        "roll": random.uniform(0.3, -0.3)
                    },
                    "magne": {
                        "yaw": random.uniform(0.3, -0.3),
                        "pitch": random.uniform(0.3, -0.3),
                        "roll": random.uniform(0.3, -0.3)
                    }
                }

            elif self.info["mode"] == "simulation":
                try:
                    val = {
                        "accel": {
                            "x": random.uniform(0.3, -0.3),
                            "y": random.uniform(0.3, -0.3),
                            "z": random.uniform(0.3, -0.3)
                        },
                        "gyro": {
                            "yaw": random.uniform(0.3, -0.3),
                            "pitch": random.uniform(0.3, -0.3),
                            "roll": random.uniform(0.3, -0.3)
                        },
                        "magne": {
                            "yaw": self.robot_pose["theta"] + random.uniform(0.3, -0.3),
                            "pitch": random.uniform(0.3, -0.3),
                            "roll": random.uniform(0.3, -0.3)
                        }
                    }
                except:
                    self.logger.warning("Pose not got yet..")
            else: # The real deal
                data = self._sensor.read()

                self._imu_calibrator.update(data)

                val = self._imu_calibrator.getCalibData()

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
            self.memory = self.info["queue_size"] * [0]
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info("IMU {} reads with {} Hz".format(self.info["id"], self.info["hz"]))

            if self.info["mode"] == "real":
                # it the mode is real enable the calibration
                self._imu_calibrator.start()

    def stop(self):
        self.info["enabled"] = False
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()
        if self.info["mode"] == "simulation":
            self.robot_pose_sub.stop()
