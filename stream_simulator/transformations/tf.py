#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random
from colorama import Fore, Style
import pprint

from commlib.logger import Logger
from stream_simulator.connectivity import CommlibFactory

class TfController:
    def __init__(self, base = None, logger = None):
        self.logger = Logger("tf") if logger is None else logger
        self.base_topic = base + ".tf" if base is not None else "streamsim.tf"
        self.base = base

        self.declare_rpc_server = CommlibFactory.getRPCService(
            callback = self.declare_callback,
            rpc_name = self.base_topic + ".declare"
        )
        self.declare_rpc_server.run()

        self.get_declarations_rpc_server = CommlibFactory.getRPCService(
            callback = self.get_declarations_callback,
            rpc_name = self.base_topic + ".get_declarations"
        )
        self.get_declarations_rpc_server.run()

        self.declare_rpc_input = [
            'type', 'subtype', 'name', 'pose', 'base_topic', 'range', 'fov', \
            'host', 'host_type'
        ]

        self.declarations = []

    def start(self):
        self.declare_rpc_server.run()

    def stop(self):
        self.declare_rpc_server.stop()

    def get_declarations_callback(self, message, meta):
        return {"declarations": self.declarations}

    def setup(self):
        self.logger.info("*************** TF status ***************")
        self.hosts = []
        self.subs = {}
        self.places = {}
        self.tree = {}

        # Gather pan-tilts

        # Get all devices and check pan-tilts exist
        self.pantilts = {}

        get_devices_rpc = CommlibFactory.getRPCClient(
            rpc_name = self.base + ".get_device_groups"
        )
        res = get_devices_rpc.call({})

        # Pan tilts on robots
        for r in res['robots']:
            cl = CommlibFactory.getRPCClient(
                broker = "redis",
                rpc_name = f"robot.{r}.nodes_detector.get_connected_devices"
            )
            rr = cl.call({})
            for d in rr['devices']:
                if d['type'] == 'PAN_TILT':
                    # print(d)
                    self.pantilts[d['name']] = {
                        'base_topic': d['base_topic'],
                        'place': d['categorization']['place']
                    }

        # Pan tilts in environment
        cl = CommlibFactory.getRPCClient(
            rpc_name = f"{res['world']}.nodes_detector.get_connected_devices"
        )
        rr = cl.call({})
        for d in rr['devices']:
            if d['type'] == 'PAN_TILT':
                # print(d)
                self.pantilts[d['name']] = {
                    'base_topic': d['base_topic'],
                    'place': d['categorization']['place']
                }
        self.logger.info("Pan tilts detected:")
        for p in self.pantilts:
            self.logger.info(f"\t{p} on {self.pantilts[p]['place']}")

            topic = self.pantilts[p]['base_topic'] + '.data'
            self.subs[p] = CommlibFactory.getSubscriber(
                topic = topic,
                callback = self.pan_tilt_callback
            )

        # Gather robots and create subscribers

        # Old one
        for d in self.declarations:
            if d['host'] not in self.hosts:
                self.hosts.append(d['host'])
                if d['host_type'] == "robot":
                    topic = d['host_type'] + "." + d["host"] + ".pose"
                    self.subs[d['host']] = CommlibFactory.getSubscriber(
                        topic = topic,
                        callback = self.robot_pose_callback
                    )

        self.logger.info("*****************************************")

        # starting subs
        for s in self.subs:
            self.subs[s].run()

    def robot_pose_callback(self, message, meta):
        print(message)

    def pan_tilt_callback(self, message, meta):
        print(message)

    # {
    #     type: robot/env/actor
    #     subtype:
    #     name:
    #     pose:
    #     base_topic:
    #     range:
    #     fov:
    #     host:
    #     host_type
    # }
    def declare_callback(self, message, meta):
        m = message

        # sanity checks
        temp = {}
        for t in self.declare_rpc_input:
            temp[t] = None
        for m in message:
            if m not in temp:
                self.logger.error(f"tf: Invalid declaration field for {message['name']}: {m}")
                return {}
            temp[m] = message[m]

        host_msg = ""
        if 'host' in message:
            host_msg = f"on {message['host']}"

        if 'host_type' in message:
            if message['host_type'] not in ['robot', 'pan_tilt']:
                self.logger.error(f"tf: Invalid host type for {message['name']}: {message['host_type']}")

        self.logger.info(f"{Style.DIM}{temp['name']}::{temp['type']}::{temp['subtype']} @ {temp['pose']} {host_msg}{Style.RESET_ALL}")

        self.declarations.append(temp)
        return {}
