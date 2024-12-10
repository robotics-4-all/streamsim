#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random

from colorama import Fore, Style

from stream_simulator.base_classes import BaseThing

class EnvDistanceController(BaseThing):
    def __init__(self,
                 conf = None,
                 package = None
                 ):

        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        super().__init__(conf["name"])

        _type = "DISTANCE"
        _category = "sensor"
        _class = "distance"
        _subclass = "sonar"
        _name = conf["name"]
        _pack = package["base"]
        _place = conf["place"]
        id = "d_" + str(BaseThing.id)
        info = {
            "type": _type,
            "base_topic": f"{_pack}.{_place}.{_category}.{_class}.{_subclass}.{_name}",
            "name": _name,
            "place": conf["place"],
            "enabled": True,
            "mode": conf["mode"],
            "conf": conf,
            "categorization": {
                "host_type": _pack,
                "place": _place,
                "category": _category,
                "class": _class,
                "subclass": [_subclass],
                "name": _name
            }
        }

        self.robots_poses = {}

        self.info = info
        self.name = info["name"]
        self.base_topic = info["base_topic"]
        self.hz = info['conf']['hz']
        self.mode = info["mode"]
        self.operation = info['conf']['operation']
        self.operation_parameters = info['conf']['operation_parameters']
        self.place = info["conf"]["place"]
        self.pose = info["conf"]["pose"]
        self.derp_data_key = info["base_topic"] + ".raw"
        self.map = package["map"]
        self.resolution = package["resolution"]
        self.max_range = info['conf']['max_range']
        self.get_device_groups_rpc_topic = package["namespace"] + ".get_device_groups"

        # tf handling
        tf_package = {
            "type": "env",
            "subtype": {
                "category": _category,
                "class": _class,
                "subclass": [_subclass]
            },
            "pose": self.pose,
            "base_topic": self.base_topic,
            "name": self.name
        }

        self.host = None
        if 'host' in info['conf']:
            self.host = info['conf']['host']
            tf_package['host'] = self.host
            # No other host type is available for env_devices
            tf_package['host_type'] = 'pan_tilt'

        self.set_communication_layer(package)

        self.tf_declare_rpc.call(tf_package)

        if self.operation == "triangle":
            self.prev = self.operation_parameters["triangle"]['min']
            self.way = 1
        elif self.operation == "sinus":
            self.prev = 0
        else:
            self.prev = None

    def set_communication_layer(self, package):
        self.set_tf_communication(package)
        self.set_data_publisher(self.base_topic)
        self.set_enable_disable_rpcs(self.base_topic, self.enable_callback, self.disable_callback)
        self.set_mode_get_set_rpcs(self.base_topic, self.set_mode_callback, self.get_mode_callback)

    def robot_pose_callback(self, message):
        nm = message['name'].split(".")[-1]
        if nm not in self.robots_poses:
            self.robots_poses[nm] = {
                'x': 0,
                'y': 0
            }
        self.robots_poses[nm]['x'] = message['x'] / self.resolution
        self.robots_poses[nm]['y'] = message['y'] / self.resolution

    def get_mode_callback(self, message):
        return {
                "mode": self.operation,
                "parameters": self.operation_parameters[self.operation]
        }

    def set_mode_callback(self, message):
        if message["mode"] == "triangle":
            self.prev = self.operation_parameters["triangle"]['min']
            self.way = 1
        elif message["mode"] == "sinus":
            self.prev = 0
        else:
            self.prev = None

        self.operation = message["mode"]
        return {}

    def sensor_read(self):
        # Get all devices and check pan-tilts exist
        get_devices_rpc = self.commlib_factory.getRPCClient(
            rpc_name = self.get_device_groups_rpc_topic
        )
        res = get_devices_rpc.call({})
        # create subscribers
        self.robots_subscribers = {}
        for r in res['robots']:
            self.robots_subscribers[r] = self.commlib_factory.getSubscriber(
                topic = f"robot.{r}.pose", # get poses from all robots
                callback = self.robot_pose_callback
            )
            self.robots_subscribers[r].run()

        self.logger.info(f"Sensor {self.name} read thread started")

        # Operation parameters
        self.constant_value = self.operation_parameters["constant"]['value']
        self.random_min = self.operation_parameters["random"]['min']
        self.random_max = self.operation_parameters["random"]['max']
        self.triangle_min = self.operation_parameters["triangle"]['min']
        self.triangle_max = self.operation_parameters["triangle"]['max']
        self.triangle_step = self.operation_parameters["triangle"]['step']
        self.normal_std = self.operation_parameters["normal"]['std']
        self.normal_mean = self.operation_parameters["normal"]['mean']
        self.sinus_dc = self.operation_parameters["sinus"]['dc']
        self.sinus_amp = self.operation_parameters["sinus"]['amplitude']
        self.sinus_step = self.operation_parameters["sinus"]['step']

        while self.info["enabled"]:
            time.sleep(1.0 / self.hz)

            val = None
            if self.mode == "mock":
                if self.operation == "constant":
                    val = self.constant_value
                elif self.operation == "random":
                    val = random.uniform(
                        self.random_min,
                        self.random_max
                    )
                elif self.operation == "normal":
                    val = random.gauss(
                        self.normal_mean,
                        self.normal_std
                    )
                elif self.operation == "triangle":
                    val = self.prev + self.way * self.triangle_step
                    if val >= self.triangle_max or val <= self.triangle_min:
                        self.way *= -1
                    self.prev = val
                elif self.operation == "sinus":
                    val = self.sinus_dc + self.sinus_amp * math.sin(self.prev)
                    self.prev += self.sinus_step
                else:
                    self.logger.warning(f"Unsupported operation: {self.operation}")

            elif self.mode == "simulation":
                # Get pose of the sensor (in case it is on a pan-tilt)
                pp = self.commlib_factory.get_tf.call({
                    "name": self.name
                })
                xx = pp['x'] / self.resolution
                yy = pp['y'] / self.resolution
                th = pp['theta']

                d = 1
                tmpx = int(xx)
                tmpy = int(yy)
                limit = self.max_range / self.resolution
                robot = False
                while self.map[int(tmpx), int(tmpy)] == 0 and d < limit and robot == False:
                    d += 1
                    tmpx = xx + d * math.cos(th)
                    tmpy = yy + d * math.sin(th)

                    # Check robots atan2
                    for r in self.robots_poses:
                        dd = math.sqrt(
                            math.pow(tmpy - self.robots_poses[r]['y'], 2) + \
                            math.pow(tmpx - self.robots_poses[r]['x'], 2)
                        )
                        # print(dd, 0.5 / self.resolution)
                        if dd < (0.5 / self.resolution):
                            print(d * self.resolution)
                            robot = True

                val = d * self.resolution

                # print(self.name, val)
            # Publishing value:
            self.publisher.publish({
                "value": val,
                "timestamp": time.time()
            })

    def enable_callback(self, message):
        self.info["enabled"] = True

        self.enable_rpc_server.run()
        self.disable_rpc_server.run()
        self.get_mode_rpc_server.run()
        self.set_mode_rpc_server.run()

        self.sensor_read_thread = threading.Thread(target = self.sensor_read)
        self.sensor_read_thread.start()

        return {"enabled": True}

    def disable_callback(self, message):
        self.info["enabled"] = False
        return {"enabled": False}

    def get_callback(self, message):
        return {"state": self.state}

    def set_callback(self, message):
        state = message["state"]
        if state not in self.allowed_states:
            raise Exception(f"{self.name} does not allow {state} state")

        self.state = state
        return {"state": self.state}

    def start(self):
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()
        self.get_mode_rpc_server.run()
        self.set_mode_rpc_server.run()

        if self.info["enabled"]:
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()

    def stop(self):
        self.info["enabled"] = False
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()
        self.get_mode_rpc_server.stop()
        self.set_mode_rpc_server.stop()
