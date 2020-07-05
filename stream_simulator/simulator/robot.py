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

from .controller_pan_tilt import PanTiltController
from .controller_leds import LedsController
from .controller_env import EnvController
from .controller_motion import MotionController

class Robot:
    def __init__(self, name = "robot", tick = 0.1, debug_level = logging.INFO):
        self.logger = Logger("name", debug_level)

        self.name = name
        self.dt = tick

        self._x = 0
        self._y = 0
        self._theta = 0

        # PAN_TILT
        self.pan_tilt_controller = PanTiltController(name = self.name, logger = self.logger)
        self.pan_tilt_set_sub = Subscriber(topic = name + ":pan_tilt", func = self.pan_tilt_controller.pan_tilt_set_callback)
        self.pan_tilt_get_server = RpcServer(topic = name + ":pan_tilt:memory", func = self.pan_tilt_controller.pan_tilt_get_callback)

        # LEDS
        self.leds_controller = LedsController(name = self.name, logger = self.logger)
        self.leds_set_sub = Subscriber(topic = name + ":leds", func = self.leds_controller.leds_set_callback)
        self.leds_wipe_server = RpcServer(topic = name + ":leds_wipe", func = self.leds_controller.leds_wipe_callback)
        self.leds_get_server = RpcServer(topic = name + ":leds:memory", func = self.leds_controller.leds_get_callback)

        # ENV
        self.env_controller = EnvController(name = self.name, logger = self.logger)
        self.env_rpc_server = RpcServer(topic = name + ":env", func = self.env_controller.env_callback)

        # MOTION
        self.motion_controller = MotionController(name = self.name, logger = self.logger)
        self.vel_sub = Subscriber(topic = name + ":cmd_vel", func = self.motion_controller.cmd_vel)
        self.motion_get_server = RpcServer(topic = name + ":motion:memory", func = self.motion_controller.motion_get_callback)

        # SIMULATOR ------------------------------------------------------------
        self.pose_pub = Publisher(topic = name + ":pose")

        # Threads
        self.motion_thread = threading.Thread(target = self.handle_motion)

        self.logger.info("Robot {} set-up".format(self.name))

    def start(self):
        self.vel_sub.start()
        self.logger.info("Robot {}: vel_sub started".format(self.name))
        self.leds_set_sub.start()
        self.logger.info("Robot {}: leds_set_sub started".format(self.name))
        self.pan_tilt_set_sub.start()
        self.logger.info("Robot {}: pan_tilt_set_sub started".format(self.name))

        self.env_rpc_server.start()
        self.logger.info("Robot {}: env_rpc_server started".format(self.name))
        self.leds_wipe_server.start()
        self.logger.info("Robot {}: leds_wipe_server started".format(self.name))
        self.motion_get_server.start()
        self.logger.info("Robot {}: motion_get_server started".format(self.name))
        self.leds_get_server.start()
        self.logger.info("Robot {}: leds_get_server started".format(self.name))
        self.pan_tilt_get_server.start()
        self.logger.info("Robot {}: pan_tilt_get_server started".format(self.name))

        self.motion_thread.start()
        self.logger.info("Robot {}: cmd_vel threading ok".format(self.name))

    def set_map(self, map, resolution):
        self.map = map
        self.width = self.map.shape[0]
        self.height = self.map.shape[1]
        self.resolution = resolution
        self.logger.info("Robot {}: map set".format(self.name))

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

    def set_pose(self, x, y, theta):
        self._x = x
        self._y = y
        self._theta = theta
        self.logger.info("Robot {} pose set: {}, {}, {}".format(self.name, x, y, theta))
