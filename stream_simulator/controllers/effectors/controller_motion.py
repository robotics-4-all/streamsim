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
from stream_simulator.connectivity import CommlibFactory
from stream_simulator.base_classes import BaseThing

class MotionController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = Logger(conf["name"])
        else:
            self.logger = package["logger"]

        super(self.__class__, self).__init__()
        id = BaseThing.id

        info = {
            "type": "SKID_STEER",
            "brand": "twist",
            "base_topic": package["name"] + ".actuator.motion.twist.d" + str(id),
            "name": "skid_steer_" + str(id),
            "place": conf["place"],
            "id": id,
            "enabled": True,
            "orientation": conf["orientation"],
            "queue_size": 0,
            "mode": package["mode"],
            "namespace": package["namespace"],
            "sensor_configuration": conf["sensor_configuration"],
            "device_name": package["device_name"],
            "endpoints":{
                "enable": "rpc",
                "disable": "rpc",
                "set": "action",
                "calibrate": "rpc",
                "follow_line": "action"
            },
            "data_models": {
                "data": ["linear", "angular"]
            }
        }

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]
        self.base_topic = info["base_topic"]
        self.derp_data_key = info["base_topic"] + ".raw"

        # tf handling
        tf_package = {
            "type": "robot",
            "subtype": "skid_steer",
            "pose": conf["pose"],
            "base_topic": info['base_topic'],
            "name": self.name
        }
        tf_package['host'] = package['device_name']
        tf_package['host_type'] = 'robot'
        package["tf_declare"].call(tf_package)

        if self.info["mode"] == "real":
            from pidevices import DfrobotMotorControllerPiGPIO
            
            self.motor_driver = DfrobotMotorControllerPiGPIO(E1=self.conf["E1"], M1=self.conf["M1"], E2=self.conf["E2"], M2=self.conf["M2"])
            self.motor_driver.start()

            self.wheel_separation = self.conf["wheel_separation"]
            self.wheel_radius = self.conf["wheel_radius"]

            self.device_finder = CommlibFactory.getRPCClient(
                broker="redis",            
                rpc_name = f"robot.{self.info['device_name']}.nodes_detector.get_connected_devices"
            )

            # this thread will initialize the motion module after delay time
            init_delay = 7
            self.initializer = threading.Thread(target=self._init, args=(init_delay,), daemon=True)
            
        self._linear = 0
        self._angular = 0
        
        self.move_action_server = CommlibFactory.getActionServer(
            broker = "redis",
            callback = self.on_goal_cmd_vel,
            action_name = info["base_topic"] + ".set"
        )

        self.motion_calibration_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.calibrate_motion,
            rpc_name = info["base_topic"] + ".calibrate"
        )
        
        self.lf_action_server = CommlibFactory.getActionServer(
            broker = "redis",
            callback = self.on_goal_follow_line,
            action_name = info["base_topic"] + ".follow_line"
        )

        self.enable_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.enable_callback,
            rpc_name = info["base_topic"] + ".enable"
        )

        self.disable_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.disable_callback,
            rpc_name = info["base_topic"] + ".disable"
        )

    def record_devices(self, available_devices):
        for d in available_devices['devices']:
            if d['type'] == "IMU":
                self._imu_topic = d['base_topic'] + ".data"
            elif d['type'] == "ENCODER":
                if d['place'] == "BL":
                    self._enc_left_topic = d['base_topic'] + ".data"
                    self._enc_left_name = d["sensor_configuration"]["name"]
                    self._enc_freq = d["hz"]
                elif d['place'] == "BR":
                    self._enc_right_topic = d['base_topic'] + ".data"
                    self._enc_right_name = d["sensor_configuration"]["name"]
            elif d['type'] == "LINE_FOLLOWER":
                self._lf_topic = d['base_topic'] + ".data"

    def calibrate_motion(self):
        pass
    
    def _enc_left_callback(self, message, meta):
        #self.logger.info("Left encoder callback: {}".format(message))
        self._speed_controller.update({
            'rps': message['rps'],
            'enc': self._enc_left_name
        })

    def _enc_right_callback(self, message, meta):
        #self.logger.info("Right encoder callback: {}".format(message))
        self._speed_controller.update({
            'rps': message['rps'],
            'enc': self._enc_right_name
        })

    def _imu_callback(self, message, meta):
        #self.logger.info("Imu message: {}".format(message))
        self._dirr_controller.update(message['data'])

    def _lf_callback(self, message, meta):
        #self.logger.info("Line follower callback: {}".format(message))
        self._lf_controller.update(list(message.values()))

    def _init(self, delay):
        # wait for all controller to be initialized
        time.sleep(delay)
        
        # record available sensor devices after all controller have been initialized
        available_devices = self.device_finder.call({})
        self.record_devices(available_devices=available_devices)

        from robot_motion import SpeedController, DirectionController, LineFollower, ComplexMotion

        # intialize speed controller of the robot
        path = "../stream_simulator/settings/pwm_to_wheel_rps.json"
        self._speed_controller = SpeedController(wheel_radius=self.wheel_radius,
                                                enc_left_name=self._enc_left_name,
                                                enc_right_name=self._enc_right_name,
                                                path_to_settings=path)

        # initialize the direction controller of the robot
        path = "../stream_simulator/settings/heading_converter.json"
        self._dirr_controller = DirectionController(path_to_heading_settings=path)

        # initialize the line follower controller 
        self._lf_controller = LineFollower(speed=0.35, logger=self.logger)

        # initialize the complex motion controller which is an interface for communicate with both the previous two
        self._complex_controller = ComplexMotion(self.motor_driver, 
                                                 self._speed_controller, 
                                                 self._dirr_controller, 
                                                 self._lf_controller)        

        # subscribe to imu's topic
        self._imu_sub = CommlibFactory.getSubscriber(
            broker = "redis",
            topic = self._imu_topic,
            callback = self._imu_callback
        )

        # subscribe to left encoder's topic
        self._enc_left_sub = CommlibFactory.getSubscriber(
            broker = "redis",
            topic = self._enc_left_topic,
            callback = self._enc_left_callback
        )

        # subscribe to right encoder's topic
        self._enc_right_sub = CommlibFactory.getSubscriber(
            broker = "redis",
            topic = self._enc_right_topic,
            callback = self._enc_right_callback
        )

        #subscribe to line follower's topic
        self._lf_sub = CommlibFactory.getSubscriber(
            broker = "redis",
            topic = self._lf_topic,
            callback = self._lf_callback
        )

        # start subscriptions to the recorded topics
        self._imu_sub.run()
        self._enc_left_sub.run()
        self._enc_right_sub.run()
        self._lf_sub.run()

    def enable_callback(self, message, meta):
        self.info["enabled"] = True
        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        self.move_action_server.run()

        self.enable_rpc_server.run()
        self.disable_rpc_server.run()
        
        if self.info["mode"] == "real":
            self.motion_calibration_server.run()
            self.lf_action_server.run()
            self.initializer.start()

    def stop(self):
        self.move_action_server.stop()

        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()
        
        if self.info["mode"] == "real":
            self.motion_calibration_server.stop()
            self.lf_action_server.stop()
            self._imu_sub.stop()
            self._enc_left_sub.stop()
            self._enc_right_sub.stop()

    def cmd_vel(self, goalh):
        print(goalh.data)

        time.sleep(1)
        timestamp = time.time()
        secs = int(timestamp)
        nanosecs = int((timestamp-secs) * 10**(9))
        ret = {
            "header":{
                "stamp":{
                    "sec": secs,
                    "nanosec": nanosecs
                }
            }
        }

        return ret

    def on_goal_cmd_vel(self, goalh):
        self.logger.info("Robot motion started {}".format(self.name))

        self.logger.info("=========================================== {}".format(goalh.data['duration']))

        ret = self._goal_handler(goalh)
        
        self.logger.info("{} Robot motion finished".format(self.name))
        return ret

    def on_goal_follow_line(self, goalh):
        self.logger.info("Line following started {}".format(self.name))
        
        ret = self._goal_handler(goalh)

        self.logger.info("{} Line following finished".format(self.name))
        return ret

    
    def _goal_handler(self, goalh):
        timestamp = time.time()
        secs = int(timestamp)
        nanosecs = int((timestamp-secs) * 10**(9))
        ret = {
            "header":{
                "stamp":{
                    "sec": secs,
                    "nanosec": nanosecs
                }
            }
        }

        self._complex_controller.set_next_goal(goal=goalh.data)

        while self._complex_controller.is_running():
            if goalh.cancel_event.is_set():
                self._complex_controller.preempt_goal()
                self.logger.info("Goal Cancelled")

                return ret
            time.sleep(0.1)

