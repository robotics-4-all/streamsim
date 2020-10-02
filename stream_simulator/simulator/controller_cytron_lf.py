#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random

from .pid import PID

from colorama import Fore, Style

from commlib.logger import Logger
from derp_me.client import DerpMeClient

from .conn_params import ConnParams
if ConnParams.type == "amqp":
    from commlib.transports.amqp import ActionServer, RPCService, Subscriber
elif ConnParams.type == "redis":
    from commlib.transports.redis import ActionServer, RPCService, Subscriber



class CytronLFController:
    def __init__(self, info = None):
        self.logger = Logger(info["name"] + "-" + info["id"])

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]

        self.derp_client = DerpMeClient(conn_params=ConnParams.get("redis"))

        if self.info["mode"] == "real": 
            from pidevices import CytronLfLSS05Mcp23017

            self.lf = CytronLfLSS05Mcp23017(bus=self.conf["bus"],
                                                address=self.conf["address"],
                                                mode=self.conf["mode"],
                                                so_1=self.conf["so_1"],
                                                so_2=self.conf["so_2"],
                                                so_3=self.conf["so_3"],
                                                so_4=self.conf["so_4"],
                                                so_5=self.conf["so_5"],
                                                cal=self.conf["cal"],
                                                name=self.name,
                                                max_data_length=self.conf["max_data_length"])
                        
            self._lf_controller = LineFollowingMotion(self.lf, sample_rate=30, kp=0.09, ki=0.003, kd=0.0015, sensor_config=self.info)

            ## https://github.com/robotics-4-all/tektrain-ros-packages/blob/master/ros_packages/robot_hw_interfaces/imu_hw_interface/imu_hw_interface/imu_hw_interface.py

        self.memory = 100 * [0]

    
        # initialize action server for the line following motion -> handler: on_goal
        _topic = info["base_topic"] + "/line_following"
        self.lf_motion_action_server = ActionServer(
            conn_params=ConnParams.get("redis"),
            on_goal=self.on_goal,
            action_name=_topic)
        self.logger.info(f"{Fore.GREEN}Created redis ActionServer {_topic}{Style.RESET_ALL}")

        self.enable_rpc_server = RPCService(
            conn_params=ConnParams.get("redis"),
            on_request=self.enable_callback,
            rpc_name=info["base_topic"] + "/enable")
        self.disable_rpc_server = RPCService(
            conn_params=ConnParams.get("redis"),
            on_request=self.disable_callback,
            rpc_name=info["base_topic"] + "/disable")

    def robot_pose_update(self, message, meta):
        self.robot_pose = message

    def sensor_read(self):
        self.logger.info("Cytron-LF {} sensor read thread started".format(self.info["id"]))

        while self.info["enabled"]:
            time.sleep(1.0 / self.info["hz"])

            val = {}

            if self.info["mode"] == "mock":
                val = {
                    "so_1": 1 if (random.uniform(0,1) > 0.5) else 0,
                    "so_2": 1 if (random.uniform(0,1) > 0.5) else 0,
                    "so_3": 1 if (random.uniform(0,1) > 0.5) else 0,
                    "so_4": 1 if (random.uniform(0,1) > 0.5) else 0,
                    "so_5": 1 if (random.uniform(0,1) > 0.5) else 0
                }

            elif self.info["mode"] == "simulation":
                try:
                    val = {
                        "so_1": 1 if (random.uniform(0,1) > 0.5) else 0,
                        "so_2": 1 if (random.uniform(0,1) > 0.5) else 0,
                        "so_3": 1 if (random.uniform(0,1) > 0.5) else 0,
                        "so_4": 1 if (random.uniform(0,1) > 0.5) else 0,
                        "so_5": 1 if (random.uniform(0,1) > 0.5) else 0
                    }
                except:
                    self.logger.warning("Pose not got yet..")
            else: # The real deal
                data = self._lf_controller.read()

                val = data._asdict()
                
                #self.logger.warning("{} mode not implemented for {}".format(self.info["mode"], self.name))

            self.memory_write(val)

            r = self.derp_client.lset(
                self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.cytron_lf.roll",
                [{"data": val["so_1"], "timestamp": time.time()}])
            r = self.derp_client.lset(
                self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.cytron_lf.roll",
                [{"data": val["so_2"], "timestamp": time.time()}])
            r = self.derp_client.lset(
                self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.cytron_lf.roll",
                [{"data": val["so_3"], "timestamp": time.time()}])
            r = self.derp_client.lset(
                self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.cytron_lf.roll",
                [{"data": val["so_4"], "timestamp": time.time()}])
            r = self.derp_client.lset(
                self.info["namespace"][1:] + "." + self.info["device_name"] + ".variables.robot.cytron_lf.roll",
                [{"data": val["so_5"], "timestamp": time.time()}])
           

        self.logger.info("Cytron-LF {} sensor read thread stopped".format(self.info["id"]))

    def enable_callback(self, message, meta):
        self.info["enabled"] = True
        self.info["hz"] = message["hz"]
        self.info["queue_size"] = message["queue_size"]

        self.memory = self.info["queue_size"] * [0]
        self.sensor_read_thread = threading.Thread(target = self.sensor_read)
        self.sensor_read_thread.start()
        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        self.logger.info("Cytron-LF {} stops reading".format(self.info["id"]))
        return {"enabled": False}

    # def enable_line_following(self):
    #     # if it is idle start it
    #     if self.info["mode"] == "real":
    #         print("Is in line:", self._lf_controller.isInLine())
    #         if not self._lf_controller.isInLine():
    #             self._lf_controller.start()


    
    def on_goal(self, goalh):
        self.logger.info("{} Line following motion started".format(self.name))

        if self.info["enabled"] == False:
            print("Controller is not enabled. Aborting...")
            return {}

        try:
            duration = goalh.data["duration"]       # duration of the line following function
            speed = goalh.data["speed"]             # speed at which the robot will follow the line
        except Exception as e:
            self.logger.error("{} goal missing one of both the parameters: duration, speed".format(self.name))

        now = time.time()


        timestamp = time.time()
        secs = int(timestamp)
        nanosecs = int((timestamp-secs) * 10**(9))
        ret = {
            "header":{
                "stamp":{
                    "sec": secs,
                    "nanosec": nanosecs
                }
            },
            "status": -1
        }

        if self._lf_controller.isInLine():
            # already running, abort action
            return ret
        else:
            self._lf_controller.start()
            self._lf_controller.speed = speed   # override default speed

            # TO ADD LOOKUP TABLE

        # do the work untill the goal is accomplished or cancele
        while (time.time() - now) < duration + 0.02:
            # if the goal is canceled
            if goalh.cancel_event.is_set():
                self._lf_controller.stop()

                self.logger.info("Goal Canceled")
                ret["status"] = -2
                return ret

            # if robot gets out of line either because the line finished or it failes to follow it
            if not self._lf_controller.isInLine():
                self.logger.info("{} Robot out of Line from ".format(self.name))
                ret["status"] = -3
                return ret

            time.sleep(0.1)

        # if goal is achieved (movement for time:duration at speed: speed)
        self._lf_controller.stop()

        self.logger.info("{} Goal finished".format(self.name))
        ret["status"] = 0
        return ret


    def start(self):
        # initialize action server
        self.lf_motion_action_server.run()

        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        if self.info["mode"] == "real":
            self._lf_controller.lf.calibrate()

        if self.info["enabled"]:
            self.memory = self.info["queue_size"] * [0]
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info("Cytron Line Follower {} reads with {} Hz".format(self.info["id"], self.info["hz"]))
            
    def stop(self):
        self.info["enabled"] = False
        # stop action server
        self.lf_motion_action_server._goal_rpc.stop()
        self.lf_motion_action_server._cancel_rpc.stop()
        self.lf_motion_action_server._result_rpc.stop()
        
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()
        
        # maybe join it
        self.sensor_read_thread.join()

        # if we are on "real" mode and the controller has started then Terminate it
        if self.info["mode"] == "real":
            if self._lf_controller.isInLine():
                self._lf_controller.stop()
                self.lf.stop()

    def memory_write(self, data):
        del self.memory[-1]
        self.memory.insert(0, data)

    def cytron_lf_callback(self, message, meta):
        if self.info["enabled"] is False:
            return {"data": []}

        self.logger.info("Robot {}: Cytron lf callback: {}".format(self.name, message))
        try:
            _to = message["from"] + 1
            _from = message["to"]
        except Exception as e:
            self.logger.error("{}: Malformed message for Cytron lf: {} - {}".format(self.name, str(e.__class__), str(e)))
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
                "so_1": self.memory[-i]["so_1"],
                "so_2": self.memory[-i]["so_2"],
                "so_3": self.memory[-i]["so_3"],
                "so_4": self.memory[-i]["so_4"],
                "so_5": self.memory[-i]["so_5"]
            })
        return ret




