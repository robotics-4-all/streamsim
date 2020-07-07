#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random
import string

from stream_simulator import ConnParams
if ConnParams.type == "amqp":
    from commlib_py.transports.amqp import Publisher
elif ConnParams.type == "redis":
    from commlib_py.transports.redis import Publisher

from stream_simulator import Logger

from .controller_pan_tilt import PanTiltController
from .controller_leds import LedsController
from .controller_env import EnvController
from .controller_imu import ImuController
from .controller_motion import MotionController
from .controller_sonar import SonarController
from .controller_ir import IrController
from .controller_tof import TofController
from .controller_button import ButtonController
from .controller_encoder import EncoderController
from .controller_camera import CameraController

class Robot:
    def __init__(self, world = None, map = None, name = "robot", tick = 0.1, debug_level = logging.INFO):
        self.logger = Logger("name", debug_level)

        self.name = name
        self.dt = tick

        self._x = 0
        self._y = 0
        self._theta = 0

        self.detection_threshold = 1.0

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

        self.devices = []
        id_length = 20
        for s in self.world["robots"][0]["sensors"]:
            if s == "microphone":
                sensors = self.world["robots"][0]["sensors"][s]
                cnt = -1
                for m in sensors:
                    cnt += 1
                    id = 'id_' + ''.join(random.choices(
                        string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "MICROPHONE",
                        "brand": "usb_mic",
                        "base_topic": self.name + "/sensor/audio/microphone/" + str(cnt) + "/" + id,
                        "name": "microphone_" + str(cnt),
                        "place": m[1],
                        "id": id,
                        "enabled": True,
                        "orientation": m[0]
                    }
                    self.devices.append(msg)
            if s == "sonar":
                sensors = self.world["robots"][0]["sensors"][s]
                cnt = -1
                for m in sensors:
                    cnt += 1
                    id = 'id_' + ''.join(random.choices(
                        string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "SONAR",
                        "brand": "sonar",
                        "base_topic": self.name + "/sensor/distance/sonar/" + str(cnt) + "/" + id,
                        "name": "sonar_" + str(cnt),
                        "place": m[1],
                        "id": id,
                        "enabled": True,
                        "orientation": m[0]
                    }
                    self.devices.append(msg)
            if s == "tof":
                pass
            if s == "camera":
                pass
            if s == "imu":
                pass
            if s == "button":
                pass
            if s == "env":
                pass

        print(self.devices)

        # Devices management
        self.pan_tilt_controller = PanTiltController(name = self.name, logger = self.logger)
        self.leds_controller = LedsController(name = self.name, logger = self.logger)
        self.env_controller = EnvController(name = self.name, logger = self.logger)
        self.imu_controller = ImuController(name = self.name, logger = self.logger)
        self.sonar_controller = SonarController(name = self.name, logger = self.logger)
        self.ir_controller = IrController(name = self.name, logger = self.logger)
        self.motion_controller = MotionController(name = self.name, logger = self.logger)
        self.tof_controller = TofController(name = self.name, logger = self.logger)
        self.button_controller = ButtonController(name = self.name, logger = self.logger)
        self.encoder_controller = EncoderController(name = self.name, logger = self.logger)
        self.camera_controller = CameraController(name = self.name, logger = self.logger)

        # SIMULATOR ------------------------------------------------------------
        self.pose_pub = Publisher(conn_params=ConnParams.get(), topic= name + ":pose")

        # Threads
        self.motion_thread = threading.Thread(target = self.handle_motion)

        self.logger.info("Robot {} set-up".format(self.name))

    def start(self):
        self.env_controller.start()
        self.sonar_controller.start()
        self.pan_tilt_controller.start()
        self.leds_controller.start()
        self.imu_controller.start()
        self.motion_controller.start()
        self.ir_controller.start()
        self.tof_controller.start()
        self.button_controller.start()
        self.encoder_controller.start()
        self.camera_controller.start()

        # Simulator stuff
        self.motion_thread.start()
        self.logger.info("Robot {}: cmd_vel threading ok".format(self.name))

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

            # Check distance from stuff
            for h in self.world["actors"]["humans"]:
                x = h["x"] * self.resolution
                y = h["y"] * self.resolution
                if math.hypot(x - self._x, y - self._y) < self.detection_threshold:
                    print("Human!")
            for h in self.world["actors"]["sound_sources"]:
                x = h["x"] * self.resolution
                y = h["y"] * self.resolution
                if math.hypot(x - self._x, y - self._y) < self.detection_threshold:
                    print("Sound source!")
            for h in self.world["actors"]["qrs"]:
                x = h["x"] * self.resolution
                y = h["y"] * self.resolution
                if math.hypot(x - self._x, y - self._y) < self.detection_threshold:
                    print("QR!")
            for h in self.world["actors"]["barcodes"]:
                x = h["x"] * self.resolution
                y = h["y"] * self.resolution
                if math.hypot(x - self._x, y - self._y) < self.detection_threshold:
                    print("Barcode!")
            for h in self.world["actors"]["colors"]:
                x = h["x"] * self.resolution
                y = h["y"] * self.resolution
                if math.hypot(x - self._x, y - self._y) < self.detection_threshold:
                    print("Color!")
            for h in self.world["actors"]["texts"]:
                x = h["x"] * self.resolution
                y = h["y"] * self.resolution
                if math.hypot(x - self._x, y - self._y) < self.detection_threshold:
                    print("Text!")

            time.sleep(self.dt)
