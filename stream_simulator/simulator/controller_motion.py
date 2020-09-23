#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random

from colorama import Fore, Style

from commlib.logger import Logger

from .conn_params import ConnParams
if ConnParams.type == "amqp":
    from commlib.transports.amqp import RPCService, Subscriber
elif ConnParams.type == "redis":
    from commlib.transports.redis import RPCService, Subscriber

class MotionController:
    def __init__(self, info = None, logger = None):
        if logger is None:
            self.logger = Logger(info["name"] + "-" + info["id"])
        else:
            self.logger = logger

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]

        if self.info["mode"] == "real":
            import wiringpi

            OUTPUT = 1

            self.E1 = self.conf["E1"]
            self.E2 = self.conf["E2"]
            self.M1 = self.conf["M1"]
            self.M2 = self.conf["M2"]

            wiringpi.wiringPiSetupGpio()
            wiringpi.pinMode(self.E1, OUTPUT)
            wiringpi.pinMode(self.E2, OUTPUT)
            wiringpi.pinMode(self.M1, OUTPUT)
            wiringpi.pinMode(self.M2, OUTPUT)

            wiringpi.softPwmCreate(self.E1, 0, 100)
            wiringpi.softPwmCreate(self.E2, 0, 100)


            self.wheel_separation = self.conf["wheel_separation"]
            self.wheel_radius = self.conf["wheel_radius"]

            ## https://github.com/robotics-4-all/tektrain-ros-packages/blob/master/ros_packages/robot_hw_interfaces/motor_controller_hw_interface/motor_controller_hw_interface/motor_controller_hw_interface.py

        self._linear = 0
        self._angular = 0

        self.memory = 100 * [0]

        _topic = info["base_topic"] + "/set"
        self.vel_sub = Subscriber(
            conn_params=ConnParams.get("redis"),
            topic = _topic,
            on_message = self.cmd_vel)
        self.logger.info(f"{Fore.GREEN}Created redis Subscriber {_topic}{Style.RESET_ALL}")

        _topic = info["base_topic"] + "/get"
        self.motion_get_server = RPCService(
            conn_params=ConnParams.get("redis"),
            on_request=self.motion_get_callback,
            rpc_name=_topic)
        self.logger.info(f"{Fore.GREEN}Created redis RPCService {_topic}{Style.RESET_ALL}")

        self.enable_rpc_server = RPCService(
            conn_params=ConnParams.get("redis"),
            on_request=self.enable_callback,
            rpc_name=info["base_topic"] + "/enable")
        self.disable_rpc_server = RPCService(
            conn_params=ConnParams.get("redis"),
            on_request=self.disable_callback,
            rpc_name=info["base_topic"] + "/disable")

    def enable_callback(self, message, meta):
        self.info["enabled"] = True
        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        self.vel_sub.run()
        self.motion_get_server.run()

        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

    def stop(self):
        self.vel_sub.stop()
        self.motion_get_server.stop()

        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()

        if self.info["mode"] == "real":
            import wiringpi
            wiringpi.pinMode(self.M1, 0)
            wiringpi.pinMode(self.M2, 0)
            wiringpi.softPwmStop(self.E1)
            wiringpi.softPwmStop(self.E2)

    def memory_write(self, data):
        del self.memory[-1]
        self.memory.insert(0, data)
        self.logger.info("Robot {}: memory updated for {}".format(self.name, "leds"))

    def cmd_vel(self, message, meta):
        try:
            response = message
            self._linear = response['linear']
            self._angular = response['angular']
            self.memory_write([self._linear, self._angular])

            if self.info["mode"] == "mock":
                pass
            elif self.info["mode"] == "simulation":
                pass
            else: # The real deal
                #self.logger.warning("{} mode not implemented for {}".format(self.info["mode"], self.name))
                print("RUNING...............")
                import wiringpi

                if self._linear > 0:
                    print("writting pwm 1111", int(100 * self._linear))
                    wiringpi.digitalWrite(self.M1, 1)
                    wiringpi.digitalWrite(self.M2, 0)
                    wiringpi.softPwmWrite(self.E1, int(100 * self._linear))
                    wiringpi.softPwmWrite(self.E2, int(100 * self._linear))
                elif self._linear < 0:
                    print("writting pwm 2222", int(100 * self._linear))
                    wiringpi.digitalWrite(self.M1, 0)
                    wiringpi.digitalWrite(self.M2, 1)
                    wiringpi.softPwmWrite(self.E1, int(100 * abs(self._linear)))
                    wiringpi.softPwmWrite(self.E2, int(100 * abs(self._linear)))
                elif self._angular > 0:
                    wiringpi.digitalWrite(self.M1, 0)
                    wiringpi.digitalWrite(self.M2, 0)
                    wiringpi.softPwmWrite(self.E1, int(100 * self._angular))
                    wiringpi.softPwmWrite(self.E2, int(100 * self._angular))
                elif self._angular < 0:
                    wiringpi.digitalWrite(self.M1, 1)
                    wiringpi.digitalWrite(self.M2, 1)
                    wiringpi.softPwmWrite(self.E1, int(100 * abs(self._angular)))
                    wiringpi.softPwmWrite(self.E2, int(100 * abs(self._angular)))


            self.logger.info("{}: New motion command: {}, {}".format(self.name, self._linear, self._angular))
        except Exception as e:
            self.logger.error("{}: cmd_vel is wrongly formatted: {} - {}".format(self.name, str(e.__class__), str(e)))

    def motion_get_callback(self, message, meta):
        self.logger.info("Robot {}: Motion get callback: {}".format(self.name, message))
        try:
            _to = message["from"] + 1
            _from = message["to"]
        except Exception as e:
            self.logger.error("{}: Malformed message for motion get: {} - {}".format(self.name, str(e.__class__), str(e)))
            return []
        ret = {"data": []}
        for i in range(_from, _to): # 0 to -1
            timestamp = time.time()
            secs = int(timestamp)
            nanosecs = int((timestamp-secs) * 10**(9))
            ret["data"].append({
                "header":{
                    "stamp":{
                        "sec": secs,
                        "nanosec": nanosecs
                    }
                },
                "linear": self.memory[-i][0],
                "angular": self.memory[-i][1],
                "deviceId": 0
            })
        return ret
