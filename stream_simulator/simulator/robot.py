#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading

from stream_simulator import Publisher
from stream_simulator import Subscriber

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

        # Subscribers
        self.vel_sub = Subscriber(topic = name + ":cmd_vel", func = self.cmd_vel)

        # Publishers
        self.pose_pub = Publisher(topic = name + ":pose")

        # Threads
        self.motion_thread = threading.Thread(target = self.handle_motion)

        self.logger.info("Robot {} set-up".format(self.name))

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

    def start(self):
        self.vel_sub.start()
        self.logger.info("Robot {}: cmd_vel subscription started".format(self.name))
        self.motion_thread.start()
        self.logger.info("Robot {}: cmd_vel threading ok".format(self.name))

    def cmd_vel(self, message):
        try:
            response = json.loads(message['data'])
            self._linear = response['linear']
            self._angular = response['angular']
            self.logger.info("{}: New motion command: {}, {}".format(self.name, self._linear, self._angular))
        except Exception as e:
            self.logger.error("{}: cmd_vel is wrongly formatted: {} - {}".format(self.name, str(e.__class__), str(e)))

    def check_ok(self, x, y, prev_x, prev_y):
        if x < 0 or y < 0:
            self.logger.error("{}: Out of bounds - negative x or y".format(self.name))
            return True
        if x / self.resolution > self.width or y / self.resolution > self.height:
            self.logger.error("{}: Out of bounds".format(self.name))
            return True
        if self.map[int(x / self.resolution), int(y / self.resolution)] == 1:
            self.logger.error("{}: Crash".format(self.name))
            return True

        return False

    def handle_motion(self):
        while True:
            prev_x = self._x
            prev_y = self._y

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
