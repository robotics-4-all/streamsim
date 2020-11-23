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

from colorama import Fore, Style

from commlib.logger import Logger
from derp_me.client import DerpMeClient

from .conn_params import ConnParams
if ConnParams.type == "amqp":
    from commlib.transports.amqp import RPCService
elif ConnParams.type == "redis":
    from commlib.transports.redis import RPCService

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
from .controller_speaker import SpeakerController
from .controller_touch_screen import TouchScreenController
from .controller_gstreamer_server import GstreamerServerController

#import my controllers
from .controller_button_array_mcp23017 import ButtonArrayController
from .controller_cytron_lf import CytronLFController

class DeviceLookup:
    def __init__(self,
        world = None,
        map = None,
        logger = None,
        name = None,
        namespace = None,
        device_name = None,
        derp = None
    ):
        self.world = world
        if logger is None:
            self.logger = Logger(name + "/device_discovery")
            self._common_logging = False
        else:
            self.logger = logger
            self._common_logging = True
            self.logger.info("Common logging is true")
        self.name = name
        self.device_name = device_name
        self.namespace = namespace
        self.devices = []
        self.controllers = {}
        self.map = map

        if derp is None:
            self.derp_client = DerpMeClient(conn_params=ConnParams.get("redis"))
            self.logger.warning(f"New derp-me client from device lookup")
        else:
            self.derp_client = derp

        # Mode: one of {real, mock, simulation}
        self.mode = self.world["robots"][0]["mode"]
        self.speak_mode = self.world["robots"][0]["speak_mode"]
        if self.mode not in ["real", "mock", "simulation"]:
            self.logger.error("Selected mode is invalid: {}".format(self.mode))
            exit(1)
        self.sensors_streamable = self.world["robots"][0]["sensors_streamable"]

        id_length = 4
        for s in self.world["robots"][0]["devices"]:
            if s == "gstreamer_server":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = "id_" + str(cnt)
                    # id = 'id_' + ''.join(random.choices(
                    #     string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "GSTREAMER_SERVER",
                        "brand": "gstream",
                        "base_topic": self.name + "/sensor/audio/gstreamer/d" + str(cnt) + "/" + id,
                        "name": "gstreamer_" + str(cnt),
                        "place": m["place"],
                        "id": id,
                        "enabled": True,
                        "orientation": m["orientation"],
                        "queue_size": 0,
                        "mode": self.mode,
                        "speak_mode": self.speak_mode,
                        "namespace": self.namespace,
                        "sensor_configuration": m["sensor_configuration"],
                        "device_name": self.device_name
                    }
                    self.devices.append(msg)
            elif s == "microphone":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = "id_" + str(cnt)
                    # id = 'id_' + ''.join(random.choices(
                    #     string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "MICROPHONE",
                        "brand": "usb_mic",
                        "base_topic": self.name + "/sensor/audio/microphone/d" + str(cnt) + "/" + id,
                        "name": "microphone_" + str(cnt),
                        "place": m["place"],
                        "id": id,
                        "enabled": True,
                        "orientation": m["orientation"],
                        "queue_size": 0,
                        "mode": self.mode,
                        "speak_mode": self.speak_mode,
                        "namespace": self.namespace,
                        "sensor_configuration": m["sensor_configuration"],
                        "device_name": self.device_name,
                        "actors": self.world["actors"]
                    }
                    self.devices.append(msg)
            elif s == "cytron_lf":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = "id_" + str(cnt)
                    # id = 'id_' + ''.join(random.choices(
                    #     string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "LINE_FOLLOWER",
                        "brand": "line_follower",
                        "base_topic": self.name + "/sensor/distance/cytron_lf/d" + str(cnt) + "/" + id,
                        "name": "cytron_lf_" + str(cnt),
                        "place": m["place"],
                        "id": id,
                        "enabled": True,
                        "streamable": self.sensors_streamable,
                        "orientation": m["orientation"],
                        "hz": m["hz"],
                        "queue_size": 100,
                        "mode": self.mode,
                        "speak_mode": self.speak_mode,
                        "namespace": self.namespace,
                        "sensor_configuration": m["sensor_configuration"],
                        "device_name": self.device_name
                    }
                    self.devices.append(msg)
            elif s == "sonar":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = "id_" + str(cnt)
                    # id = 'id_' + ''.join(random.choices(
                    #     string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "SONAR",
                        "brand": "sonar",
                        "base_topic": self.name + "/sensor/distance/sonar/d" + str(cnt) + "/" + id,
                        "name": "sonar_" + str(cnt),
                        "place": m["place"],
                        "id": id,
                        "enabled": True,
                        "streamable": self.sensors_streamable,
                        "orientation": m["orientation"],
                        "hz": m["hz"],
                        "queue_size": 100,
                        "mode": self.mode,
                        "speak_mode": self.speak_mode,
                        "namespace": self.namespace,
                        "sensor_configuration": m["sensor_configuration"],
                        "max_range": m["max_range"],
                        "device_name": self.device_name
                    }
                    self.devices.append(msg)
            elif s == "ir":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = "id_" + str(cnt)
                    # id = 'id_' + ''.join(random.choices(
                    #     string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "IR",
                        "brand": "ir",
                        "base_topic": self.name + "/sensor/distance/ir/d" + str(cnt) + "/" + id,
                        "name": "ir_" + str(cnt),
                        "place": m["place"],
                        "id": id,
                        "enabled": True,
                        "streamable": self.sensors_streamable,
                        "orientation": m["orientation"],
                        "hz": m["hz"],
                        "queue_size": 100,
                        "mode": self.mode,
                        "speak_mode": self.speak_mode,
                        "namespace": self.namespace,
                        "sensor_configuration": m["sensor_configuration"],
                        "max_range": m["max_range"],
                        "device_name": self.device_name
                    }
                    self.devices.append(msg)
            elif s == "tof":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = "id_" + str(cnt)
                    # id = 'id_' + ''.join(random.choices(
                    #     string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "TOF",
                        "brand": "vl53l1x",
                        "base_topic": self.name + "/sensor/distance/tof/d" + str(cnt) + "/" + id,
                        "name": "tof_" + str(cnt),
                        "place": m["place"],
                        "id": id,
                        "enabled": True,
                        "streamable": self.sensors_streamable,
                        "orientation": m["orientation"],
                        "hz": m["hz"],
                        "queue_size": 100,
                        "mode": self.mode,
                        "speak_mode": self.speak_mode,
                        "namespace": self.namespace,
                        "sensor_configuration": m["sensor_configuration"],
                        "max_range": m["max_range"],
                        "device_name": self.device_name
                    }
                    self.devices.append(msg)
            elif s == "camera":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = "id_" + str(cnt)
                    # id = 'id_' + ''.join(random.choices(
                    #     string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "CAMERA",
                        "brand": "picamera",
                        "base_topic": self.name + "/sensor/visual/camera/d" + str(cnt) + "/" + id,
                        "name": "camera_" + str(cnt),
                        "place": m["place"],
                        "id": id,
                        "enabled": True,
                        "streamable": self.sensors_streamable,
                        "orientation": m["orientation"],
                        "hz": m["hz"],
                        "queue_size": 0,
                        "mode": self.mode,
                        "speak_mode": self.speak_mode,
                        "namespace": self.namespace,
                        "sensor_configuration": m["sensor_configuration"],
                        "device_name": self.device_name,
                        "actors": self.world["actors"]
                    }
                    self.devices.append(msg)
            elif s == "imu":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = "id_" + str(cnt)
                    # id = 'id_' + ''.join(random.choices(
                    #     string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "IMU",
                        "brand": "icm_20948",
                        "base_topic": self.name + "/sensor/imu/accel_gyro_magne_temp/d" + str(cnt) + "/" + id,
                        "name": "imu_" + str(cnt),
                        "place": m["place"],
                        "id": id,
                        "enabled": True,
                        "streamable": self.sensors_streamable,
                        "orientation": m["orientation"],
                        "hz": m["hz"],
                        "queue_size": 100,
                        "mode": self.mode,
                        "speak_mode": self.speak_mode,
                        "namespace": self.namespace,
                        "sensor_configuration": m["sensor_configuration"],
                        "device_name": self.device_name
                    }
                    self.devices.append(msg)
            elif s == "button":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = "id_" + str(cnt)
                    # id = 'id_' + ''.join(random.choices(
                    #     string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "BUTTON",
                        "brand": "simple",
                        "base_topic": self.name + "/sensor/button/tactile_switch/d" + str(cnt) + "/" + id,
                        "name": "button_" + str(cnt),
                        "place": m["place"],
                        "id": id,
                        "enabled": True,
                        "streamable": self.sensors_streamable,
                        "orientation": m["orientation"],
                        "hz": 1,
                        "queue_size": 100,
                        "mode": self.mode,
                        "speak_mode": self.speak_mode,
                        "namespace": self.namespace,
                        "sensor_configuration": m["sensor_configuration"],
                        "device_name": self.device_name
                    }

                    self.devices.append(msg)
            elif s == "env":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = "id_" + str(cnt)
                    # id = 'id_' + ''.join(random.choices(
                    #     string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "ENV",
                        "brand": "bme680",
                        "base_topic": self.name + "/sensor/env/temp_hum_pressure_gas/d" + str(cnt) + "/" + id,
                        "name": "env_" + str(cnt),
                        "place": m["place"],
                        "id": id,
                        "enabled": True,
                        "streamable": self.sensors_streamable,
                        "orientation": m["orientation"],
                        "hz": m["hz"],
                        "queue_size": 100,
                        "mode": self.mode,
                        "speak_mode": self.speak_mode,
                        "namespace": self.namespace,
                        "sensor_configuration": m["sensor_configuration"],
                        "device_name": self.device_name,
                        "temperature": m["sim_temperature"],
                        "humidity": m["sim_humidity"],
                        "gas": m["sim_air_quality"],
                        "pressure": m["sim_pressure"]
                    }
                    self.devices.append(msg)
            elif s == "speaker":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = "id_" + str(cnt)
                    # id = 'id_' + ''.join(random.choices(
                    #     string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "SPEAKERS",
                        "brand": "usb_speaker",
                        "base_topic": self.name + "/actuator/audio/speaker/usb_speaker/d" + str(cnt) + "/" + id,
                        "name": "speaker_" + str(cnt),
                        "place": m["place"],
                        "id": id,
                        "enabled": True,
                        "orientation": m["orientation"],
                        "queue_size": 0,
                        "mode": self.mode,
                        "speak_mode": self.speak_mode,
                        "namespace": self.namespace,
                        "sensor_configuration": m["sensor_configuration"],
                        "device_name": self.device_name
                    }
                    self.devices.append(msg)
            elif s == "leds":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = "id_" + str(cnt)
                    # id = 'id_' + ''.join(random.choices(
                    #     string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "LED",
                        "brand": "neopx",
                        "base_topic": self.name + "/actuator/visual/leds/neopx/d" + str(cnt) + "/" + id,
                        "name": "led_" + str(cnt),
                        "place": m["place"],
                        "id": id,
                        "enabled": True,
                        "orientation": m["orientation"],
                        "queue_size": 0,
                        "mode": self.mode,
                        "speak_mode": self.speak_mode,
                        "namespace": self.namespace,
                        "sensor_configuration": m["sensor_configuration"],
                        "device_name": self.device_name
                    }
                    self.devices.append(msg)
            elif s == "pan_tilt":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = "id_" + str(cnt)
                    # id = 'id_' + ''.join(random.choices(
                    #     string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "PAN_TILT",
                        "brand": "pca9685",
                        "base_topic": self.name + "/actuator/servo/pantilt/d" + str(cnt) + "/" + id,
                        "name": "pan_tilt_" + str(cnt),
                        "place": m["place"],
                        "id": id,
                        "enabled": True,
                        "orientation": m["orientation"],
                        "queue_size": 0,
                        "mode": self.mode,
                        "speak_mode": self.speak_mode,
                        "namespace": self.namespace,
                        "sensor_configuration": m["sensor_configuration"],
                        "device_name": self.device_name
                    }
                    self.devices.append(msg)
            elif s == "touch_screen":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = "id_" + str(cnt)
                    # id = 'id_' + ''.join(random.choices(
                    #     string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "TOUCH_SCREEN",
                        "brand": "touch_screen",
                        "base_topic": self.name + "/actuator/visual/screen/touch_screen/d" + str(cnt) + "/" + id,
                        "name": "touch_screen_" + str(cnt),
                        "place": m["place"],
                        "id": id,
                        "enabled": True,
                        "orientation": m["orientation"],
                        "queue_size": 0,
                        "mode": self.mode,
                        "speak_mode": self.speak_mode,
                        "namespace": self.namespace,
                        "sensor_configuration": m["sensor_configuration"],
                        "device_name": self.device_name
                    }
                    self.devices.append(msg)
            elif s == "skid_steer":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = "id_" + str(cnt)
                    # id = 'id_' + ''.join(random.choices(
                    #     string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "SKID_STEER",
                        "brand": "twist",
                        "base_topic": self.name + "/actuator/motion/base/twist/d" + str(cnt) + "/" + id,
                        "name": "skid_steer_" + str(cnt),
                        "place": m["place"],
                        "id": id,
                        "enabled": True,
                        "orientation": m["orientation"],
                        "queue_size": 0,
                        "mode": self.mode,
                        "speak_mode": self.speak_mode,
                        "namespace": self.namespace,
                        "sensor_configuration": m["sensor_configuration"],
                        "device_name": self.device_name
                    }
                    self.devices.append(msg)
            elif s == "encoder":
                devices = self.world["robots"][0]["devices"][s]
                cnt = -1
                for m in devices:
                    cnt += 1
                    id = "id_" + str(cnt)
                    # id = 'id_' + ''.join(random.choices(
                    #     string.ascii_lowercase + string.digits, k = id_length))
                    msg = {
                        "type": "ENCODER",
                        "brand": "simple",
                        "base_topic": self.name + "/sensor/encoder/d" + str(cnt) + "/" + id,
                        "name": "encoder_" + str(cnt),
                        "place": m["place"],
                        "id": id,
                        "enabled": True,
                        "streamable": self.sensors_streamable,
                        "orientation": m["orientation"],
                        "hz": m["hz"],
                        "queue_size": 100,
                        "mode": self.mode,
                        "speak_mode": self.speak_mode,
                        "namespace": self.namespace,
                        "sensor_configuration": m["sensor_configuration"],
                        "device_name": self.device_name
                    }
                    self.devices.append(msg)
            else:
                self.logger.error("Device declared in yaml does not exist: {}".format(s))


        # Devices management
        _logger = None
        if self._common_logging is True:
            _logger = self.logger
        for d in self.devices:
            if d["type"] == "PAN_TILT":
                self.controllers[d["name"]] = PanTiltController(info = d, logger = _logger, derp = self.derp_client)
            elif d["type"] == "LINE_FOLLOWER":
                self.controllers[d["name"]] = CytronLFController(info = d, logger = _logger, derp = self.derp_client)
            elif d["type"] == "LED":
                self.controllers[d["name"]] = LedsController(info = d, logger = _logger, derp = self.derp_client)
            elif d["type"] == "ENV":
                self.controllers[d["name"]] = EnvController(info = d, logger = _logger, derp = self.derp_client)
            elif d["type"] == "IMU":
                self.controllers[d["name"]] = ImuController(info = d, logger = _logger, derp = self.derp_client)
            elif d["type"] == "SONAR":
                self.controllers[d["name"]] = SonarController(info = d, map = self.map, logger = _logger, derp = self.derp_client)
            elif d["type"] == "IR":
                self.controllers[d["name"]] = IrController(info = d, map = self.map, logger = _logger, derp = self.derp_client)
            elif d["type"] == "SKID_STEER":
                self.controllers[d["name"]] = MotionController(info = d, logger = _logger, derp = self.derp_client)
                # Just keep the motion controller in another var for the simulator:
                self.motion_controller = self.controllers[d["name"]]
            elif d["type"] == "TOF":
                self.controllers[d["name"]] = TofController(info = d, map = self.map, derp = self.derp_client)
            # elif d["type"] == "BUTTON":
            #     self.controllers[d["name"]] = ButtonController(info = d)
            elif d["type"] == "ENCODER":
                self.controllers[d["name"]] = EncoderController(info = d, logger = _logger, derp = self.derp_client)
            elif d["type"] == "CAMERA":
                self.controllers[d["name"]] = CameraController(info = d, logger = _logger, derp = self.derp_client)
            elif d["type"] == "MICROPHONE":
                self.controllers[d["name"]] = MicrophoneController(info = d, logger = _logger, derp = self.derp_client)
            elif d["type"] == "SPEAKERS":
                self.controllers[d["name"]] = SpeakerController(info = d, logger = _logger, derp = self.derp_client)
            elif d["type"] == "TOUCH_SCREEN":
                self.controllers[d["name"]] = TouchScreenController(info = d, logger = _logger, derp = self.derp_client)
            elif d["type"] == "GSTREAMER_SERVER":
                self.controllers[d["name"]] = GstreamerServerController(info = d, logger = _logger, derp = self.derp_client)
            else:
                self.logger.error("Controller declared in yaml does not exist: {}".format(d["name"]))
            self.logger.warning(d["name"] + " controller created")


        #===============================Button Array==================================
        # Gather all buttons and pass them into the Button Array Controller

        self.button_configuration = {
                "places": [],
                "pin_nums": [],
                "direction": "down",
                "bounce": 200,
        }

        for d in self.devices:
            # gather all button numbers and places
            if d["type"] == "BUTTON":
                self.button_configuration["pin_nums"].append(d["sensor_configuration"].get("pin_num"))
                self.button_configuration["places"].append(d["place"])

        #print("Print button configuration:", self.button_configuration,  " of size: ", len(self.button_configuration))

        # if there were any buttons registered create a generic msg passing their configurations
        if len(self.button_configuration["pin_nums"]) > 0:
            #print("Adding button array")
            cnt = 0
            id = "id_" + str(cnt)
            msg = {
                "type": "BUTTON_ARRAY",
                "brand": "simple",
                "base_topic": self.name + "/sensor/button_array/d" + str(cnt) + "/" + id,
                "name": "button_array_" + str(cnt),
                "place": "UNKNOWN",
                "id": id,
                "enabled": True,
                "streamable": self.sensors_streamable,
                "orientation": 0,
                "hz": 1,
                "queue_size": 100,
                "mode": self.mode,
                "speak_mode": self.speak_mode,
                "namespace": self.namespace,
                "sensor_configuration": self.button_configuration,
                "device_name": self.device_name
            }

            self.devices.append(msg)

            #self.devices.append(msg)
            self.controllers[msg["name"]] = ButtonArrayController(info = msg, logger = _logger, derp = self.derp_client)
        #===============================================================================


    def get(self):
        return {
            "devices": self.devices,
            "controllers": self.controllers
        }
