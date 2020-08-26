#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random

from commlib_py.logger import Logger

from stream_simulator import ConnParams
if ConnParams.type == "amqp":
    from commlib_py.transports.amqp import RPCServer, Subscriber
elif ConnParams.type == "redis":
    from commlib_py.transports.redis import RPCServer, Subscriber

class MotionController:
    def __init__(self, info = None):
        self.logger = Logger(info["name"] + "-" + info["id"])

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]

        if self.info["mode"] == "real":
            from pidevices import Mcp23017GPIO
            self.motor_controller = Mcp23017GPIO(bus=self.conf["bus"], address=self.conf["address"], 
                                                 E1=self.conf["E1"], M1=self.conf["M1"], 
                                                 E2=self.conf["E2"], M2=self.conf["M2"])
            
            #self.motor_controller = Mcp23017GPIO(bus=1, address=0x22, M2="B_0", E2="B_1",M1="B_3", E1="B_2")

            self.motor_controller.initialize()
            
            self.motor_controller.set_pin_function('M2', 'output')
            self.motor_controller.set_pin_function('M1', 'output')

            self.motor_controller.set_pin_function('E2', 'output')
            self.motor_controller.set_pin_function('E1', 'output')
            
            
            self.motor_controller.set_pin_pwm('E1', True)
            self.motor_controller.set_pin_pwm('E2', True)

            self.motor_controller.set_pin_frequency('E1', 200)
            self.motor_controller.set_pin_frequency('E2', 200)

            
            self.wheel_separation = self.conf["wheel_separation"]
            self.wheel_radius = self.conf["wheel_radius"]
            ## https://github.com/robotics-4-all/tektrain-ros-packages/blob/master/ros_packages/robot_hw_interfaces/motor_controller_hw_interface/motor_controller_hw_interface/motor_controller_hw_interface.py

        self._linear = 0
        self._angular = 0

        self.memory = 100 * [0]

        self.vel_sub = Subscriber(conn_params=ConnParams.get(), topic = info["base_topic"] + "/set", on_message = self.cmd_vel)

        self.motion_get_server = RPCServer(conn_params=ConnParams.get(), on_request=self.motion_get_callback, rpc_name=info["base_topic"] + "/get")

        self.enable_rpc_server = RPCServer(conn_params=ConnParams.get(), on_request=self.enable_callback, rpc_name=info["base_topic"] + "/enable")
        self.disable_rpc_server = RPCServer(conn_params=ConnParams.get(), on_request=self.disable_callback, rpc_name=info["base_topic"] + "/disable")

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


        self.motor_controller.write("E1", 0)
        self.motor_controller.write("E1", 0)
        self.motor_controller.set_pin_pwm('E2', False)
        self.motor_controller.set_pin_pwm('E1', False)
        self.motor_controller.close()


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

                if self._linear > 0:
                    self.motor_controller.write("M1", 1)
                    self.motor_controller.write("M2", 0)
                    self.motor_controller.write('E1', self._linear)
                    self.motor_controller.write('E2', self._linear)
                elif self._linear < 0:
                    self.motor_controller.write("M1", 0)
                    self.motor_controller.write("M2", 1)
                    self.motor_controller.write('E1', abs(self._linear))
                    self.motor_controller.write('E2', abs(self._linear))
                elif self._angular > 0:
                    self.motor_controller.write("M1", 0)
                    self.motor_controller.write("M2", 0)
                    self.motor_controller.write('E1', self._angular)
                    self.motor_controller.write('E2', self._angular)
                elif self._angular < 0:
                    self.motor_controller.write("M1", 1)
                    self.motor_controller.write("M2", 1)
                    self.motor_controller.write('E1', abs(self._angular))
                    self.motor_controller.write('E2', abs(self._angular))



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