class LineFollowingMotion(PID):
    TIMEOUT = 0.4

    def __init__(self, line_follower, sample_rate, kp, ki, kd, sensor_config):
        # initialize classes
        super(LineFollowingMotion, self).__init__(sample_rate, kp, ki, kd)

        from pidevices import DfrobotMotorControllerPiGPIO

        # to add initialazation of motor controller form tektrain_real.yaml -> edit device lookup
        self.conf = sensor_config["sensor_configuration"]

        self.motor_driver = DfrobotMotorControllerPiGPIO(E1=20, E2=12, M1=21, M2=16, range=1.0) 
        self.motor_driver.start()

        self.lf = line_follower
        
        # setup constants 
        self.pid_gains = [kp, ki, kd]
        self.weights =  [-5, -2.5, 0.0, 2.5, 5]

        # other members
        self._speed = 0.0

        self.thread = None
        self._alive = False
        
        self._stop_timer = 0.0
        self._stop_state = False

        self.measurements = [0, 0, 0, 0, 0]

    def start(self):
        print("initializing")

        self._alive = True
        self._speed = 0.4

        self.thread = threading.Thread(target=self._run, args=(), daemon = True)
        self.thread.start()

        print("Thread started")

        
    def _run(self):
        while self._alive:
            self._read()

            curr_error = self._error()
            pid = self.calcPID(curr_error)

            self._move(pid)

            if not self._alive:
                self.stop()

            time.sleep(self._sample_period + 0.001)

    def _read(self):
        self.measurements = list(self.read())

        # stopping condition - out of the line for TIMEOUT seconds
        if sum(self.measurements) == 0.0:
            if not self._stop_state:     
                self._stop_timer = time.time()
                self._stop_state = True
            else:
                if (time.time() - self._stop_timer) > self.TIMEOUT:
                    print("***** Terminated ******")
                    self.stop()
        else:
            self._stop_timer = time.time()
            self._stop_state  = False


    def read(self):
        return self.lf.read()


    @property
    def speed(self):
        return self._speed

    @speed.setter
    def speed(self, val):
        if 0 <= val and val <= 1.0:
            self._speed = val

    def isInLine(self):
        return self._alive

    def _error(self):
        if not self._alive:
            return 0.0
            
        if sum(self.measurements) != 0:
            # calculate normal internal product
            error = 0.0
            for i in range(len(self.measurements)):
                error += self.measurements[i] * self.weights[i]

            error /= sum(self.measurements) 
        else:
            #no measurements error is zero ~ out of line
            error = 0.0

        return error

    def _move(self, pid_val):
        if not self._alive:
            return
        
        if self._speed + pid_val > 1.0:
            leftover = self._speed + pid_val - 1.0

            self.motor_driver.move_linear_side(1.0, 1)
            self.motor_driver.move_linear_side(self._speed - pid_val - leftover, 0)
        else:
            self.motor_driver.move_linear_side(self._speed + pid_val, 1)
            self.motor_driver.move_linear_side(self._speed - pid_val, 0)


    def stop(self):
        if self._alive:
            self._alive = False
            self._speed = 0
            self.motor_driver.stop()

            print("Line follower terminated")