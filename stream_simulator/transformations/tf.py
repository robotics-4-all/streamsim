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
    def __init__(self, base = None, resolution = None, logger = None):
        self.logger = Logger("tf") if logger is None else logger
        self.base_topic = base + ".tf" if base is not None else "streamsim.tf"
        self.base = base
        self.resolution = resolution

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

        self.get_tf_rpc_server = CommlibFactory.getRPCService(
            callback = self.get_tf_callback,
            rpc_name = self.base_topic + ".get_tf"
        )
        self.get_tf_rpc_server.run()

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

    def get_tf_callback(self, message, meta):
        name = message['name']
        if name not in self.items_hosts_dict:
            self.logger.error(f"TF: Requested transformation of missing device: {name}")
            return {}

        if name in self.robots:
            return self.places_absolute[name]
        elif name in self.pantilts:
            pose = self.places_absolute[name]
            base_th = 0
            if self.items_hosts_dict[name] != None:
                base_th = self.places_absolute[self.items_hosts_dict[name]]['theta']
            pose['theta'] = self.places_relative[name]['theta'] + \
                self.pantilts[name]['pan'] + base_th
            return pose
        else:
            return self.places_absolute[name]

    def setup(self):
        self.logger.info("*************** TF status ***************")
        self.subs = {} # Filled
        self.places_relative = {}
        self.places_absolute = {}
        self.tree = {} # filled
        self.items_hosts_dict = {}
        self.existing_hosts = []
        self.pantilts = {}
        self.robots = []

        # Fill tree
        for d in self.declarations:
            if d['host'] not in self.tree:
                self.tree[d['host']] = []

            self.tree[d['host']].append(d['name'])
            self.items_hosts_dict[d['name']] = d['host']

            self.places_relative[d['name']] = d['pose'].copy()
            self.places_absolute[d['name']] = d['pose'].copy()
            if 'x' in d['pose']: # The only culprit is linear alarm
                for i in ['x', 'y']:
                    self.places_relative[d['name']][i] *= self.resolution
                    self.places_absolute[d['name']][i] *= self.resolution

        # Get all devices and check pan-tilts exist
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
                    self.pantilts[d['name']] = {
                        'base_topic': d['base_topic'],
                        'place': d['categorization']['place'],
                        'pan': 0.0
                    }

        # Pan tilts in environment
        cl = CommlibFactory.getRPCClient(
            rpc_name = f"{res['world']}.nodes_detector.get_connected_devices"
        )
        rr = cl.call({})
        for d in rr['devices']:
            if d['type'] == 'PAN_TILT':
                self.pantilts[d['name']] = {
                    'base_topic': d['base_topic'],
                    'place': d['categorization']['place'],
                    'pan': 0.0
                }

        self.logger.info("Pan tilts detected:")
        for p in self.pantilts:
            self.logger.info(f"\t{p} on {self.pantilts[p]['place']}")

            self.existing_hosts.append(p)

            topic = self.pantilts[p]['base_topic'] + '.data'
            self.subs[p] = CommlibFactory.getSubscriber(
                topic = topic,
                callback = self.pan_tilt_callback
            )

        # Gather robots and create subscribers
        for d in self.declarations:
            if d['host_type'] == "robot":
                if d['host'] not in self.existing_hosts:
                    self.robots.append(d['host'])
                    self.existing_hosts.append(d['host'])

                    topic = d['host_type'] + "." + d["host"] + ".pose"
                    self.subs[d['host']] = CommlibFactory.getSubscriber(
                        topic = topic,
                        callback = self.robot_pose_callback
                    )

        # Check pan tilt poses for None
        for pt in self.pantilts:
            for k in ['x', 'y', 'theta']:
                if self.places_relative[pt][k] == None:
                    self.logger.error(f"Pan-tilt {pt} has {k} = None. Please fix it in yaml.")

        self.logger.info("Hosts detected:")
        for h in self.tree:
            if h not in self.existing_hosts and h != None:
                self.logger.error(f"We have a missing host: {h}")
                self.logger.error(f"\tAffected devices: {self.tree[h]}")
            self.logger.info(f"\t{h}: {self.tree[h]}")

        self.logger.info("")
        self.logger.info("Setting initial pan-tilt devices poses:")
        # update poses based on tree for pan-tilts
        for d in self.pantilts:
            if d in self.tree:  # We can have a pan-tilt with no devices on it
                for i in self.tree[d]:
                    # initial pan is considered 0
                    pt_abs_pose = self.places_absolute[d]
                    self.places_absolute[i]['x'] += pt_abs_pose['x']
                    self.places_absolute[i]['y'] += pt_abs_pose['y']
                    if self.places_absolute[i]['theta'] != None:
                        self.places_absolute[i]['theta'] += pt_abs_pose['theta']

                    self.logger.info(f"{i}@{d}:")
                    self.logger.info(f"\tPan-tilt: {self.places_absolute[d]}")
                    self.logger.info(f"\tRelative: {self.places_relative[i]}")
                    self.logger.info(f"\tAbsolute: {self.places_absolute[i]}")

        self.logger.info("*****************************************")

        # starting subs
        for s in self.subs:
            self.subs[s].run()

    def robot_pose_callback(self, message, meta):
        nm = message['name'].split(".")[-1]
        # self.logger.info(f"Updating {nm}: {message}")
        if nm not in self.places_absolute:
            self.places_absolute[nm] = {'x': 0, 'y': 0, 'theta': 0}
        self.places_absolute[nm]['x'] = message['x']
        self.places_absolute[nm]['y'] = message['y']
        self.places_absolute[nm]['theta'] = message['theta']

        # Update all thetas of devices
        for d in self.tree[nm]:
            if self.places_absolute[d]['theta'] != None and d not in self.pantilts:
                self.places_absolute[d]['theta'] = \
                    self.places_absolute[nm]['theta'] + \
                    self.places_relative[d]['theta']
                # self.logger.info(f"Updated {d}: {self.places_absolute[d]['theta']}")

            self.places_absolute[d]['x'] = self.places_absolute[nm]['x']
            self.places_absolute[d]['y'] = self.places_absolute[nm]['y']

            # Just setting devs on pan tilts the robot's pose
            if d in self.pantilts:
                pt_devs = self.tree[d]
                for dev in pt_devs:
                    self.places_absolute[dev]['x'] = self.places_absolute[nm]['x']
                    self.places_absolute[dev]['y'] = self.places_absolute[nm]['y']
                # Updating the angle of objects on pan-tilt
                # self.logger.info(f"Updating pt {d} on {nm}")
                pan_now = self.pantilts[d]['pan']
                # self.logger.info(f"giving {pan_now}")
                self.update_pan_tilt(d, pan_now)

    def update_pan_tilt(self, pt_name, pan):
        base_th = 0
        # If we are on a robot take its theta
        if self.items_hosts_dict[pt_name] != None:
            base_th = self.places_absolute[self.items_hosts_dict[pt_name]]['theta']

        # self.logger.info(f"Updated {pt_name}: {self.places_absolute[pt_name]} / {pan}")

        abs_pt_theta = self.places_relative[pt_name]['theta'] + pan + base_th
        for i in self.tree[pt_name]:
            if self.places_absolute[i]['theta'] != None:
                self.places_absolute[i]['theta'] = \
                    self.places_relative[i]['theta'] + \
                    abs_pt_theta
                # self.logger.info(f"Updated {i}: {self.places_absolute[i]}")

    def pan_tilt_callback(self, message, meta):
        self.pantilts[message['name']]['pan'] = message['pan']
        self.update_pan_tilt(message['name'], message['pan'])


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

        # Fix thetas if exist:
        if temp['pose']['theta'] != None:
            temp['pose']['theta'] *= math.pi/180.0

        self.declarations.append(temp)
        return {}
