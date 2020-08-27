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

from .conn_params import ConnParams
if ConnParams.type == "amqp":
    from commlib.transports.amqp import Publisher, RPCService
elif ConnParams.type == "redis":
    from commlib.transports.redis import Publisher, RPCService

from commlib.logger import Logger
from .device_lookup import DeviceLookup

class Robot:
    def __init__(self, world = None, map = None, name = "robot", tick = 0.1):
        self.logger = Logger(name)
        logging.getLogger("pika").setLevel(logging.INFO)

        try:
            self.namespace = os.environ['TEKTRAIN_NAMESPACE']
        except:
            self.logger.warning("No TEKTRAIN_NAMESPACE environmental variable found. Automatically setting it to /robot")
            os.environ["TEKTRAIN_NAMESPACE"] = "/robot"
            self.namespace = "/robot"

        self.name = self.namespace + "/" + name
        self.dt = tick

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
        self._x = pose['x'] * self.resolution
        self._y = pose['y'] * self.resolution
        self._theta = pose['theta'] / 180.0 * math.pi
        self.logger.info("Robot {} pose set: {}, {}, {}".format(
            self.name, self._x, self._y, self._theta))

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

        self.devices_rpc_server = RPCService(conn_params=ConnParams.get(), on_request=self.devices_callback, rpc_name=self.name + '/nodes_detector/get_connected_devices')
        self.logger.info("Created redis RPCService {}".format(self.name + '/nodes_detector/get_connected_devices'))

        self.internal_pose_pub = Publisher(conn_params=ConnParams.get(), topic= name + "/pose")
        self.logger.info("Created redis Publisher {}".format(name + "/pose"))

        # SIMULATOR ------------------------------------------------------------
        if self.world['robots'][0]['amqp_inform'] is True:
            import commlib
            conn_params = commlib.transports.amqp.ConnectionParameters()
            conn_params.credentials.username = 'bot'
            conn_params.credentials.password = 'b0t'
            conn_params.host = 'tektrain-cloud.ddns.net'
            conn_params.port = 5672
            conn_params.vhost = "sim"

            final_t = self.name.replace("/", ".")[1:]
            final_t = final_t[final_t.find(".") + 1:]
            final_top = final_t + ".pose"
            final_dete_top = final_t + ".detect"
            final_leds_top = final_t + ".leds"
            final_leds_wipe_top = final_t + ".leds.wipe"
            final_exec = final_t + ".execution"

            self.pose_pub = commlib.transports.amqp.Publisher(
                conn_params=conn_params, topic= final_top)
            self.logger.info("Created amqp Publisher {}".format(final_top))

            self.detects_pub = commlib.transports.amqp.Publisher(
                conn_params=conn_params, topic= final_dete_top)
            self.logger.info("Created amqp Publisher {}".format(final_dete_top))

            self.leds_pub = commlib.transports.amqp.Publisher(
                conn_params=conn_params, topic= final_leds_top)
            self.logger.info("Created amqp Publisher {}".format(final_leds_top))

            self.leds_wipe_pub = commlib.transports.amqp.Publisher(
                conn_params=conn_params, topic= final_leds_wipe_top)
            self.logger.info("Created amqp Publisher {}".format(final_leds_wipe_top))

            self.execution_pub = commlib.transports.amqp.Publisher(
                conn_params=conn_params, topic= final_exec)
            self.logger.info("Created amqp Publisher {}".format(final_exec))

            self.buttons_sub = commlib.transports.amqp.Subscriber(
                conn_params=conn_params,
                topic=final_t + ".buttons",
                on_message=self.button_amqp)
            self.logger.info("Created amqp Subscriber {}".format(final_t + ".buttons"))
            self.buttons_sub.run()

            self.buttons_sim_pub = Publisher(conn_params=ConnParams.get(), topic= name + "/buttons_sim")
            self.logger.info("Created redis Publisher {}".format(name + "/buttons_sim"))

        # Threads
        self.simulator_thread = threading.Thread(target = self.simulation_thread)

        from derp_me.client import DerpMeClient
        self.derp_client = DerpMeClient(conn_params=ConnParams.get())

        self.logger.info("Device {} set-up".format(self.name))

    def button_amqp(self, message, meta):
        self.logger.warning("Got button press from amqp " + str(message))
        self.buttons_sim_pub.publish({
            "button": message["button"]
            # "button": "F"
        })

    def start(self):
        for c in self.controllers:
            self.controllers[c].start()

        self.devices_rpc_server.run()
        self.stopped = False
        self.simulator_thread.start()

        r = self.derp_client.lset(
            "stream_sim/state",
            [{
                "state": "ACTIVE",
                "device": self.name,
                "timestamp": time.time()
            }])

    def stop(self):
        for c in self.controllers:
            self.logger.warning("Trying to stop controller {}".format(c))
            self.controllers[c].stop()

        self.logger.warning("Trying to stop devices_rpc_server")
        self.devices_rpc_server.stop()
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

            self.check_detections()

            time.sleep(self.dt)

    def check_detections(self):
        # [text, human, sound, qr, barcode, language, motion, color]
        detections = {
            'type': None,
            'id': None,
            'value': None
        }

        if self.world['robots'][0]['amqp_inform'] is True:
            try:
                v = self.derp_client.lget(self.name.replace("/", ".")[1:] + ".detect", 0, 0)['val'][0]
                if time.time() - v['timestamp'] < 2.5 * self.dt:
                    # Get the closest source
                    v2 = self.derp_client.lget(self.name.replace("/", ".")[1:] + ".detect.source", 0, 0)['val'][0]
                    v["actor_id"] = v2["id"]
                    self.logger.warning("Sending to amqp notifier: " + str(v))
                    self.detects_pub.publish(v)
            except:
                self.logger.debug("AMQP notification failed - detects")
                pass

            # Check for leds
            try:
                v = self.derp_client.lget(self.name.replace("/", ".")[1:] + ".leds", 0, 0)['val'][0]
                if time.time() - v['timestamp'] < 2.5 * self.dt:
                    self.logger.warning("Sending to amqp notifier: " + str(v))
                    self.leds_pub.publish(v)
            except:
                self.logger.debug("AMQP notification failed - leds")
                pass

            # Check for nodes change
            try:
                v = self.derp_client.lget(self.name.replace("/", ".")[1:] + ".execution.nodes", 0, 0)['val'][0]
                if time.time() - v['timestamp'] < 2.5 * self.dt:
                    self.logger.warning("Sending to amqp notifier: " + str(v))
                    self.execution_pub.publish(v)
            except:
                self.logger.debug("AMQP notification failed - execution")
                pass

            # Check for leds
            try:
                v = self.derp_client.lget(self.name.replace("/", ".")[1:] + ".leds.wipe", 0, 0)['val'][0]
                if time.time() - v['timestamp'] < 2.5 * self.dt:
                    self.logger.warning("Sending to amqp notifier: " + str(v))
                    self.leds_wipe_pub.publish(v)
            except:
                self.logger.debug("AMQP notification failed - leds wipe")
                pass

        return
