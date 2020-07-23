#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random

from commlib_py.logger import Logger
from derp_me.client import DerpMeClient

from stream_simulator import ConnParams
if ConnParams.type == "amqp":
    from commlib_py.transports.amqp import RPCServer
elif ConnParams.type == "redis":
    from commlib_py.transports.redis import RPCServer

class ImuController:
    def __init__(self, info = None):
        self.logger = Logger(info["name"] + "-" + info["id"])

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]

        self.derp_client = DerpMeClient(conn_params=ConnParams.get())

        if self.info["mode"] == "real":
            from pidevices import ICM_20948
            self.sensor = ICM_20948(3) ## CHECK BUS??
            ## https://github.com/robotics-4-all/tektrain-ros-packages/blob/master/ros_packages/robot_hw_interfaces/imu_hw_interface/imu_hw_interface/imu_hw_interface.py

        self.memory = 100 * [0]

        self.imu_rpc_server = RPCServer(conn_params=ConnParams.get(), on_request=self.imu_callback, rpc_name=info["base_topic"] + "/get")
        self.enable_rpc_server = RPCServer(conn_params=ConnParams.get(), on_request=self.enable_callback, rpc_name=info["base_topic"] + "/enable")
        self.disable_rpc_server = RPCServer(conn_params=ConnParams.get(), on_request=self.disable_callback, rpc_name=info["base_topic"] + "/disable")

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
                self.memory_write(val)

                r = self.derp_client.lset(
                    self.info["namespace"][1:] + ".variables.robot.imu.roll",
                    [{"data": val["magne"]["roll"], "timestamp": time.time()}])
                r = self.derp_client.lset(
                    self.info["namespace"][1:] + ".variables.robot.imu.pitch",
                    [{"data": val["magne"]["pitch"], "timestamp": time.time()}])
                r = self.derp_client.lset(
                    self.info["namespace"][1:] + ".variables.robot.imu.yaw",
                    [{"data": val["magne"]["yaw"], "timestamp": time.time()}])


            elif self.info["mode"] == "simulation":
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
                self.memory_write(val)

                r = self.derp_client.lset(
                    self.info["namespace"][1:] + ".variables.robot.imu.roll",
                    [{"data": val["magne"]["roll"], "timestamp": time.time()}])
                r = self.derp_client.lset(
                    self.info["namespace"][1:] + ".variables.robot.imu.pitch",
                    [{"data": val["magne"]["pitch"], "timestamp": time.time()}])
                r = self.derp_client.lset(
                    self.info["namespace"][1:] + ".variables.robot.imu.yaw",
                    [{"data": val["magne"]["yaw"], "timestamp": time.time()}])
            else: # The real deal
                self.logger.warning("{} mode not implemented for {}".format(self.info["mode"], self.name))

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
