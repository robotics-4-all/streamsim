#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random
from colorama import Fore, Style

from stream_simulator.base_classes import BaseThing

current_milli_time = lambda: int(round(time.time() * 1000))

class ButtonArrayController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        id = "d_button_array_" + str(BaseThing.id + 1)

        name = id
        _category = "sensor"
        _class = "button_array"
        _subclass = "tactile"
        _pack = package["name"]
        _namespace = package["namespace"]

        super().__init__(id, auto_start=False)

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

        self.set_tf_communication(package)
        self.set_simulation_communication(_namespace)

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]
        self.base_topic = info["base_topic"]

        self.buttons_base_topics = self.conf["base_topics"]
        self.publishers = {}

        self.number_of_buttons = len(self.conf["places"])
        self.values = [True] * self.number_of_buttons         # multiple values
        self.button_places = self.conf["places"]
        self.prev = 0

        for b in self.buttons_base_topics:
            self.publishers[b] = self.commlib_factory.getPublisher(
                topic = self.buttons_base_topics[b] + ".data"
            )

        self.enable_rpc_server = self.commlib_factory.getRPCService(
            callback = self.enable_callback,
            rpc_name = info["base_topic"] + ".enable"
        )
        self.disable_rpc_server = self.commlib_factory.getRPCService(
            callback = self.disable_callback,
            rpc_name = info["base_topic"] + ".disable"
        )

        if self.info["mode"] == "simulation":
            self.sim_button_pressed_sub = self.commlib_factory.getSubscriber(
                topic = _namespace + "." + self.info['device_name'] + ".buttons_sim.internal",
                callback = self.sim_button_pressed
            )

        self.commlib_factory.run()

    def dispatch_information(self, _data, _button):
        # Publish to stream
        self.publishers[_button].publish({
            "data": _data,
            "timestamp": time.time()
        })

    def sim_button_pressed(self, data):
        self.logger.warning(f"Button controller: Pressed from sim! {data}")
        # Simulated press
        self.dispatch_information(1, data["button"])
        time.sleep(0.1)
        # Simulated release
        self.dispatch_information(0, data["button"])

    def sensor_read(self):
        self.logger.info(f"Button {self.info['id']} sensor read thread started")
        while self.info["enabled"]:
            time.sleep(1.0 / self.info["hz"])
            if self.info["mode"] == "mock":
                _val = float(random.randint(0,1))
                _place = random.randint(0, len(self.button_places) - 1)

                self.dispatch_information(_val, self.button_places[_place])

        self.logger.info(f"Button {self.info['id']} sensor read thread stopped")

    def start(self):
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)
        self.logger.info("Sensor %s started", self.name)

        if self.info["mode"] == "mock":
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info(f"Button {self.info['id']} reads with {self.info['hz']} Hz")

    def stop(self):
        self.info["enabled"] = False
        self.commlib_factory.stop()

    def enable_callback(self, message):
        self.info["enabled"] = True
        self.info["hz"] = message["hz"]
        self.info["queue_size"] = message["queue_size"]

        if self.info["mode"] == "mock":
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()

        return {"enabled": True}

    def disable_callback(self, message):
        self.info["enabled"] = False
        self.logger.info(f"Button {self.info['id']} stops reading")
        return {"enabled": False}
