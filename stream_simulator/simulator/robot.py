#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random
import string
import os

from stream_simulator import ConnParams
if ConnParams.type == "amqp":
    from commlib_py.transports.amqp import Publisher, RPCServer
elif ConnParams.type == "redis":
    from commlib_py.transports.redis import Publisher, RPCServer

from commlib_py.logger import Logger
from .device_lookup import DeviceLookup

class Robot:
    def __init__(self, world = None, map = None, name = "robot", tick = 0.1):
        self.logger = Logger(name)
        self.logger.std_logger.setLevel(logging.INFO)

        try:
            self.namespace = os.environ['TEKTRAIN_NAMESPACE']
        except:
            self.logger.warning("No TEKTRAIN_NAMESPACE environmental variable found. Automatically setting it to /robot")
            os.environ["TEKTRAIN_NAMESPACE"] = "/robot"
            self.namespace = "/robot"


        self.name = self.namespace + "/" + name
        self.dt = tick

        self._x = 0
        self._y = 0
        self._theta = 0

        self.detection_threshold = 1

        # Yaml configuration management
        self.world = world
        self.map = map
        self.width = self.map.shape[0]
        self.height = self.map.shape[1]
        self.resolution = self.world["map"]["resolution"]
        self.logger.info("Robot {}: map set".format(self.name))

        pose = self.world['robots'][0]['starting_pose']
        self._x = pose['x'] * self.resolution
        self._y = pose['y'] * self.resolution
        self._theta = pose['theta'] / 180.0 * math.pi
        self.logger.info("Robot {} pose set: {}, {}, {}".format(
            self.name, self._x, self._y, self._theta))

        # Devices set
        self.device_management = DeviceLookup(
            world = self.world, map = self.map, name = self.name,\
            namespace = self.namespace, device_name = name)
        tmp = self.device_management.get()
        self.devices = tmp['devices']
        self.controllers = tmp['controllers']
        try:
            self.motion_controller = self.device_management.motion_controller
        except:
            self.logger.warning("Robot has no motion controller.. Smells like device!".format(self.name))
            self.motion_controller = None

        self.devices_rpc_server = RPCServer(conn_params=ConnParams.get(), on_request=self.devices_callback, rpc_name=self.namespace + '/nodes_detector/get_connected_devices')

        self.internal_pose_pub = Publisher(conn_params=ConnParams.get(), topic= name + "/pose")

        # SIMULATOR ------------------------------------------------------------
        if self.world['robots'][0]['amqp_inform'] is True:
            import commlib_py
            conn_params = commlib_py.transports.amqp.ConnectionParameters()
            conn_params.credentials.username = 'bot'
            conn_params.credentials.password = 'b0t'
            conn_params.host = 'tektrain-cloud.ddns.net'
            conn_params.port = 5672
            conn_params.vhost = "sim"

            final_top = self.name.replace("/", ".")[1:]
            final_top = final_top[final_top.find(".") + 1:] + ".pose"
            final_dete_top = final_top[final_top.find(".") + 1:] + ".detect"
            self.pose_pub = commlib_py.transports.amqp.Publisher(conn_params=conn_params, topic= final_top)

            self.detects_pub = commlib_py.transports.amqp.Publisher(conn_params=conn_params, topic= final_dete_top)

        # Threads
        self.simulator_thread = threading.Thread(target = self.simulation_thread)

        from derp_me.client import DerpMeClient
        self.derp_client = DerpMeClient(conn_params=ConnParams.get())

        self.logger.info("Device {} set-up".format(self.name))

    def start(self):
        for c in self.controllers:
            self.controllers[c].start()

        self.devices_rpc_server.run()
        self.stopped = False
        self.simulator_thread.start()

        r = self.derp_client.lset(
            "stream_sim/state",
            [{
                "state": "ACTIVE",
                "timestamp": time.time()
            }])

    def stop(self):
        for c in self.controllers:
            self.logger.warning("Trying to stop controller {}".format(c))
            self.controllers[c].stop()

        self.logger.warning("Trying to stop devices_rpc_server")
        self.devices_rpc_server.stop()
        self.logger.warning("Trying to stop simulation_thread")
        self.stopped = True

    def devices_callback(self, message, meta):
        self.logger.warning("Getting devices")
        timestamp = time.time()
        secs = int(timestamp)
        nanosecs = int((timestamp-secs) * 10**(9))
        return {"devices": self.devices, "header":{
                "stamp":{
                    "sec": secs,
                    "nanosec": nanosecs
                }
            }
        }

    def initialize_resources(self):
        pass

    def check_ok(self, x, y, prev_x, prev_y):
        # Check out of bounds
        if x < 0 or y < 0:
            self.logger.error("{}: Out of bounds - negative x or y".format(self.name))
            return True
        if x / self.resolution > self.width or y / self.resolution > self.height:
            self.logger.error("{}: Out of bounds".format(self.name))
            return True

        # Check collision to obstacles
        x_i = int(x / self.resolution)
        x_i_p = int(prev_x / self.resolution)
        if x_i > x_i_p:
            x_i, x_i_p = x_i_p, x_i

        y_i = int(y / self.resolution)
        y_i_p = int(prev_y / self.resolution)
        if y_i > y_i_p:
            y_i, y_i_p = y_i_p, y_i

        if x_i == x_i_p:
            for i in range(y_i, y_i_p):
                if self.map[x_i, i] == 1:
                    self.logger.error("{}: Crash #1".format(self.name))
                    return True
        elif y_i == y_i_p:
            for i in range(x_i, x_i_p):
                if self.map[i, y_i] == 1:
                    self.logger.error("{}: Crash #2".format(self.name))
                    return True
        else: # we have a straight line
            th = math.atan2(y_i_p - y_i, x_i_p - x_i)
            dist = math.hypot(x_i_p - x_i, y_i_p - y_i)
            d = 0
            while d < dist:
                xx = x_i + d * math.cos(th)
                yy = y_i + d * math.sin(th)
                if self.map[int(xx), int(yy)] == 1:
                    self.logger.error("{}: Crash #3".format(self.name))
                    return True
                d += 1.0

        return False

    def simulation_thread(self):
        while self.stopped is False:
            if self.motion_controller is not None:
                prev_x = self._x
                prev_y = self._y
                prev_th = self._theta

                if self.motion_controller._angular == 0:
                    self._x += self.motion_controller._linear * self.dt * math.cos(self._theta)
                    self._y += self.motion_controller._linear * self.dt * math.sin(self._theta)
                else:
                    arc = self.motion_controller._linear / self.motion_controller._angular
                    self._x += - arc * math.sin(self._theta) + \
                        arc * math.sin(self._theta + self.dt * self.motion_controller._angular)
                    self._y -= - arc * math.cos(self._theta) + \
                        arc * math.cos(self._theta + self.dt * self.motion_controller._angular)
                self._theta += self.motion_controller._angular * self.dt

                if self.check_ok(self._x, self._y, prev_x, prev_y):
                    self._x = prev_x
                    self._y = prev_y
                    self._theta = prev_th

                if self.world['robots'][0]['amqp_inform'] is True:
                    self.pose_pub.publish({
                        "x": float("{:.2f}".format(self._x)),
                        "y": float("{:.2f}".format(self._y)),
                        "theta": float("{:.2f}".format(self._theta)),
                        "resolution": self.resolution
                    })

                self.internal_pose_pub.publish({
                    "x": float("{:.2f}".format(self._x)),
                    "y": float("{:.2f}".format(self._y)),
                    "theta": float("{:.2f}".format(self._theta)),
                    "resolution": self.resolution
                })

            self.check_detections()

            time.sleep(self.dt)

    def check_detections(self):
        # [text, human, sound, qr, barcode, language, motion, color]
        detections = {
            'type': None,
            'id': None,
            'value': None
        }

        if self.world['robots'][0]['amqp_inform'] is True:
            try:
                v = self.derp_client.lget("robot.detect", 0, 0)['val'][0]
                if time.time() - v['timestamp'] < self.dt:
                    self.logger.warning("Sending to amqp notifier: " + str(v))
                    self.detects_pub.publish(v)
            except:
                print("AMQP notification failed")
                pass

        # Check distance from stuff
        for h in self.world["actors"]["humans"]:
            x = h["x"] * self.resolution
            y = h["y"] * self.resolution
            if math.hypot(x - self._x, y - self._y) < self.detection_threshold:
                self.detection_pub.publish({
                    'type': 'human',
                    'id': h['id'],
                    'value': -1
                })
                self.logger.info("Detected {} {}".format('human', h['id']))

                if h['move'] == 1:
                    self.detection_pub.publish({
                        'type': 'motion',
                        'id': h['id'],
                        'value': -1
                    })
                    self.logger.info("Detected {} {}".format('motion', h['id']))
                if h['sound'] == 1:
                    self.detection_pub.publish({
                        'type': 'sound',
                        'id': h['id'],
                        'value': -1
                    })
                    self.logger.info("Detected {} {}".format('sound', h['id']))
                if h['lang'] != 0:
                    self.detection_pub.publish({
                        'type': 'language',
                        'id': h['id'],
                        'value': h['lang']
                    })
                    self.logger.info("Detected {} {}".format('language', h['id']))

        for h in self.world["actors"]["sound_sources"]:
            x = h["x"] * self.resolution
            y = h["y"] * self.resolution
            if math.hypot(x - self._x, y - self._y) < self.detection_threshold:
                self.detection_pub.publish({
                    'type': 'sound',
                    'id': h['id'],
                    'value': -1
                })
                self.logger.info("Detected {} {}".format('sound', h['id']))

        for h in self.world["actors"]["qrs"]:
            x = h["x"] * self.resolution
            y = h["y"] * self.resolution
            if math.hypot(x - self._x, y - self._y) < self.detection_threshold:
                self.detection_pub.publish({
                    'type': 'qr',
                    'id': h['id'],
                    'value': h['message']
                })
                self.logger.info("Detected {} {}".format('qr', h['id']))

        for h in self.world["actors"]["barcodes"]:
            x = h["x"] * self.resolution
            y = h["y"] * self.resolution
            if math.hypot(x - self._x, y - self._y) < self.detection_threshold:
                self.detection_pub.publish({
                    'type': 'barcode',
                    'id': h['id'],
                    'value': h['message']
                })
                self.logger.info("Detected {} {}".format('barcode', h['id']))

        for h in self.world["actors"]["colors"]:
            x = h["x"] * self.resolution
            y = h["y"] * self.resolution
            if math.hypot(x - self._x, y - self._y) < self.detection_threshold:
                self.detection_pub.publish({
                    'type': 'color',
                    'id': h['id'],
                    'value': {
                        'r': h['r'],
                        'g': h['g'],
                        'b': h['b']
                    }
                })
                self.logger.info("Detected {} {}".format('color', h['id']))

        for h in self.world["actors"]["texts"]:
            x = h["x"] * self.resolution
            y = h["y"] * self.resolution
            if math.hypot(x - self._x, y - self._y) < self.detection_threshold:
                self.detection_pub.publish({
                    'type': 'text',
                    'id': h['id'],
                    'value': h['text']
                })
                self.logger.info("Detected {} {}".format('text', h['id']))
