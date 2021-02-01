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

current_milli_time = lambda: int(round(time.time() * 1000))

class ButtonArrayController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = Logger(conf["name"])
        else:
            self.logger = package["logger"]

        super(self.__class__, self).__init__()
        id = "d_" + str(BaseThing.id)

        name = id
        _category = "sensor"
        _class = "button_array"
        _subclass = "tactile"
        _pack = package["name"]

        info = {
            "type": "BUTTON_ARRAY",
            "brand": "simple",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": "button_array_" + str(id),
            "place": "UNKNOWN",
            "id": id,
            "enabled": True,
            "orientation": 0,
            "hz": 4,
            "mode": package["mode"],
            "speak_mode": package["speak_mode"],
            "namespace": package["namespace"],
            "sensor_configuration": conf["sensor_configuration"],
            "device_name": package["device_name"]
        }

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]
        self.base_topic = info["base_topic"]

        self.buttons_base_topics = self.conf["base_topics"]
        self.publishers = {}
        self.derp_data_keys = {}

        self.number_of_buttons = len(self.conf["pin_nums"])
        self.values = [True] * self.number_of_buttons         # multiple values
        self.button_places = self.conf["places"]
        self.prev = 0

        for b in self.buttons_base_topics:
            self.publishers[b] = CommlibFactory.getPublisher(
                broker = "redis",
                topic = self.buttons_base_topics[b] + ".data"
            )
            self.derp_data_keys[b] = self.buttons_base_topics[b] + ".raw"

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

        if self.info["mode"] == "real":
            from pidevices import ButtonArrayMcp23017
            self.sensor = ButtonArrayMcp23017(
                pin_nums=self.conf["pin_nums"],
                direction=self.conf["direction"],
                bounce=self.conf["bounce"],
                name=self.name,
                max_data_length=10
            )

        elif self.info["mode"] == "simulation":
            self.sim_button_pressed_sub = CommlibFactory.getSubscriber(
                broker = "redis",
                topic = self.info['device_name'] + ".buttons_sim",
                callback = self.sim_button_pressed
            )
            self.sim_button_pressed_sub.run()

    def dispatch_information(self, _data, _button):
        # Publish to stream
        self.publishers[_button].publish({
            "data": _data,
            "timestamp": time.time()
        })
        # Set in memory
        r = CommlibFactory.derp_client.lset(
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
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        if self.info["mode"] == "real":
            for pin_num in range(self.number_of_buttons):
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
        self.info["enabled"] = True
        self.info["hz"] = message["hz"]
        self.info["queue_size"] = message["queue_size"]

        if self.info["mode"] == "mock":
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()

        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        self.logger.info(f"Button {self.info['id']} stops reading")
        return {"enabled": False}
