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
    from commlib.transports.amqp import ActionServer, RPCService, Subscriber, Publisher
elif ConnParams.type == "redis":
    from commlib.transports.redis import ActionServer, RPCService, Subscriber, Publisher

class CytronLFController:
    def __init__(self, info = None, logger = None, derp = None):
        if logger is None:
            self.logger = Logger(info["name"] + "-" + info["id"])
        else:
            self.logger = logger

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]
        self.base_topic = info["base_topic"]
        self.streamable = info["streamable"]

        _topic = self.base_topic + ".data"
        self.publisher = Publisher(
            conn_params=ConnParams.get("redis"),
            topic=_topic
        )
        self.logger.info(f"{Fore.GREEN}Created redis Publisher {_topic}{Style.RESET_ALL}")

        if self.info["mode"] == "real":
            from pidevices import CytronLfLSS05Mcp23017

            self.lf_sensor = CytronLfLSS05Mcp23017(bus=self.conf["bus"],
                                                address=self.conf["address"],
                                                mode=self.conf["mode"],
                                                so_1=self.conf["so_1"],
                                                so_2=self.conf["so_2"],
                                                so_3=self.conf["so_3"],
                                                so_4=self.conf["so_4"],
                                                so_5=self.conf["so_5"],
                                                cal=self.conf["cal"],
                                                name=self.name,
                                                max_data_length=self.conf["max_data_length"])

        self.memory = 100 * [0]

        _topic = info["base_topic"] + ".get"
        self.cytron_lf_rpc_server = RPCService(
            conn_params=ConnParams.get("redis"),
            on_request=self.cytron_lf_callback,
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

    def robot_pose_update(self, message, meta):
        self.robot_pose = message

    def sensor_read(self):
        self.logger.info("Cytron-LF {} sensor read thread started".format(self.info["id"]))

        while self.info["enabled"]:
            time.sleep(1.0 / self.info["hz"])

            val = {}

            if self.info["mode"] == "mock":
                val = {
                    "so_1": 1 if (random.uniform(0,1) > 0.5) else 0,
                    "so_2": 1 if (random.uniform(0,1) > 0.5) else 0,
                    "so_3": 1 if (random.uniform(0,1) > 0.5) else 0,
                    "so_4": 1 if (random.uniform(0,1) > 0.5) else 0,
                    "so_5": 1 if (random.uniform(0,1) > 0.5) else 0
                }

            elif self.info["mode"] == "simulation":
                try:
                    val = {
                        "so_1": 1 if (random.uniform(0,1) > 0.5) else 0,
                        "so_2": 1 if (random.uniform(0,1) > 0.5) else 0,
                        "so_3": 1 if (random.uniform(0,1) > 0.5) else 0,
                        "so_4": 1 if (random.uniform(0,1) > 0.5) else 0,
                        "so_5": 1 if (random.uniform(0,1) > 0.5) else 0
                    }
                except:
                    self.logger.warning("Pose not got yet..")
            else: # The real deal
                data = self.lf_sensor.read()

                val = data._asdict()

            self.memory_write(val)

            self.publisher.publish({
                'so_1': val['so_1'],
                'so_2': val['so_2'],
                'so_3': val['so_3'],
                'so_4': val['so_4'],
                'so_5': val['so_5']
            })

        self.logger.info("Cytron-LF {} sensor read thread stopped".format(self.info["id"]))

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
        self.logger.info("Cytron-LF {} stops reading".format(self.info["id"]))
        return {"enabled": False}

    def start(self):
        self.cytron_lf_rpc_server.run()
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        if self.info["mode"] == "real":
            self.lf_sensor.calibrate()

        if self.info["enabled"]:
            self.memory = self.info["queue_size"] * [0]
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info("Cytron Line Follower {} reads with {} Hz".format(self.info["id"], self.info["hz"]))

    def stop(self):
        self.info["enabled"] = False
        self.cytron_lf_rpc_server.stop()
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()

        self.sensor_read_thread.join()

        # if we are on "real" mode and the controller has started then Terminate it
        if self.info["mode"] == "real":
            self.lf_sensor.stop()

    def memory_write(self, data):
        del self.memory[-1]
        self.memory.insert(0, data)

    def cytron_lf_callback(self, message, meta):
        if self.info["enabled"] is False:
            return {"data": []}

        self.logger.info("Robot {}: Cytron lf callback: {}".format(self.name, message))
        try:
            _to = message["from"] + 1
            _from = message["to"]
        except Exception as e:
            self.logger.error("{}: Malformed message for Cytron lf: {} - {}".format(self.name, str(e.__class__), str(e)))
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
                "so_1": self.memory[-i]["so_1"],
                "so_2": self.memory[-i]["so_2"],
                "so_3": self.memory[-i]["so_3"],
                "so_4": self.memory[-i]["so_4"],
                "so_5": self.memory[-i]["so_5"]
            })
        return ret
