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

current_milli_time = lambda: int(round(time.time() * 1000))

class ButtonArrayController():
    def __init__(self, info = None, logger = None, derp = None):
        if logger is None:
            self.logger = Logger(info["name"] + "-" + info["id"])
        else:
            self.logger = logger

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]

        if derp is None:
            self.derp_client = DerpMeClient(conn_params=ConnParams.get("redis"))
            self.logger.warning(f"New derp-me client from {info['name']}")
        else:
            self.derp_client = derp

        if self.info["mode"] == "real":
            from pidevices import ButtonArrayMcp23017

            self.sensor = ButtonArrayMcp23017(pin_nums=self.conf["pin_nums"],
                                                direction=self.conf["direction"],
                                                bounce=self.conf["bounce"],
                                                name=self.name,
                                                max_data_length=10)

            self.number_of_buttons = len(self.conf["pin_nums"])
            #print("List length: ",self.number_of_buttons)

            self.memory = 100 * [0]
            self.values = [True] * self.number_of_buttons         # multiple values
            self.button_places = self.conf["places"]
            #print("Button places: ", self.button_places)

            self.prev = 0

        _topic = info["base_topic"] + "/get"
        self.button_array_rpc_server = RPCService(
            conn_params=ConnParams.get("redis"),
            on_request=self.button_array_callback,
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


    def real_button_pressed(self, button):
        if self.values[button] is False:
            return
        self.values[button] = False
        print("Button ", button, " pressed at ", current_milli_time())
        r = self.derp_client.lset(
            self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.buttons." + self.button_places[button],
            [{
                "data": button,
                "timestamp": time.time()
            }])
        r = self.derp_client.lset(
            self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.buttons.touch_detected",
            [{
                "data": button,
                "timestamp": time.time()
            }])
        r = self.derp_client.lset(
            self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.buttons.pressed_part",
            [{
                "data": "Tactile." + self.button_places[button],
                "timestamp": time.time()
            }])

        #self.logger.warning("Button controller: Pressed from real! ")
        self.values[button] = True


    def start(self):
        print("Button array starting")
        self.button_array_rpc_server.run()
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        if self.info["mode"] == "real":
            for pin_num in range(self.number_of_buttons):
                print("function assigned for button: ", pin_num)
                self.sensor.when_pressed(pin_num, self.real_button_pressed, pin_num)

            buttons = [i for i in range(self.number_of_buttons)]
            self.sensor.enable_pressed(buttons)


    def stop(self):
        self.info["enabled"] = False
        self.button__array_rpc_server.stop()
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()

        self.sensor.stop()


    def memory_write(self, data):
        del self.memory[-1]
        self.memory.insert(0, data)


    def enable_callback(self, message, meta):
        print("Button array starting")
        self.info["enabled"] = True
        self.info["hz"] = message["hz"]
        self.info["queue_size"] = message["queue_size"]

        self.memory = self.info["queue_size"] * [0]
        return {"enabled": True}


    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        self.logger.info(f"Button {self.info['id']} stops reading")
        return {"enabled": False}



    def button_array_callback(self, message, meta):
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
