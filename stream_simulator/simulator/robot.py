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

        try:
            self.namespace = os.environ['TEKTRAIN_NAMESPACE']
        except:
            self.logger.error("No TEKTRAIN_NAMESPACE environmental variable found. Please set it!")
            exit(0)

        self.name = self.namespace + "/" + name
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
        id_length = 4
        for s in self.world["robots"][0]["devices"]:
            if s == "microphone":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = 'id_' + ''.join(random.choices(
                        string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "MICROPHONE",
                        "brand": "usb_mic",
                        "base_topic": self.name + "/sensor/audio/microphone/d" + str(cnt) + "/" + id,
                        "name": "microphone_" + str(cnt),
                        "place": m[1],
                        "id": id,
                        "enabled": True,
                        "orientation": m[0]
                    }
                    self.devices.append(msg)
            elif s == "sonar":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = 'id_' + ''.join(random.choices(
                        string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "SONAR",
                        "brand": "sonar",
                        "base_topic": self.name + "/sensor/distance/sonar/d" + str(cnt) + "/" + id,
                        "name": "sonar_" + str(cnt),
                        "place": m[1],
                        "id": id,
                        "enabled": True,
                        "orientation": m[0]
                    }
                    self.devices.append(msg)
            elif s == "ir":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = 'id_' + ''.join(random.choices(
                        string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "IR",
                        "brand": "ir",
                        "base_topic": self.name + "/sensor/distance/ir/d" + str(cnt) + "/" + id,
                        "name": "ir_" + str(cnt),
                        "place": m[1],
                        "id": id,
                        "enabled": True,
                        "orientation": m[0]
                    }
                    self.devices.append(msg)
            elif s == "tof":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = 'id_' + ''.join(random.choices(
                        string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "TOF",
                        "brand": "vl53l1x",
                        "base_topic": self.name + "/sensor/distance/tof/d" + str(cnt) + "/" + id,
                        "name": "tof_" + str(cnt),
                        "place": m[1],
                        "id": id,
                        "enabled": True,
                        "orientation": m[0]
                    }
                    self.devices.append(msg)
            elif s == "camera":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = 'id_' + ''.join(random.choices(
                        string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "CAMERA",
                        "brand": "picamera",
                        "base_topic": self.name + "/sensor/visual/camera/d" + str(cnt) + "/" + id,
                        "name": "camera_" + str(cnt),
                        "place": m[1],
                        "id": id,
                        "enabled": True,
                        "orientation": m[0]
                    }
                    self.devices.append(msg)
            elif s == "imu":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = 'id_' + ''.join(random.choices(
                        string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "IMU",
                        "brand": "icm_20948",
                        "base_topic": self.name + "/sensor/imu/accel_gyro_magne_temp/d" + str(cnt) + "/" + id,
                        "name": "imu_" + str(cnt),
                        "place": m[1],
                        "id": id,
                        "enabled": True,
                        "orientation": m[0]
                    }
                    self.devices.append(msg)
            elif s == "button":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = 'id_' + ''.join(random.choices(
                        string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "BUTTON",
                        "brand": "simple",
                        "base_topic": self.name + "/sensor/button/tactile_switch/d" + str(cnt) + "/" + id,
                        "name": "button_" + str(cnt),
                        "place": m[1],
                        "id": id,
                        "enabled": True,
                        "orientation": m[0]
                    }
                    self.devices.append(msg)
            elif s == "env":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = 'id_' + ''.join(random.choices(
                        string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "ENV",
                        "brand": "bme680",
                        "base_topic": self.name + "/sensor/env/temp_hum_pressure_gas/d" + str(cnt) + "/" + id,
                        "name": "env_" + str(cnt),
                        "place": m[1],
                        "id": id,
                        "enabled": True,
                        "orientation": m[0]
                    }
                    self.devices.append(msg)
            elif s == "speaker":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = 'id_' + ''.join(random.choices(
                        string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "SPEAKERS",
                        "brand": "usb_speaker",
                        "base_topic": self.name + "/actuator/audio/speaker/usb_speaker/d" + str(cnt) + "/" + id,
                        "name": "speaker_" + str(cnt),
                        "place": m[1],
                        "id": id,
                        "enabled": True,
                        "orientation": m[0]
                    }
                    self.devices.append(msg)
            elif s == "leds":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = 'id_' + ''.join(random.choices(
                        string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "LED",
                        "brand": "neopx",
                        "base_topic": self.name + "/actuator/visual/leds/neopx/d" + str(cnt) + "/" + id,
                        "name": "led_" + str(cnt),
                        "place": m[1],
                        "id": id,
                        "enabled": True,
                        "orientation": m[0]
                    }
                    self.devices.append(msg)
            elif s == "pan_tilt":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = 'id_' + ''.join(random.choices(
                        string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "PAN_TILT",
                        "brand": "pca9685",
                        "base_topic": self.name + "/actuator/servo/pantilt/d" + str(cnt) + "/" + id,
                        "name": "pan_tilt_" + str(cnt),
                        "place": m[1],
                        "id": id,
                        "enabled": True,
                        "orientation": m[0]
                    }
                    self.devices.append(msg)
            elif s == "touch_screen":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = 'id_' + ''.join(random.choices(
                        string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "TOUCH_SCREEN",
                        "brand": "touch_screen",
                        "base_topic": self.name + "/actuator/visual/screen/touch_screen/d" + str(cnt) + "/" + id,
                        "name": "touch_screen_" + str(cnt),
                        "place": m[1],
                        "id": id,
                        "enabled": True,
                        "orientation": m[0]
                    }
                    self.devices.append(msg)
            elif s == "skid_steer":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = 'id_' + ''.join(random.choices(
                        string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "SKID_STEER",
                        "brand": "twist",
                        "base_topic": self.name + "/actuator/motion/base/twist/d" + str(cnt) + "/" + id,
                        "name": "skid_steer_" + str(cnt),
                        "place": m[1],
                        "id": id,
                        "enabled": True,
                        "orientation": m[0]
                    }
                    self.devices.append(msg)
            elif s == "encoder":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = 'id_' + ''.join(random.choices(
                        string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "ENCODER",
                        "brand": "simple",
                        "base_topic": self.name + "/sensor/encoder/d" + str(cnt) + "/" + id,
                        "name": "encoder_" + str(cnt),
                        "place": m[1],
                        "id": id,
                        "enabled": True,
                        "orientation": m[0]
                    }
                    self.devices.append(msg)
            else:
                self.logger.critical("Device declared in yaml does not exist: {}".format(s))

        self.controllers = {}

        # Devices management
        for d in self.devices:
            if d["type"] == "PAN_TILT":
                self.controllers[d["id"]] = PanTiltController(info = d, logger = self.logger)
            elif d["type"] == "LED":
                self.controllers[d["id"]] = LedsController(info = d, logger = self.logger)
            elif d["type"] == "ENV":
                self.controllers[d["id"]] = EnvController(info = d, logger = self.logger)
            elif d["type"] == "IMU":
                self.controllers[d["id"]] = ImuController(info = d, logger = self.logger)
            elif d["type"] == "SONAR":
                self.controllers[d["id"]] = SonarController(info = d, logger = self.logger)
            elif d["type"] == "IR":
                self.controllers[d["id"]] = IrController(info = d, logger = self.logger)
            elif d["type"] == "SKID_STEER":
                self.controllers[d["id"]] = MotionController(info = d, logger = self.logger)
                # Just keep the motion controller in another var for the simulator:
                self.motion_controller = self.controllers[d["id"]]
            elif d["type"] == "TOF":
                self.controllers[d["id"]] = TofController(info = d, logger = self.logger)
            elif d["type"] == "BUTTON":
                self.controllers[d["id"]] = ButtonController(info = d, logger = self.logger)
            elif d["type"] == "ENCODER":
                self.controllers[d["id"]] = EncoderController(info = d, logger = self.logger)
            elif d["type"] == "CAMERA":
                self.controllers[d["id"]] = CameraController(info = d, logger = self.logger)
            else:
                self.logger.critical("Controller declared in yaml does not exist: {}".format(d["name"]))

        self.devices_rpc_server = RPCServer(conn_params=ConnParams.get(), on_request=self.devices_callback, rpc_name=self.namespace + '/nodes_detector/get_connected_devices')

        # SIMULATOR ------------------------------------------------------------
        self.pose_pub = Publisher(conn_params=ConnParams.get(), topic= name + ":pose")

        # Threads
        self.motion_thread = threading.Thread(target = self.handle_motion)

        self.logger.info("Robot {} set-up".format(self.name))

    def start(self):
        for c in self.controllers:
            self.controllers[c].start()

        self.devices_rpc_server.run()

        # Simulator stuff
        self.motion_thread.start()
        self.logger.info("Robot {}: cmd_vel threading ok".format(self.name))

    def devices_callback(self, message, meta):
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
