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
from stream_simulator.connectivity import CommlibFactory

class EnvDistanceController(BaseThing):
    def __init__(self,
                 conf = None,
                 package = None
                 ):

        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        super(self.__class__, self).__init__()

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

        package["tf_declare"].call(tf_package)

        # Communication
        self.publisher = CommlibFactory.getPublisher(
            broker = "redis",
            topic = self.base_topic + ".data"
        )
        self.enable_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.enable_callback,
            rpc_name = self.base_topic + ".enable"
        )
        self.disable_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.disable_callback,
            rpc_name = self.base_topic + ".disable"
        )
        self.set_mode_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.set_mode_callback,
            rpc_name = self.base_topic + ".set_mode"
        )
        self.get_mode_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.get_mode_callback,
            rpc_name = self.base_topic + ".get_mode"
        )

        if self.operation == "triangle":
            self.prev = self.operation_parameters["triangle"]['min']
            self.way = 1
        elif self.operation == "sinus":
            self.prev = 0
        else:
            self.prev = None

    def robot_pose_callback(self, message, meta):
        nm = message['name'].split(".")[-1]
        if nm not in self.robots_poses:
            self.robots_poses[nm] = {
                'x': 0,
                'y': 0
            }
        self.robots_poses[nm]['x'] = message['x'] / self.resolution
        self.robots_poses[nm]['y'] = message['y'] / self.resolution

    def get_mode_callback(self, message, meta):
        return {
                "mode": self.operation,
                "parameters": self.operation_parameters[self.operation]
        }

    def set_mode_callback(self, message, meta):
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
        while CommlibFactory.get_tf == None:
            time.sleep(0.1)

        # Get all devices and check pan-tilts exist
        get_devices_rpc = CommlibFactory.getRPCClient(
            rpc_name = "streamsim.get_device_groups"
        )
        res = get_devices_rpc.call({})
        # create subscribers
        self.robots_subscribers = {}
        for r in res['robots']:
            self.robots_subscribers[r] = CommlibFactory.getSubscriber(
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
                pp = CommlibFactory.get_tf.call({
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

    def enable_callback(self, message, meta):
        self.info["enabled"] = True

        self.enable_rpc_server.run()
        self.disable_rpc_server.run()
        self.get_mode_rpc_server.run()
        self.set_mode_rpc_server.run()

        self.sensor_read_thread = threading.Thread(target = self.sensor_read)
        self.sensor_read_thread.start()

        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        return {"enabled": False}

    def get_callback(self, message, meta):
        return {"state": self.state}

    def set_callback(self, message, meta):
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
