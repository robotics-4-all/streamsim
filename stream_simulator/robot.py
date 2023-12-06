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

from colorama import Fore, Style, Back
import configparser

from commlib.node import TransportType
import commlib.transports.amqp as acomm
from stream_simulator.connectivity import CommlibFactory

class Robot:
    def __init__(self,
                 configuration = None,
                 world = None,
                 map = None,
                 tick = 0.1):

        self.env_properties = world.env_properties
        world = world.configuration

        self.configuration = configuration
        self.logger = logging.getLogger(__name__)

        self.tf_base = world['tf_base']
        self.tf_declare_rpc = CommlibFactory.getRPCClient(
            rpc_name = self.tf_base + ".declare"
        )

        self.logger.warning("Setting namespace to robot")
        os.environ["TEKTRAIN_NAMESPACE"] = "robot"
        self.namespace = "robot"

        self.common_logging = False

        self.motion_controller = None

        self.raw_name = self.configuration["name"]
        self.name = self.namespace + "." + self.configuration["name"]
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

        self._x = 0
        self._y = 0
        self._theta = 0
        if "starting_pose" in self.configuration:
            pose = self.configuration['starting_pose']
            self._init_x = pose['x'] #* self.resolution
            self._init_y = pose['y'] #* self.resolution
            self._init_theta = pose['theta'] / 180.0 * math.pi
            self.logger.info("Robot {} pose set: {}, {}, {}".format(
                self.name, self._x, self._y, self._theta))

            self._x = self._init_x
            self._y = self._init_y
            self._theta = self._init_theta

        self.step_by_step_execution = self.configuration['step_by_step_execution']
        self.logger.warning("Step by step execution is {}".format(self.step_by_step_execution))

        # Devices set
        self.speak_mode = self.configuration["speak_mode"]
        self.mode = self.configuration["mode"]
        if self.mode not in ["real", "mock", "simulation"]:
            self.logger.error("Selected mode is invalid: {}".format(self.mode))
            exit(1)

        _logger = None
        if self.common_logging is True:
            _logger = self.logger

        self.devices = []
        self.controllers = {}
        self.device_lookup()

        # rpc service which resets the robot pose to the initial given values
        self.reset_pose_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.reset_pose_callback,
            rpc_name = self.name + '.reset_robot_pose'
        )
        self.devices_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.devices_callback,
            rpc_name = self.name + '.nodes_detector.get_connected_devices'
        )
        self.internal_pose_pub = CommlibFactory.getPublisher(
            broker = "redis",
            topic = self.name + ".pose"
        )

        # SIMULATOR ------------------------------------------------------------
        if self.configuration['remote_inform'] is True:
            import commlib

            final_t = self.name
            final_t = final_t[final_t.find(".") + 1:]
            final_top = final_t + ".pose"
            final_dete_top = final_t + ".detect"
            final_leds_top = final_t + ".leds"
            final_leds_wipe_top = final_t + ".leds.wipe"
            final_exec = final_t + ".execution"

            # AMQP Publishers  -----------------------------------------------
            self.pose_pub = CommlibFactory.getPublisher(
                broker = "mqtt",
                topic = final_top
            )
            self.detects_pub = CommlibFactory.getPublisher(
                broker = "mqtt",
                topic = final_dete_top
            )
            self.leds_pub = CommlibFactory.getPublisher(
                broker = "mqtt",
                topic = final_leds_top
            )
            self.leds_wipe_pub = CommlibFactory.getPublisher(
                broker = "mqtt",
                topic = final_leds_wipe_top
            )
            self.execution_pub = CommlibFactory.getPublisher(
                broker = "mqtt",
                topic = final_exec
            )

            # AMQP Subscribers  -----------------------------------------------
            self.buttons_amqp_sub = CommlibFactory.getSubscriber(
                broker = "mqtt",
                topic = final_t + ".buttons",
                callback = self.button_amqp
            )

            if self.step_by_step_execution:
                self.step_by_step_amqp_sub = CommlibFactory.getSubscriber(
                    broker = "mqtt",
                    topic = final_t + ".step_by_step",
                    callback = self.step_by_step_amqp
                )

            # REDIS Publishers  -----------------------------------------------

            self.buttons_sim_pub = CommlibFactory.getPublisher(
                broker = "redis",
                topic = self.configuration["name"] + ".buttons_sim"
            )
            self.next_step_pub = CommlibFactory.getPublisher(
                broker = "redis",
                topic = self.configuration["name"] + ".next_step"
            )

            # REDIS Subscribers -----------------------------------------------

            self.execution_nodes_redis_sub = CommlibFactory.getSubscriber(
                broker = "redis",
                topic = final_t + ".execution.nodes",
                callback = self.execution_nodes_redis
            )
            self.detects_redis_sub = CommlibFactory.getSubscriber(
                broker = "redis",
                topic = final_t + ".detects",
                callback = self.detects_redis
            )
            self.leds_redis_sub = CommlibFactory.getSubscriber(
                broker = "redis",
                topic = final_t + ".leds",
                callback = self.leds_redis
            )
            self.leds_wipe_redis_sub = CommlibFactory.getSubscriber(
                broker = "redis",
                topic = final_t + ".leds.wipe",
                callback = self.leds_wipe_redis
            )

        # Threads
        self.simulator_thread = threading.Thread(target = self.simulation_thread)

        self.logger.info("Device {} set-up".format(self.name))

    def register_controller(self, c):
        if c.name in self.controllers:
            self.logger.error(f"Device {c.name} declared twice")
        else:
            # Do not put button array in devices
            if c.info["type"] != "BUTTON_ARRAY":
                self.devices.append(c.info)

            if c.info["type"] == "BUTTON":
                # Do not put in controllers
                return
            self.controllers[c.name] = c

        if c.info["type"] == "SKID_STEER":
            self.motion_controller = c

        self.logger.info(\
            f"{Fore.WHITE + Style.BRIGHT}{c.name} controller created {Style.RESET_ALL}")

    def device_lookup(self):
        actors = {}
        if "actors" in self.world:
            actors = self.world["actors"]
        p = {
            "name": self.name,
            "mode": self.mode,
            "speak_mode": self.speak_mode,
            "namespace": self.namespace,
            "device_name": self.configuration["name"],
            "logger": self.logger,
            "map": self.map,
            "actors": actors,
            'tf_declare': self.tf_declare_rpc,
            "env_properties": self.env_properties
        }
        str_sim = __import__("stream_simulator")
        str_contro = getattr(str_sim, "controllers")
        map = {
           "ir": getattr(str_contro, "IrController"),
           "sonar": getattr(str_contro, "SonarController"),
           "tof": getattr(str_contro, "TofController"),
           "camera": getattr(str_contro, "CameraController"),
           "skid_steer": getattr(str_contro, "MotionController"),
           "microphone": getattr(str_contro, "MicrophoneController"),
           "cytron_lf": getattr(str_contro, "CytronLFController"),
           "imu": getattr(str_contro, "ImuController"),
           "env": getattr(str_contro, "EnvController"),
           "speaker": getattr(str_contro, "SpeakerController"),
           "leds": getattr(str_contro, "LedsController"),
           "pan_tilt": getattr(str_contro, "PanTiltController"),
           "touch_screen": getattr(str_contro, "TouchScreenController"),
           "encoder": getattr(str_contro, "EncoderController"),
           "gstreamer_server": getattr(str_contro, "GstreamerServerController"),
           "button": getattr(str_contro, "ButtonController"),
           "button_array": getattr(str_contro, "ButtonArrayController"),
           "rfid_reader": getattr(str_contro, "RfidReaderController"),
        }
        for s in self.configuration["devices"]:
            for m in self.configuration["devices"][s]:
                # Handle pose
                if 'pose' not in m:
                    m['pose'] = {'x': 0, 'y': 0, 'theta': None}
                else:
                    if 'x' not in m['pose']:
                        m['pose']['x'] = 0
                    if 'y' not in m['pose']:
                        m['pose']['y'] = 0
                    if 'theta' not in m['pose']:
                        m['pose']['theta'] = None

                self.register_controller(map[s](conf = m, package = p))

        # Handle the buttons
        self.button_configuration = {
                "places": [],
                "pin_nums": [],
                "base_topics": {},
                "direction": "down",
                "bounce": 200,
        }
        buttons = [x for x in self.devices if x["type"] == "BUTTON"]
        for d in buttons:
            self.logger.debug(f"Button {d['id']} added in button_array")
            self.button_configuration["pin_nums"].append(\
                d["sensor_configuration"].get("pin_num"))
            self.button_configuration["places"].append(d["place"])
            self.button_configuration["base_topics"][d["place"]] = d["base_topic"]
        if len(self.button_configuration["pin_nums"]) > 0:
            m = {
                "sensor_configuration": self.button_configuration
            }
            self.register_controller(map["button_array"](conf = m, package = p))

    def leds_redis(self, message):
        self.logger.debug("Got leds from redis " + str(message))
        self.logger.warning(f"{Fore.YELLOW}Sending to amqp notifier: {message}{Style.RESET_ALL}")
        self.leds_pub.publish(message)

    def leds_wipe_redis(self, message):
        self.logger.debug("Got leds wipe from redis " + str(message))
        self.logger.warning(f"{Fore.YELLOW}Sending to amqp notifier: {message}{Style.RESET_ALL}")
        self.leds_wipe_pub.publish(message)

    def execution_nodes_redis(self, message):
        self.logger.debug("Got execution node from redis " + str(message))
        self.logger.warning(f"{Fore.MAGENTA}Sending to amqp notifier: {message}{Style.RESET_ALL}")
        message["device"] = self.raw_name
        self.execution_pub.publish(message)

    def detects_redis(self, message):
        self.logger.warning("Got detect from redis " + str(message))
        # Wait for source
        done = False
        while not done:
            try:
                v2 = "" ## Change this!
                # v2 = CommlibFactory.derp_client.lget(self.name + ".detect.source", 0, 0)['val'][0]
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

    def button_amqp(self, message):
        self.logger.warning("Got button press from amqp " + str(message))
        self.buttons_sim_pub.publish({
            "button": message["button"]
        })

    def step_by_step_amqp(self, message):
        self.logger.info(f"Got next step from amqp")
        self.next_step_pub.publish({})

    def start(self):
        for c in self.controllers:
            self.controllers[c].start()

        if self.configuration['remote_inform'] is True:
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

    def stop(self):
        for c in self.controllers:
            self.logger.warning("Trying to stop controller {}".format(c))
            self.controllers[c].stop()

        if self.configuration['amqp_inform'] is True:
            self.buttons_sub.stop()
            if self.step_by_step_execution:
                self.step_by_step_sub.stop()

        self.logger.warning("Trying to stop devices_rpc_server")
        self.devices_rpc_server.stop()
        self.logger.warning("Trying to stop reset_pose_rpc_server")
        self.reset_pose_rpc_server.stop()

        self.logger.warning("Trying to stop simulation_thread")
        self.stopped = True

    def devices_callback(self, message):
        self.logger.warning("Getting devices")
        timestamp = time.time()
        secs = int(timestamp)
        nanosecs = int((timestamp-secs) * 10**(9))
        return {
                "devices": self.devices,
                "timestamp": time.time()
        }

    def reset_pose_callback(self, message):
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
            self.error_log_msg = "Out of bounds - negative x or y"
            self.logger.error("{}: {}".format(self.name, self.error_log_msg))
            return True
        if x / self.resolution > self.width or y / self.resolution > self.height:
            self.error_log_msg = "Out of bounds"
            self.logger.error("{}: {}".format(self.name, self.error_log_msg))
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
                    self.error_log_msg = "Crashed on a Wall"
                    self.logger.error("{}: {}".format(self.name, self.error_log_msg))
                    return True
        elif y_i == y_i_p:
            for i in range(x_i, x_i_p):
                if self.map[i, y_i] == 1:
                    self.error_log_msg = "Crashed on a Wall"
                    self.logger.error("{}: {}".format(self.name, self.error_log_msg))
                    return True
        else: # we have a straight line
            th = math.atan2(y_i_p - y_i, x_i_p - x_i)
            dist = math.hypot(x_i_p - x_i, y_i_p - y_i)
            d = 0
            while d < dist:
                xx = x_i + d * math.cos(th)
                yy = y_i + d * math.sin(th)
                if self.map[int(xx), int(yy)] == 1:
                    self.error_log_msg = "Crashed on a Wall"
                    self.logger.error("{}: {}".format(self.name, self.error_log_msg))
                    return True
                d += 1.0

        return False

    def dispatch_pose_local(self):
        # Send initial pose
        self.internal_pose_pub.publish({
            "x": self._x,
            "y": self._y,
            "theta": self._theta,
            "resolution": self.resolution,
            "name": self.name
        })

    def simulation_thread(self):
        t = time.time()

        self.dispatch_pose_local()
        while self.stopped is False:
            if self.motion_controller is not None:
                # update time interval
                dt = time.time() - t
                t = time.time()

                prev_x = self._x
                prev_y = self._y
                prev_th = self._theta

                if self.motion_controller._angular == 0:
                    self._x += self.motion_controller._linear * dt * math.cos(self._theta)
                    self._y += self.motion_controller._linear * dt * math.sin(self._theta)
                else:
                    arc = self.motion_controller._linear / self.motion_controller._angular
                    self._x += - arc * math.sin(self._theta) + \
                        arc * math.sin(self._theta + dt * self.motion_controller._angular)
                    self._y -= - arc * math.cos(self._theta) + \
                        arc * math.cos(self._theta + dt * self.motion_controller._angular)
                self._theta += self.motion_controller._angular * dt

                xx = float("{:.2f}".format(self._x))
                yy = float("{:.2f}".format(self._y))
                theta2 = float("{:.2f}".format(self._theta))

                if self._x != prev_x or self._y != prev_y or self._theta != prev_th:
                    if self.configuration['amqp_inform'] is True:
                        self.logger.info("AMQP pose updated")
                        self.pose_pub.publish({
                            "x": xx,
                            "y": yy,
                            "theta": theta2,
                            "resolution": self.resolution
                        })
                    self.logger.info(f"{self.raw_name}: New pose: {xx}, {yy}, {theta2}")

                    # Send internal pose for distance sensors
                    self.internal_pose_pub.publish({
                        "x": xx,
                        "y": yy,
                        "theta": theta2,
                        "resolution": self.resolution,
                        "name": self.name
                    })

                if self.check_ok(self._x, self._y, prev_x, prev_y):
                    self._x = prev_x
                    self._y = prev_y
                    self._theta = prev_th

                    # notify ui about the error in robot's position
                    CommlibFactory.notify_ui(
                        type = "new_message",
                        data = {
                            "type": "logs",
                            "message": f"Robot: {self.raw_name} {self.error_log_msg}"
                        }
                    )

            time.sleep(self.dt)
