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

class LedsController(BaseThing):
    WAIT_MS = 50

    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = Logger(conf["name"])
        else:
            self.logger = package["logger"]

        super(self.__class__, self).__init__()
        id = "d_" + str(BaseThing.id)
        name = id
        if 'name' in conf:
            name = conf['name']
        _category = "actuator"
        _class = "visual"
        _subclass = "leds"
        _pack = package["name"]

        info = {
            "type": "LED",
            "brand": "neopx",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": name,
            "place": conf["place"],
            "id": id,
            "enabled": True,
            "orientation": conf["orientation"],
            "queue_size": 0,
            "mode": package["mode"],
            "speak_mode": package["speak_mode"],
            "namespace": package["namespace"],
            "sensor_configuration": conf["sensor_configuration"],
            "device_name": package["device_name"],
            "categorization": {
                "host_type": "robot",
                "place": _pack.split(".")[-1],
                "category": _category,
                "class": _class,
                "subclass": [_subclass],
                "name": name
            }
        }

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]
        self.base_topic = info["base_topic"]
        self.derp_data_key = info["base_topic"] + ".raw"

        # tf handling
        tf_package = {
            "type": "robot",
            "subtype": {
                "category": _category,
                "class": _class,
                "subclass": [_subclass]
            },
            "pose": conf["pose"],
            "base_topic": info['base_topic'],
            "name": self.name
        }
        tf_package['host'] = package['device_name']
        tf_package['host_type'] = 'robot'
        if 'host' in conf:
            tf_package['host'] = conf['host']
            tf_package['host_type'] = 'pan_tilt'
        package["tf_declare"].call(tf_package)

        self._color = {
                'r': 0.0,
                'g': 0.0,
                'b': 0.0
        }
        self._brightness = 0

        if 'led_type' not in self.conf:
            self.conf['led_type'] == "none"

        if self.info["mode"] == "real":
            try:
                if self.conf['led_type'] == "respeaker":
                    from pidevices import LedRespeaker

                    self.leds = LedRespeaker(
                        led_brightness=self.conf['led_brightness'], 
                        name=self.conf['name']
                    )
                else:
                    from pidevices import Neopixel

                    self.leds = LedController(
                        led_count=self.conf['led_count'],
                        led_pin=self.conf['led_pin'],
                        led_freq_hz=self.conf['led_freq_hz'],
                        led_brightness=self.conf['led_brightness'],
                        led_invert=self.conf['led_invert'],
                        led_channel=self.conf['led_channel'],
                        name=self.conf['name']
                    )
            except Exception as e:
                self.logger.error("Error occured when initializing {} leds: {}.".format(
                    self.conf['led_type'], 
                    e
                ))

                self.leds = None
        #############################################

        self.events = []
        self.events_fields = {}

        if 'events' in self.conf:
            for event in self.conf['events']:
                try:
                    self.events.append(
                        CommlibFactory.getSubscriber(
                            broker = "redis",
                            callback = self.event_cb,
                            topic = event['topic']
                        )
                    )
                    self.events_fields[event['topic']] = {
                        "color": event['color'],
                        "effect": event['effect'],
                        "duration": int(event['duration'])
                    }
                except Exception as e:
                    self.logger.error("Failed to create event for topic: {}".format(
                        event['topic']
                    ))
        else:
            self.logger.warning("No event section in Led Controller")

        self.get_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.leds_get_callback,
            rpc_name = info["base_topic"] + ".get"
        )
        self.leds_wipe_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.leds_wipe_callback,
            rpc_name = info["base_topic"] + ".wipe"
        )
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
    
    def event_cb(self, message, meta):
        try:
            color = self.events_fields[message['uri']]['color']
            effect = self.events_fields[message['uri']]['effect']
            duration = self.events_fields[message['uri']]['duration']

            status = self.animation(color, effect, duration)

            if status == -1:
                self.logger.warning("Invalid effect for event: {}".format(
                    message['uri']
                ))
            elif status == -2:
                self.logger.warning("Animation not implemented for led type: {}".format(
                    self.conf["led_type"]
                ))
            else:
                self.logger.info("Setting color for event {} to the value {}".format(
                    message["uri"],
                    color
                ))
        except Exception as e:
            self.logger.error("Error when trying to set color for event: {} with message: {}".format(
                message["uri"],
                e
            ))

    def animation(self, color, effect, duration):
        if self.conf["led_type"] == "respeaker":
            if effect == "none":
                self.leds.write(data=[color], wipe=True)
            elif  effect == "listen":
                hex_color = self.leds.rgb_to_hex(color)
                self.leds.pixel_ring.set_color_palette(hex_color, 0x003333)
                self.leds.pixel_ring.listen()
            elif effect == "think":
                hex_color = self.leds.rgb_to_hex(color)
                self.leds.pixel_ring.set_color_palette(hex_color, 0x003333)
                self.leds.pixel_ring.think()
            elif  effect == "spin":
                hex_color = self.leds.rgb_to_hex(color)
                self.leds.pixel_ring.set_color_palette(hex_color, 0x003333)
                self.leds.pixel_ring.spin()
            elif  effect == "speak":
                hex_color = self.leds.rgb_to_hex(color)
                self.leds.pixel_ring.set_color_palette(hex_color, 0x003333)
                self.leds.pixel_ring.speak()
            else:
                return -1

            if duration > 0:
                time.sleep(duration) 
                self.leds.write(data=[[0, 0, 0, 0]], wipe=True)
            
            return 0
        else:
            return -2
            

    def event_start_listenning_callback(self, message, meta):
        self.leds.write(data=[[255, 0, 0, 255]], wipe=True)

    def event_stop_listenning_callback(self, message, meta):
        self.leds.write(data=[[0, 0, 0, 0]], wipe=True)

    def enable_callback(self, message, meta):
        self.info["enabled"] = True
        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        self.get_rpc_server.run()
        self.leds_wipe_server.run()
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        for event in self.events:
            event.run()
       

    def stop(self):
        self.get_rpc_server.stop()
        self.leds_wipe_server.stop()
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()
        
        for event in self.events:
            event.stop()

    def leds_get_callback(self, message, meta):
        self.logger.info(f"Getting led state!")
        return {
            "color": self._color,
            "luminosity": self._brightness
        }

    def leds_wipe_callback(self, message, meta):
        try:
            response = message

            r = response["r"]
            g = response["g"]
            b = response["b"]
            brightness = response["brightness"]
            wait_ms = response["wait_ms"] if "wait_ms" in response else LedsController.WAIT_MS

            self._color = [r, g, b, brightness]
            self._brightness = brightness

            CommlibFactory.notify_ui(
                type = "robot_effectors",
                data = {
                    "name": self.name,
                    "robot": self.info["device_name"],
                    "value": {
                        'r': r,
                        'g': g,
                        'b': b,
                        'brightness': brightness
                    }
                }
            )

            if self.info["mode"] == "mock":
                pass
            elif self.info["mode"] == "simulation":
                pass
            else: # The real deal
                self.leds.write(data=[self._color], wait_ms=wait_ms, wipe=True)

            r = CommlibFactory.derp_client.lset(
                self.derp_data_key,
                [{
                    "data": {"r": r, "g": g, "b": b, "brightness": brightness},
                    "type": "wipe",
                    "timestamp": time.time()
                }]
            )

            self.logger.info("{}: New leds wipe command: {}".format(self.name, message))

        except Exception as e:
            self.logger.error("{}: leds_wipe is wrongly formatted: {} - {}".format(self.name, str(e.__class__), str(e)))

        return {}
