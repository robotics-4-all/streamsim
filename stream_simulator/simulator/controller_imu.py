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
    from commlib.transports.amqp import RPCService, Subscriber
elif ConnParams.type == "redis":
    from commlib.transports.redis import RPCService, Subscriber

class ImuController:
    def __init__(self, info = None):
        self.logger = Logger(info["name"] + "-" + info["id"])

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]

        self.derp_client = DerpMeClient(conn_params=ConnParams.get("redis"))

        if self.info["mode"] == "real":
            from pidevices import ICM_20948
            self.sensor = ICM_20948(self.conf["bus"]) # connect to bus (1)
            ## https://github.com/robotics-4-all/tektrain-ros-packages/blob/master/ros_packages/robot_hw_interfaces/imu_hw_interface/imu_hw_interface/imu_hw_interface.py

        self.memory = 100 * [0]

        _topic = info["base_topic"] + "/get"
        self.imu_rpc_server = RPCService(
            conn_params=ConnParams.get("redis"),
            on_request=self.imu_callback,
            rpc_name=_topic)
        self.logger.info(f"{Fore.GREEN}Created redis RPCService {_topic}{Style.RESET_ALL}")

        self.enable_rpc_server = RPCService(
            conn_params=ConnParams.get("redis"),
            on_request=self.enable_callback,
            rpc_name=info["base_topic"] + "/enable")
        self.disable_rpc_server = RPCService(
            conn_params=ConnParams.get("redis"),
            on_request=self.disable_callback,
            rpc_name=info["base_topic"] + "/disable")

        if self.info["mode"] == "simulation":
            _topic = self.info['device_name'] + "/pose"
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

            val = {
                "accel": {
                    "x": 0,
                    "y": 0,
                    "z": 0
                },
                "gyro": {
                    "yaw": 0,
                    "pitch": 0,
                    "roll": 0
                },
                "magne": {
                    "yaw": 0,
                    "pitch": 0,
                    "roll": 0
                }
            }
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
                data = self.sensor.read()

                val["accel"]["x"] = data.accel.x
                val["accel"]["y"] = data.accel.y
                val["accel"]["z"] = data.accel.z

                val["gyro"]["x"] = data.gyro.z
                val["gyro"]["y"] = data.gyro.y
                val["gyro"]["z"] = data.gyro.x

                val["magne"]["x"] = data.magne.z
                val["magne"]["y"] = data.magne.y
                val["magne"]["z"] = data.magne.x
                
                #self.logger.warning("{} mode not implemented for {}".format(self.info["mode"], self.name))

            self.memory_write(val)

            r = self.derp_client.lset(
                self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.imu.roll",
                [{"data": val["magne"]["roll"], "timestamp": time.time()}])
            r = self.derp_client.lset(
                self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.imu.pitch",
                [{"data": val["magne"]["pitch"], "timestamp": time.time()}])
            r = self.derp_client.lset(
                self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.imu.yaw",
                [{"data": val["magne"]["yaw"], "timestamp": time.time()}])

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

        self.logger.info("Robot {}: Imu callback: {}".format(self.name, message))
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
