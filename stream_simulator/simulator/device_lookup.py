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

from stream_simulator import Logger

from stream_simulator import ConnParams
if ConnParams.type == "amqp":
    from commlib_py.transports.amqp import RPCServer
elif ConnParams.type == "redis":
    from commlib_py.transports.redis import RPCServer

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
from .controller_microphone import MicrophoneController

class DeviceLookup:
    def __init__(self, world = None, logger = None, name = None):
        self.world = world
        self.logger = logger
        self.name = name
        self.devices = []
        self.controllers = {}

        # Mode: one of {real, mock, simulation}
        self.mode = self.world["robots"][0]["mode"]
        if self.mode not in ["real", "mock", "simulation"]:
            self.logger.error("Selected mode is invalid: {}".format(self.mode))
            exit(1)

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
                        "orientation": m[0],
                        "hz": 0,
                        "queue_size": 0,
                        "mode": self.mode
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
                        "orientation": m[0],
                        "hz": 1,
                        "queue_size": 100,
                        "mode": self.mode
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
                        "orientation": m[0],
                        "hz": 1,
                        "queue_size": 100,
                        "mode": self.mode
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
                        "orientation": m[0],
                        "hz": 1,
                        "queue_size": 100,
                        "mode": self.mode
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
                        "orientation": m[0],
                        "hz": 0,
                        "queue_size": 0,
                        "mode": self.mode
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
                        "orientation": m[0],
                        "hz": 1,
                        "queue_size": 100,
                        "mode": self.mode
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
                        "orientation": m[0],
                        "hz": 1,
                        "queue_size": 100,
                        "mode": self.mode
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
                        "orientation": m[0],
                        "hz": 1,
                        "queue_size": 100,
                        "mode": self.mode
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
                        "orientation": m[0],
                        "hz": 0,
                        "queue_size": 0,
                        "mode": self.mode
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
                        "orientation": m[0],
                        "hz": 0,
                        "queue_size": 0,
                        "mode": self.mode
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
                        "orientation": m[0],
                        "hz": 0,
                        "queue_size": 0,
                        "mode": self.mode
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
                        "orientation": m[0],
                        "hz": 0,
                        "queue_size": 0,
                        "mode": self.mode
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
                        "orientation": m[0],
                        "hz": 0,
                        "queue_size": 0,
                        "mode": self.mode
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
                        "orientation": m[0],
                        "hz": 1,
                        "queue_size": 100,
                        "mode": self.mode
                    }
                    self.devices.append(msg)
            else:
                self.logger.error("Device declared in yaml does not exist: {}".format(s))

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
            elif d["type"] == "MICROPHONE":
                self.controllers[d["id"]] = MicrophoneController(info = d, logger = self.logger)
            else:
                self.logger.error("Controller declared in yaml does not exist: {}".format(d["name"]))

    def get(self):
        return {
            "devices": self.devices,
            "controllers": self.controllers
        }
