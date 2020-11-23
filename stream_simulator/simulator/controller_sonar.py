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

from .conn_params import ConnParams
if ConnParams.type == "amqp":
    from commlib.transports.amqp import RPCService, Subscriber, Publisher
elif ConnParams.type == "redis":
    from commlib.transports.redis import RPCService, Subscriber, Publisher

from derp_me.client import DerpMeClient

class SonarController:
    def __init__(self, info = None, map = None, logger = None, derp = None):
        if logger is None:
            self.logger = Logger(info["name"] + "-" + info["id"])
        else:
            self.logger = logger

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]
        self.map = map
        self.base_topic = info["base_topic"]
        self.streamable = info["streamable"]
        if self.streamable:
            _topic = self.base_topic + "/stream"
            self.publisher = Publisher(
                conn_params=ConnParams.get("redis"),
                topic=_topic
            )
            self.logger.info(f"{Fore.GREEN}Created redis Publisher {_topic}{Style.RESET_ALL}")
            _topic = self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.distance." + self.info["place"]
            self.var_publisher = Publisher(
                conn_params=ConnParams.get("redis"),
                topic=_topic
            )
            self.logger.info(f"{Fore.GREEN}Created redis Publisher {_topic}{Style.RESET_ALL}")

        if derp is None:
            self.derp_client = DerpMeClient(conn_params=ConnParams.get("redis"))
            self.logger.warning(f"New derp-me client from {info['name']}")
        else:
            self.derp_client = derp

        self.memory = 100 * [0]

        _topic = info["base_topic"] + "/get"
        self.sonar_rpc_server = RPCService(
            conn_params=ConnParams.get("redis"),
            on_request=self.sonar_callback,
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
            _topic =self.info['device_name'] + "/pose"
            self.robot_pose_sub = Subscriber(
                conn_params=ConnParams.get("redis"),
                topic = _topic,
                on_message = self.robot_pose_update)
            self.logger.info(f"{Fore.GREEN}Created redis Subscriber {_topic}{Style.RESET_ALL}")


    def robot_pose_update(self, message, meta):
        self.robot_pose = message

    def sensor_read(self):
        self.logger.debug("Sonar {} sensor read thread started".format(self.info["id"]))
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
                self.logger.warning("{} mode not implemented for {}".format(self.info["mode"], self.name))

            self.memory_write(val)

            if self.streamable:
                self.publisher.publish({
                    "data": val,
                    "timestamp": time.time()
                })
                self.var_publisher.publish({
                    "data": val,
                    "timestamp": time.time()
                })
            else:
                r = self.derp_client.lset(
                    self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.distance." + self.info["place"],
                    [{
                        "data": val,
                        "timestamp": time.time()
                    }])

        self.logger.debug("Sonar {} sensor read thread stopped".format(self.info["id"]))

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
        self.logger.info("Sonar {} stops reading".format(self.info["id"]))
        return {"enabled": False}

    def start(self):
        self.sonar_rpc_server.run()
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        if self.info["mode"] == "simulation":
            self.robot_pose_sub.run()

        if self.info["enabled"]:
            self.memory = self.info["queue_size"] * [0]
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info("Sonar {} reads with {} Hz".format(self.info["id"], self.info["hz"]))

    def stop(self):
        self.info["enabled"] = False
        self.sonar_rpc_server.stop()
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()

        if self.info["mode"] == "simulation":
            self.robot_pose_sub.stop()

    def memory_write(self, data):
        del self.memory[-1]
        self.memory.insert(0, data)
        # self.logger.info("Robot {}: memory updated for {}".format(self.name, "sonar"))

    def sonar_callback(self, message, meta):
        if self.info["enabled"] is False:
            return {"data": []}

        self.logger.info("Robot {}: sonar callback: {}".format(self.name, message))
        try:
            _to = message["from"] + 1
            _from = message["to"]
        except Exception as e:
            self.logger.error("{}: Malformed message for env: {} - {}".format(self.name, str(e.__class__), str(e)))
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
                "distance": self.memory[-i]
            })
        return ret
