#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random

from .conn_params import ConnParams
if ConnParams.type == "amqp":
    from commlib.transports.amqp import RPCService
elif ConnParams.type == "redis":
    from commlib.transports.redis import RPCService

from commlib.logger import Logger
from derp_me.client import DerpMeClient

class GstreamerServerController:
    def __init__(self, info = None):
        self.logger = Logger(info["name"] + "-" + info["id"])

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]

        self.derp_client = DerpMeClient(conn_params=ConnParams.get())

        self.enable_rpc_server = RPCService(conn_params=ConnParams.get(), on_request=self.enable_callback, rpc_name=info["base_topic"] + "/enable")
        self.disable_rpc_server = RPCService(conn_params=ConnParams.get(), on_request=self.disable_callback, rpc_name=info["base_topic"] + "/disable")

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
            Gst.init()
            self.stream = Gst.parse_launch("{} ! audioconvert ! audioresample !"
                                           "audio/x-raw, rate=16000, channels=1,"
                                           " format=S16LE !"
                                           " multiudpsink clients={}".format(
                                               self.conf["alsa_device"], hosts_ports))

            self.logger.info("GStreamer Server is up (?)")

            self.stream.set_state(Gst.State.PLAYING)
