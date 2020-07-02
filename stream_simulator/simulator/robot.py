#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random

from stream_simulator import Publisher
from stream_simulator import Subscriber

from stream_simulator import RpcServer

from stream_simulator import Logger

class Robot:
    def __init__(self, name = "robot", tick = 0.1, debug_level = logging.INFO):
        self.logger = Logger("name", debug_level)

        self.name = name
        self.dt = tick

        self._x = 0
        self._y = 0
        self._theta = 0

        self._linear = 0
        self._angular = 0

        self._color = [0, 0, 0, 0]
        self._wipe_color = [0, 0, 0, 0]

        # Subscribers
        self.vel_sub = Subscriber(topic = name + ":cmd_vel", func = self.cmd_vel)
        self.leds_set_sub = Subscriber(topic = name + ":leds", func = self.leds_set_callback)

        # Publishers
        self.pose_pub = Publisher(topic = name + ":pose")
        self.leds_wipe_pub = Publisher(topic = name + ":leds_wipe")

        # RPC servers
        self.env_rpc_server = RpcServer(topic = name + ":env", func = self.env_callback)
        self.leds_wipe_server = RpcServer(topic = name + ":leds_wipe", func = self.leds_wipe_callback)

        # Threads
        self.motion_thread = threading.Thread(target = self.handle_motion)

        self.logger.info("Robot {} set-up".format(self.name))

    def start(self):
        self.vel_sub.start()
        self.logger.info("Robot {}: vel_sub started".format(self.name))
        self.leds_set_sub.start()
        self.logger.info("Robot {}: leds_set_sub started".format(self.name))

        self.env_rpc_server.start()
        self.logger.info("Robot {}: env_rpc_server started".format(self.name))
        self.leds_wipe_server.start()
        self.logger.info("Robot {}: leds_wipe_server started".format(self.name))

        self.motion_thread.start()
        self.logger.info("Robot {}: cmd_vel threading ok".format(self.name))

    def env_callback(self, message):
        self.logger.info("Robot {}: Env callback: {}".format(self.name, message))
        try:
            _to = message["from"] + 1
            _from = message["to"]
        except Exception as e:
            self.logger.error("{}: Malformed message for env: {} - {}".format(self.name, str(e.__class__), str(e)))
            return []
        ret = []
        for i in range(_from, _to): # 0 to -1
            timestamp = time.time()
            secs = int(timestamp)
            nanosecs = int((timestamp-secs) * 10**(9))
            ret.append({
                "header":{
                    "stamp":{
                        "sec": secs,
                        "nanosec": nanosecs
                    }
                },
                "temperature": float(random.uniform(30, 10)),
                "pressure": float(random.uniform(30, 10)),
                "humidity": float(random.uniform(30, 10)),
                "gas": float(random.uniform(30, 10))
            })
        return ret

    def set_pose(self, x, y, theta):
        self._x = x
        self._y = y
        self._theta = theta
        self.logger.info("Robot {} pose set: {}, {}, {}".format(self.name, x, y, theta))

    def set_map(self, map, resolution):
        self.map = map
        self.width = self.map.shape[0]
        self.height = self.map.shape[1]
        self.resolution = resolution
        self.logger.info("Robot {}: map set".format(self.name))

    def leds_set_callback(self, message):
        try:
            response = json.loads(message['data'])
            id = response["id"]
            r = response["r"]
            g = response["g"]
            b = response["b"]
            intensity = response["intensity"]
            self._color = [r, g, b, intensity]
            self.logger.info("{}: New set leds command: {}".format(self.name, message))
        except Exception as e:
            self.logger.error("{}: leds_set is wrongly formatted: {} - {}".format(self.name, str(e.__class__), str(e)))

    def leds_wipe_callback(self, message):
        try:
            response = message
            r = response["r"]
            g = response["g"]
            b = response["b"]
            intensity = response["brightness"]
            ms = response["wait_ms"]
            self._color = [r, g, b, intensity]
            self.logger.info("{}: New leds wipe command: {}".format(self.name, message))

            self.leds_wipe_pub.publish({"r": r, "g": g, "b": b})
        except Exception as e:
            self.logger.error("{}: leds_wipe is wrongly formatted: {} - {}".format(self.name, str(e.__class__), str(e)))

        return {}

    def cmd_vel(self, message):
        try:
            response = json.loads(message['data'])
            self._linear = response['linear']
            self._angular = response['angular']
            self.logger.info("{}: New motion command: {}, {}".format(self.name, self._linear, self._angular))
        except Exception as e:
            self.logger.error("{}: cmd_vel is wrongly formatted: {} - {}".format(self.name, str(e.__class__), str(e)))

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

    def handle_motion(self):
        while True:
            prev_x = self._x
            prev_y = self._y
            prev_th = self._theta

            if self._angular == 0:
                self._x += self._linear * self.dt * math.cos(self._theta)
                self._y += self._linear * self.dt * math.sin(self._theta)
            else:
                arc = self._linear / self._angular
                self._x += - arc * math.sin(self._theta) + \
                    arc * math.sin(self._theta + self.dt * self._angular)
                self._y -= - arc * math.cos(self._theta) + \
                    arc * math.cos(self._theta + self.dt * self._angular)
            self._theta += self._angular * self.dt

            if self.check_ok(self._x, self._y, prev_x, prev_y):
                self._x = prev_x
                self._y = prev_y
                self._theta = prev_th

            self.logger.debug("Robot pose: {}, {}, {}".format(\
                "{:.2f}".format(self._x), \
                "{:.2f}".format(self._y), \
                "{:.2f}".format(self._theta)))

            self.pose_pub.publish({
                "x": float("{:.2f}".format(self._x)),
                "y": float("{:.2f}".format(self._y)),
                "theta": float("{:.2f}".format(self._theta))
            })

            time.sleep(self.dt)
