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

from .conn_params import ConnParams
if ConnParams.type == "amqp":
    from commlib.transports.amqp import Publisher, RPCService
elif ConnParams.type == "redis":
    from commlib.transports.redis import Publisher, RPCService

from commlib.logger import Logger
from .device_lookup import DeviceLookup

class Robot:
    def __init__(self, world = None, map = None, name = "robot", tick = 0.25):
        self.logger = Logger(name)
        logging.getLogger("pika").setLevel(logging.INFO)

        try:
            self.namespace = os.environ['TEKTRAIN_NAMESPACE']
        except:
            self.logger.warning("No TEKTRAIN_NAMESPACE environmental variable found. Automatically setting it to /robot")
            os.environ["TEKTRAIN_NAMESPACE"] = "/robot"
            self.namespace = "/robot"

        self.raw_name = name
        self.name = self.namespace + "/" + name
        self.dt = tick

        # intial robot pose - remains remains constant throughout streamsim launch
        self._init_x = 0
        self._init_y = 0
        self._init_theta = 0

        # current robot pose - varies during execution
        self._x = 0
        self._y = 0
        self._theta = 0

        self._curr_node = -1

        self.detection_threshold = 1

        # Yaml configuration management
        self.world = world
        self.map = map
        self.width = self.map.shape[0]
        self.height = self.map.shape[1]
        self.resolution = self.world["map"]["resolution"]
        self.logger.info("Robot {}: map set".format(self.name))

        pose = self.world['robots'][0]['starting_pose']
        self._init_x = pose['x'] * self.resolution
        self._init_y = pose['y'] * self.resolution
        self._init_theta = pose['theta'] / 180.0 * math.pi
        self.logger.info("Robot {} pose set: {}, {}, {}".format(
            self.name, self._x, self._y, self._theta))

        self._x = self._init_x
        self._y = self._init_y
        self._theta = self._init_theta

        self.step_by_step_execution = self.world['robots'][0]['step_by_step_execution']
        self.logger.warning("Step by step execution is {}".format(self.step_by_step_execution))

        # Devices set
        self.device_management = DeviceLookup(
            world = self.world, map = self.map, name = self.name,\
            namespace = self.namespace, device_name = name)
        tmp = self.device_management.get()
        self.devices = tmp['devices']
        self.controllers = tmp['controllers']
        try:
            self.motion_controller = self.device_management.motion_controller
        except:
            self.logger.warning("Robot has no motion controller.. Smells like device!".format(self.name))
            self.motion_controller = None

        # rpc service which resets the robot pose to the initial given values
        _topic = self.name + '/reset_robot_pose'
        self.reset_pose_rpc_server = RPCService(
            conn_params=ConnParams.get("redis"),
            on_request=self.reset_pose_callback,
            rpc_name=_topic)
        self.logger.info(f"{Fore.GREEN} Created redis RPCService {_topic} {Style.RESET_ALL}")

        _topic = self.name + '/nodes_detector/get_connected_devices'
        self.devices_rpc_server = RPCService(
            conn_params=ConnParams.get("redis"),
            on_request=self.devices_callback,
            rpc_name=_topic)
        self.logger.info(f"{Fore.GREEN} Created redis RPCService {_topic} {Style.RESET_ALL}")

        _topic =name + "/pose"
        self.internal_pose_pub = Publisher(
            conn_params=ConnParams.get("redis"),
            topic= _topic)
        self.logger.info(f"{Fore.GREEN} Created redis Publisher {_topic}{Style.RESET_ALL}")

        # SIMULATOR ------------------------------------------------------------
        if self.world['robots'][0]['amqp_inform'] is True:
            import commlib

            final_t = self.name.replace("/", ".")[1:]
            final_t = final_t[final_t.find(".") + 1:]
            final_top = final_t + ".pose"
            final_dete_top = final_t + ".detect"
            final_leds_top = final_t + ".leds"
            final_leds_wipe_top = final_t + ".leds.wipe"
            final_exec = final_t + ".execution"

            # AMQP Publishers  -----------------------------------------------

            self.pose_pub = commlib.transports.amqp.Publisher(
                conn_params=ConnParams.get("amqp"),
                topic= final_top)
            self.logger.info(f"{Fore.RED}Created amqp Publisher {final_top}{Style.RESET_ALL}")

            self.detects_pub = commlib.transports.amqp.Publisher(
                conn_params=ConnParams.get("amqp"),
                topic= final_dete_top)
            self.logger.info(f"{Fore.RED}Created amqp Publisher {final_dete_top}{Style.RESET_ALL}")

            self.leds_pub = commlib.transports.amqp.Publisher(
                conn_params=ConnParams.get("amqp"),
                topic= final_leds_top)
            self.logger.info(f"{Fore.RED}Created amqp Publisher {final_leds_top}{Style.RESET_ALL}")

            self.leds_wipe_pub = commlib.transports.amqp.Publisher(
                conn_params=ConnParams.get("amqp"),
                topic= final_leds_wipe_top)
            self.logger.info(f"{Fore.RED}Created amqp Publisher {final_leds_wipe_top}{Style.RESET_ALL}")

            self.execution_pub = commlib.transports.amqp.Publisher(
                conn_params=ConnParams.get("amqp"),
                topic= final_exec)
            self.logger.info(f"{Fore.RED}Created amqp Publisher {final_exec}{Style.RESET_ALL}")

            # AMQP Subscribers  -----------------------------------------------

            _topic = final_t + ".buttons"
            self.buttons_amqp_sub = commlib.transports.amqp.Subscriber(
                conn_params=ConnParams.get("amqp"),
                topic=_topic,
                on_message=self.button_amqp)
            self.logger.info(f"{Fore.RED}Created amqp Subscriber {_topic}{Style.RESET_ALL}")

            if self.step_by_step_execution:
                _topic = final_t + ".step_by_step"
                self.step_by_step_amqp_sub = commlib.transports.amqp.Subscriber(
                    conn_params=ConnParams.get("amqp"),
                    topic=_topic,
                    on_message=self.step_by_step_amqp)
                self.logger.info(f"{Fore.RED}Created amqp Subscriber {_topic}{Style.RESET_ALL}")

            # REDIS Publishers  -----------------------------------------------

            _topic = name + "/buttons_sim"
            self.buttons_sim_pub = Publisher(
                conn_params=ConnParams.get("redis"),
                topic= _topic)
            self.logger.info(f"{Fore.GREEN}Created redis Publisher {_topic}{Style.RESET_ALL}")

            _topic = name + ".next_step"
            self.next_step_pub = Publisher(
                conn_params=ConnParams.get("redis"),
                topic= _topic)
            self.logger.info(f"{Fore.GREEN}Created redis Publisher {_topic}{Style.RESET_ALL}")

            # REDIS Subscribers -----------------------------------------------

            _topic = final_t + ".execution.nodes"
            self.execution_nodes_redis_sub = commlib.transports.redis.Subscriber(
                conn_params=ConnParams.get("redis"),
                topic=_topic,
                on_message=self.execution_nodes_redis)
            self.logger.info(f"{Fore.GREEN}Created redis Subscriber {_topic}{Style.RESET_ALL}")

            _topic = final_t + ".detects"
            self.detects_redis_sub = commlib.transports.redis.Subscriber(
                conn_params=ConnParams.get("redis"),
                topic=_topic,
                on_message=self.detects_redis)
            self.logger.info(f"{Fore.GREEN}Created redis Subscriber {_topic}{Style.RESET_ALL}")

            _topic = final_t + ".leds"
            self.leds_redis_sub = commlib.transports.redis.Subscriber(
                conn_params=ConnParams.get("redis"),
                topic=_topic,
                on_message=self.leds_redis)
            self.logger.info(f"{Fore.GREEN}Created redis Subscriber {_topic}{Style.RESET_ALL}")

            _topic = final_t + ".leds.wipe"
            self.leds_wipe_redis_sub = commlib.transports.redis.Subscriber(
                conn_params=ConnParams.get("redis"),
                topic=_topic,
                on_message=self.leds_wipe_redis)
            self.logger.info(f"{Fore.GREEN}Created redis Subscriber {_topic}{Style.RESET_ALL}")


        # Threads
        self.simulator_thread = threading.Thread(target = self.simulation_thread)

        from derp_me.client import DerpMeClient
        self.derp_client = DerpMeClient(conn_params=ConnParams.get("redis"))

        self.logger.info("Device {} set-up".format(self.name))

    def leds_redis(self, message, meta):
        self.logger.debug("Got leds from redis " + str(message))
        self.logger.warning(f"{Fore.YELLOW}Sending to amqp notifier: {message}{Style.RESET_ALL}")
        self.leds_pub.publish(message)

    def leds_wipe_redis(self, message, meta):
        self.logger.debug("Got leds wipe from redis " + str(message))
        self.logger.warning(f"{Fore.YELLOW}Sending to amqp notifier: {message}{Style.RESET_ALL}")
        self.leds_wipe_pub.publish(message)

    def execution_nodes_redis(self, message, meta):
        self.logger.debug("Got execution node from redis " + str(message))
        self.logger.warning(f"{Fore.MAGENTA}Sending to amqp notifier: {message}{Style.RESET_ALL}")
        message["device"] = self.raw_name 
        self.execution_pub.publish(message)

    def detects_redis(self, message, meta):
        self.logger.warning("Got detect from redis " + str(message))
        # Wait for source
        done = False
        while not done:
            try:
                v2 = self.derp_client.lget(self.name.replace("/", ".")[1:] + ".detect.source", 0, 0)['val'][0]
                self.logger.info("Got the source!")
                done = True
            except:
                time.sleep(0.1)
                self.logger.info("Source not written yet...")

        if v2 != "empty":
            message["actor_id"] = v2["id"]
        else:
            message["actor_id"] = -1    
        self.logger.warning(f"{Fore.CYAN}Sending to amqp notifier: {message}{Style.RESET_ALL}")
        self.detects_pub.publish(message)

    def button_amqp(self, message, meta):
        self.logger.warning("Got button press from amqp " + str(message))
        self.buttons_sim_pub.publish({
            "button": message["button"]
        })

    def step_by_step_amqp(self, message, meta):
        self.logger.info(f"Got next step from amqp")
        self.next_step_pub.publish({})

    def start(self):
        for c in self.controllers:
            self.controllers[c].start()

        if self.world['robots'][0]['amqp_inform'] is True:
            self.buttons_amqp_sub.run()
            self.execution_nodes_redis_sub.run()
            self.detects_redis_sub.run()
            self.leds_redis_sub.run()
            self.leds_wipe_redis_sub.run()
            if self.step_by_step_execution:
                self.step_by_step_amqp_sub.run()

        self.devices_rpc_server.run()
        self.reset_pose_rpc_server.run()
        self.stopped = False
        self.simulator_thread.start()

        r = self.derp_client.lset(
            "stream_sim/state",
            [{
                "state": "ACTIVE",
                "device": self.name,
                "timestamp": time.time()
            }])
        self.logger.warning(f"Wrote in derpme!!!{r}")
        r = self.derp_client.lset(
            f"{self.name}/step_by_step_status",
            [{
                "value": self.step_by_step_execution,
                "timestamp": time.time()
            }])

    def stop(self):
        for c in self.controllers:
            self.logger.warning("Trying to stop controller {}".format(c))
            self.controllers[c].stop()

        if self.world['robots'][0]['amqp_inform'] is True:
            self.buttons_sub.stop()
            if self.step_by_step_execution:
                self.step_by_step_sub.stop()

        self.logger.warning("Trying to stop devices_rpc_server")
        self.devices_rpc_server.stop()
        self.logger.warning("Trying to stop reset_pose_rpc_server")
        self.reset_pose_rpc_server.stop()

        self.logger.warning("Trying to stop simulation_thread")
        self.stopped = True

    def devices_callback(self, message, meta):
        self.logger.warning("Getting devices")
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

    def reset_pose_callback(self, message, meta):
        self.logger.warning("Resetting robot pose")
        self._x = self._init_x
        self._y = self._init_y
        self._theta = self._init_theta
        return {}

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

    def simulation_thread(self):
        while self.stopped is False:
            if self.motion_controller is not None:
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

                if self._x != prev_x or self._y != prev_y or self._theta != prev_th:
                    if self.world['robots'][0]['amqp_inform'] is True:
                        self.logger.info("AMQP pose updated")
                        self.pose_pub.publish({
                            "x": float("{:.2f}".format(self._x)),
                            "y": float("{:.2f}".format(self._y)),
                            "theta": float("{:.2f}".format(self._theta)),
                            "resolution": self.resolution
                        })

                # Send internal pose for distance sensors
                self.internal_pose_pub.publish({
                    "x": float("{:.2f}".format(self._x)),
                    "y": float("{:.2f}".format(self._y)),
                    "theta": float("{:.2f}".format(self._theta)),
                    "resolution": self.resolution
                })

                if self.check_ok(self._x, self._y, prev_x, prev_y):
                    self._x = prev_x
                    self._y = prev_y
                    self._theta = prev_th

            time.sleep(self.dt)
