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
    from commlib.transports.amqp import RPCService, Subscriber, Publisher
elif ConnParams.type == "redis":
    from commlib.transports.redis import RPCService, Subscriber, Publisher

from commlib.logger import Logger
from derp_me.client import DerpMeClient

current_milli_time = lambda: int(round(time.time() * 1000))

class ButtonArrayController():
    def __init__(self, info = None, logger = None, derp = None):
        if logger is None:
            self.logger = Logger(info["name"])
        else:
            self.logger = logger

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]
        self.base_topic = info["base_topic"]

        self.buttons_base_topics = self.conf["base_topics"]
        self.publishers = {}
        self.derp_data_keys = {}

        for b in self.buttons_base_topics:
            _topic = self.buttons_base_topics[b] + ".data"
            self.publishers[b] = Publisher(
                conn_params=ConnParams.get("redis"),
                topic=_topic
            )
            self.logger.info(f"{Fore.GREEN}Created redis Publisher {_topic}{Style.RESET_ALL}")

            self.derp_data_keys[b] = self.buttons_base_topics[b] + ".raw"

        if derp is None:
            self.derp_client = DerpMeClient(conn_params=ConnParams.get("redis"))
            self.logger.warning(f"New derp-me client from {info['name']}")
        else:
            self.derp_client = derp

        self.number_of_buttons = len(self.conf["pin_nums"])
        self.values = [True] * self.number_of_buttons         # multiple values
        self.button_places = self.conf["places"]
        self.prev = 0

        if self.info["mode"] == "real":
            from pidevices import ButtonArrayMcp23017
            self.sensor = ButtonArrayMcp23017(pin_nums=self.conf["pin_nums"],
                                                direction=self.conf["direction"],
                                                bounce=self.conf["bounce"],
                                                name=self.name,
                                                max_data_length=10)

        elif self.info["mode"] == "simulation":
            _topic = self.info['device_name'] + ".buttons_sim"
            self.sim_button_pressed_sub = Subscriber(
                conn_params=ConnParams.get("redis"),
                topic = _topic,
                on_message = self.sim_button_pressed)

            self.logger.info(f"{Fore.GREEN}Created redis Subscriber {_topic}{Style.RESET_ALL}")
            self.sim_button_pressed_sub.run()

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


    def dispatch_information(self, _data, _button):
        # Publish to stream
        self.publishers[_button].publish({
            "data": _data,
            "timestamp": time.time()
        })
        # Set in memory
        r = self.derp_client.lset(
            self.derp_data_keys[_button],
            [{
                "data": _data,
                "timestamp": time.time()
            }]
        )

    # Untested!!!
    def sim_button_pressed(self, data, meta):
        self.dispatch_information(1, data["button"])
        time.sleep(0.1)
        # Simulated release
        self.dispatch_information(0, data["button"])
        self.logger.warning(f"Button controller: Pressed from sim! {data}")

    def sensor_read(self):
        self.logger.info(f"Button {self.info['id']} sensor read thread started")
        while self.info["enabled"]:
            time.sleep(1.0 / self.info["hz"])
            if self.info["mode"] == "mock":
                _val = float(random.randint(0,1))
                _place = random.randint(0, len(self.button_places) - 1)

                self.dispatch_information(_val, self.button_places[_place])

        self.logger.info(f"Button {self.info['id']} sensor read thread stopped")

    # Untested!!!
    def real_button_pressed(self, button):
        if self.values[button] is False:
            return
        self.values[button] = False
        self.logger.info(f"Button {button} pressed at {current_milli_time()}")

        self.dispatch_information(1, self.button_places[button])

        self.values[button] = True

    def start(self):
        print("Button array starting")
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        if self.info["mode"] == "real":
            for pin_num in range(self.number_of_buttons):
                print("function assigned for button: ", pin_num)
                self.sensor.when_pressed(pin_num, self.real_button_pressed, pin_num)

            buttons = [i for i in range(self.number_of_buttons)]
            self.sensor.enable_pressed(buttons)
        if self.info["mode"] == "mock":
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info(f"Button {self.info['id']} reads with {self.info['hz']} Hz")

    def stop(self):
        self.info["enabled"] = False
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()

        self.sensor.stop()

    def enable_callback(self, message, meta):
        print("Button array starting")
        self.info["enabled"] = True
        self.info["hz"] = message["hz"]
        self.info["queue_size"] = message["queue_size"]

        if self.info["mode"] == "mock":
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()

        self.memory = self.info["queue_size"] * [0]
        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        self.logger.info(f"Button {self.info['id']} stops reading")
        return {"enabled": False}
