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

    def handle_motion(self):
        while True:
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

            self.logger.debug("Robot pose: {}, {}, {}".format(\
                "{:.2f}".format(self._x), \
                "{:.2f}".format(self._y), \
                "{:.2f}".format(self._theta)))

            self.pose_pub.publish({
                "x": self._x,
                "y": self._y,
                "theta": self._theta
            })

            # Check if on obstacle
            print(self._x / self.resolution, self._y / self.resolution)
            if self.map[int(self._x / self.resolution), int(self._y / self.resolution)] == 1:
                print("CRASH")

            time.sleep(self.dt)
