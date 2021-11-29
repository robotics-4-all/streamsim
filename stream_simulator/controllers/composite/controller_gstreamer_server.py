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

class GstreamerServerController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = Logger(conf["name"])
        else:
            self.logger = package["logger"]

        super(self.__class__, self).__init__()
        id = "d_" + str(BaseThing.id)
        name = "gstreamer_" + str(id)
        if 'name' in conf:
            name = conf['name']
            id = name

        info = {
            "type": "GSTREAMER_SERVER",
            "brand": "gstream",
            "base_topic": package["name"] + ".sensor.audio.gstreamer." + str(id),
            "name": name,
            "place": conf["place"],
            "id": "id_" + str(id),
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
                "category": "server",
                "class": "streamer",
                "subclass": ['gstreamer'],
                "name": name
            }
        }

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]

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

    def enable_callback(self, message, meta):
        self.info["enabled"] = True
        self.start()
        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        self.stream.set_state(Gst.State.PAUSED)
        return {"enabled": False}

    def stop(self):
        pass

    def start(self):
        if self.info["mode"] == "real":
            import gi
            gi.require_version("Gst", "1.0")
            from gi.repository import Gst  # noqaE402

            self.conf["alsa_device"] = \
                "alsasrc device=dsnoop:CARD={},DEV=0".format(\
                self.conf["alsa_device"])

            # Concat hosts and ports
            # TODO check if the ports and hosts haven't the same lenght.
            hosts_ports = ""
            for h, p in zip(self.conf["hosts"][:-1], self.conf["ports"][:-1]):
                hosts_ports += "{}:{},".format(h, p)
            hosts_ports += "{}:{}".format(self.conf["hosts"][-1], self.conf["ports"][-1])

            # Create gstreamer stream pipeline
            Gst.init(None)
            self.stream = Gst.parse_launch("{} ! audioconvert ! audioresample !"
                                           "audio/x-raw, rate=16000, channels=1,"
                                           " format=S16LE !"
                                           " multiudpsink clients={}".format(
                                               self.conf["alsa_device"], hosts_ports))

            self.logger.info("GStreamer Server is up (?)")

            self.stream.set_state(Gst.State.PLAYING)
