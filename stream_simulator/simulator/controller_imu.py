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
from derp_me.client import DerpMeClient

from .conn_params import ConnParams
if ConnParams.type == "amqp":
    from commlib.transports.amqp import RPCService, Subscriber, Publisher
elif ConnParams.type == "redis":
    from commlib.transports.redis import RPCService, Subscriber, Publisher

class ImuController:
    def __init__(self, info = None, logger = None, derp = None):
        if logger is None:
            self.logger = Logger(info["name"] + "-" + info["id"])
        else:
            self.logger = logger

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]
        self.base_topic = info["base_topic"]

        _topic = self.base_topic + ".data"
        self.publisher = Publisher(
            conn_params=ConnParams.get("redis"),
            topic=_topic
        )
        self.logger.info(f"{Fore.GREEN}Created redis Publisher {_topic}{Style.RESET_ALL}")

        if derp is None:
            self.derp_client = DerpMeClient(conn_params=ConnParams.get("redis"))
            self.logger.warning(f"New derp-me client from {info['name']}")
        else:
            self.derp_client = derp

        if self.info["mode"] == "real":
            from pidevices import ICM_20948
            from .imu_calibration import IMUCalibration

            self._sensor = ICM_20948(self.conf["bus"]) # connect to bus (1)
            self._imu_calibrator = IMUCalibration(calib_time=5, buf_size=5)

        self.memory = 100 * [0]

        _topic = info["base_topic"] + ".get"
        self.imu_rpc_server = RPCService(
            conn_params=ConnParams.get("redis"),
            on_request=self.imu_callback,
            rpc_name=_topic)
        self.logger.info(f"{Fore.GREEN}Created redis RPCService {_topic}{Style.RESET_ALL}")

        _topic = info["base_topic"] + ".enable"
        self.enable_rpc_server = RPCService(
            conn_params=ConnParams.get("redis"),
            on_request=self.enable_callback,
            rpc_name=_topic)
        self.logger.info(f"{Fore.GREEN}Created redis RPCService {_topic}{Style.RESET_ALL}")

        _topic = info["base_topic"] + ".disable"
        self.disable_rpc_server = RPCService(
            conn_params=ConnParams.get("redis"),
            on_request=self.disable_callback,
            rpc_name=_topic)
        self.logger.info(f"{Fore.GREEN}Created redis RPCService {_topic}{Style.RESET_ALL}")

        if self.info["mode"] == "simulation":
            _topic = self.info['namespace'] + '.' + self.info['device_name'] + ".pose"
            self.robot_pose_sub = Subscriber(
                conn_params=ConnParams.get("redis"),
                topic = _topic,
                on_message = self.robot_pose_update)
            self.logger.info(f"{Fore.GREEN}Created redis Subscriber {_topic}{Style.RESET_ALL}")
            self.robot_pose = {
                "x": 0,
                "y": 0,
                "theta": 0
            }

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

            self.memory_write(val)

            # Publish data to sensor stream
            self.publisher.publish({
                "data": val,
                "timestamp": time.time()
            })

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
        self.imu_rpc_server.run()
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
        self.imu_rpc_server.stop()
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()
        if self.info["mode"] == "simulation":
            self.robot_pose_sub.stop()

    def memory_write(self, data):
        del self.memory[-1]
        self.memory.insert(0, data)
        # self.logger.info("Robot {}: memory updated for {}".format(self.name, "imu"))

    def imu_callback(self, message, meta):
        if self.info["enabled"] is False:
            return {"data": []}

        self.logger.debug("Robot {}: Imu callback: {}".format(self.name, message))
        try:
            _to = message["from"] + 1
            _from = message["to"]
        except Exception as e:
            self.logger.error("{}: Malformed message for Imu: {} - {}".format(self.name, str(e.__class__), str(e)))
            return []
        ret = {"data": []}
        for i in range(_from, _to): # 0 to -1
            timestamp = time.time()
            secs = int(timestamp)
            nanosecs = int((timestamp-secs) * 10**(9))
            ret["data"].append({
                "header":{
                    "stamp":{
                        "sec": secs,
                        "nanosec": nanosecs
                    }
                },
                "accel": self.memory[-i]["accel"],
                "gyro": self.memory[-i]["gyro"],
                "magne": self.memory[-i]["magne"]
            })
        return ret
