#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random
from colorama import Fore, Style

from .conn_params import ConnParams
if ConnParams.type == "amqp":
    from commlib.transports.amqp import RPCService, Subscriber
elif ConnParams.type == "redis":
    from commlib.transports.redis import RPCService, Subscriber

from commlib.logger import Logger
from derp_me.client import DerpMeClient

class ButtonController:
    def __init__(self, info = None):
        self.logger = Logger(info["name"] + "-" + info["id"])

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]

        self.derp_client = DerpMeClient(conn_params=ConnParams.get())

        if self.info["mode"] == "real":
            from pidevices import ButtonMcp23017
            self.sensor = ButtonMcp23017(bus=self.conf["bus"],
                                         address=self.conf["address"],
                                         pin_num=self.conf["pin_num"],
                                         direction=self.conf["direction"],
                                         edge=self.conf["edge"],
                                         bounce=self.conf["bounce"],
                                         name=self.name,
                                         max_data_length=self.conf["max_data_length"])

            self.sensor.when_pressed(self.real_button_pressed)
            #### Continue implementation: https://github.com/robotics-4-all/tektrain-ros-packages/blob/master/ros_packages/robot_hw_interfaces/button_hw_interface/button_hw_interface/button_hw_interface.py
        elif self.info["mode"] == "simulation":
            _topic = self.info['device_name'] + "/buttons_sim"
            self.sim_button_pressed_sub = Subscriber(
                conn_params=ConnParams.get(),
                topic = _topic,
                on_message = self.sim_button_pressed)

            self.logger.info(f"{Fore.GREEN}Created redis Subscriber {_topic}{Style.RESET_ALL}")

            self.sim_button_pressed_sub.run()

        self.memory = 100 * [0]
        self.val = 0
        self.prev = 0

        _topic = info["base_topic"] + "/get"
        self.button_rpc_server = RPCService(conn_params=ConnParams.get(), on_request=self.button_callback, rpc_name=_topic)
        self.logger.info(f"{Fore.GREEN}Created redis RPCService {_topic}{Style.RESET_ALL}")

        self.enable_rpc_server = RPCService(conn_params=ConnParams.get(), on_request=self.enable_callback, rpc_name=info["base_topic"] + "/enable")

        self.disable_rpc_server = RPCService(conn_params=ConnParams.get(), on_request=self.disable_callback, rpc_name=info["base_topic"] + "/disable")

    def real_button_pressed(self):
        r = self.derp_client.lset(
            self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.buttons." + self.info["place"],
            [{
                "data": 1,
                "timestamp": time.time()
            }])
        r = self.derp_client.lset(
            self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.buttons.touch_detected",
            [{
                "data": 1,
                "timestamp": time.time()
            }])
        r = self.derp_client.lset(
            self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.buttons.pressed_part",
            [{
                "data": "Tactile." + self.info["place"],
                "timestamp": time.time()
            }])

        self.logger.warning("Button controller: Pressed from real! ")

    def sim_button_pressed(self, data, meta):
        if data["button"] == self.info["place"]:
            r = self.derp_client.lset(
                self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.buttons." + self.info["place"],
                [{
                    "data": 1,
               	    "timestamp": time.time()
                }])
            r = self.derp_client.lset(
                self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.buttons.touch_detected",
                [{
                    "data": 1,
                    "timestamp": time.time()
                }])
            r = self.derp_client.lset(
                self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.buttons.pressed_part",
                [{
                    "data": "Tactile." + self.info["place"],
                    "timestamp": time.time()
                }])

            self.logger.warning(f"Button controller: Pressed from sim! {data}")

    def sensor_read(self):
        self.logger.info(f"Button {self.info['id']} sensor read thread started")
        while self.info["enabled"]:
            time.sleep(1.0 / self.info["hz"])

            if self.info["mode"] == "mock":
                self.val = float(random.randint(0,1))

                r = self.derp_client.lset(
                    self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.buttons." + self.info["place"],
                    [{
                        "data": self.val,
                        "timestamp": time.time()
                    }])
                if self.val != 0:
                    r = self.derp_client.lset(
                        self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.buttons.touch_detected",
                        [{
                            "data": self.val,
                            "timestamp": time.time()
                        }])
                    r = self.derp_client.lset(
                        self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.buttons.pressed_part",
                        [{
                            "data": "Tactile." + self.info["place"],
                            "timestamp": time.time()
                        }])

        self.logger.info(f"Button {self.info['id']} sensor read thread stopped")

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
        self.logger.info(f"Button {self.info['id']} stops reading")
        return {"enabled": False}

    def start(self):
        self.button_rpc_server.run()
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        if self.info["enabled"]:
            self.memory = self.info["queue_size"] * [0]
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info(f"Button {self.info['id']} reads with {self.info['hz']} Hz")

    def stop(self):
        self.info["enabled"] = False
        self.button_rpc_server.stop()
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()

    def memory_write(self, data):
        del self.memory[-1]
        self.memory.insert(0, data)
        # self.logger.info("Robot {}: memory updated for {}".format(self.name, "button"))

    def button_callback(self, message, meta):
        if self.info["enabled"] is False:
            return {"data": []}

        self.logger.info(f"Robot {self.name}: Button callback: {message}")
        try:
            _to = message["from"] + 1
            _from = message["to"]
        except Exception as e:
            self.logger.error(f"{self.name}: Malformed message for button: {e.__class__} - {e}")
            return []
        ret = {"data": []}

        try:
            r = self.derp_client.lget(
                self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.buttons." + self.info["place"], _from, _to)
            for rr in r['val']:
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
                    "change": rr['data']
                })

        except:
            pass

        return ret
