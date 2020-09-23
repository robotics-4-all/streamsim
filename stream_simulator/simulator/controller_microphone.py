#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random
import base64

from colorama import Fore, Style

from commlib.logger import Logger

from .conn_params import ConnParams
if ConnParams.type == "amqp":
    from commlib.transports.amqp import ActionServer, RPCService, Subscriber
elif ConnParams.type == "redis":
    from commlib.transports.redis import ActionServer, RPCService, Subscriber

class MicrophoneController:
    def __init__(self, info = None, logger = None):
        if logger is None:
            self.logger = Logger(info["name"] + "-" + info["id"])
        else:
            self.logger = logger

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]

        self.blocked = False

        # merge actors
        self.actors = []
        for i in info["actors"]:
            for h in info["actors"][i]:
                k = h
                h["type"] = i
                self.actors.append(k)

        if self.info["mode"] == "real":
            from pidevices import Microphone
            self.sensor = Microphone(dev_name=self.conf["dev_name"],
                                     channels=self.conf["channels"],
                                     name=self.name,
                                     max_data_length=self.conf["max_data_length"])
            ## https://github.com/robotics-4-all/tektrain-ros-packages/blob/master/ros_packages/robot_hw_interfaces/microphone_hw_interface/microphone_hw_interface/microphone_hw_interface.py

        self.memory = 100 * [0]

        _topic = info["base_topic"] + "/record"
        self.record_action_server = ActionServer(
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

        if self.info["mode"] == "simulation":
            _topic = self.info['device_name'] + "/pose"
            self.robot_pose_sub = Subscriber(conn_params=
                ConnParams.get("redis"),
                topic = _topic,
                on_message = self.robot_pose_update)
            self.logger.info(f"{Fore.GREEN}Created redis Subscriber {_topic}{Style.RESET_ALL}")
            self.robot_pose_sub.run()

        from derp_me.client import DerpMeClient
        self.derp_client = DerpMeClient(conn_params=ConnParams.get("redis"))

    def robot_pose_update(self, message, meta):
        self.robot_pose = message

    def on_goal(self, goalh):
        self.logger.info("{} recording started".format(self.name))
        if self.info["enabled"] == False:
            return {}

        # Concurrent speaker calls handling
        while self.blocked:
            time.sleep(0.1)
        self.logger.info("Microphone unlocked")
        self.blocked = True

        try:
            duration = goalh.data["duration"]
        except Exception as e:
            self.logger.error("{} goal had no duration as parameter".format(self.name))

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
            "record": "",
            "volume": 0
        }
        if self.info["mode"] == "mock":
            now = time.time()
            while time.time() - now < duration:
                self.logger.info("Recording...")
                if goalh.cancel_event.is_set():
                    self.logger.info("Cancel got")
                    self.blocked = False
                    return ret
                time.sleep(0.1)

            ret["record"] = base64.b64encode(b'0x55').decode("ascii")
            ret["volume"] = 100

        elif self.info["mode"] == "simulation":
            # Read from file
            import wave
            import os
            dirname = os.path.dirname(__file__)

            x = self.robot_pose["x"]
            y = self.robot_pose["y"]
            th = self.robot_pose["theta"]
            reso = self.robot_pose["resolution"]

            findings = {
                "humans": [],
                "sound_sources": []
            }
            closest = "empty"
            closest_dist = 1000000000000
            closest_full = None

            # Find actors
            for h in self.actors:
                if h["type"] not in ["humans", "sound_sources"]:
                    continue

                xx = h["x"] * reso
                yy = h["y"] * reso
                d = math.hypot(xx - x, yy - y)
                self.logger.info("dist to {}: {}".format(h["id"], d))
                if d <= 2.0:
                    # In range - check if in the same semi-plane
                    # xt = x + math.cos(th) * d
                    # yt = y + math.sin(th) * d
                    # thres = d * 1.4142
                    # self.logger.info("\tThres to {}: {} / {}".format(h["id"], math.hypot(xt - xx, yt - yy), thres))
                    # if math.hypot(xt - xx, yt - yy) < thres:
                    # We got a winner!
                    findings[h["type"]].append(h)
                    if d < closest_dist:
                        closest = h["type"]
                        closest_full = h

            for i in findings:
                for j in findings[i]:
                    self.logger.info("Microphone detected: " + str(j))
            self.logger.info("Closest detection: {}".format(closest))

            cl_f = closest_full
            if closest == "empty":
                cl_f = "empty"
            self.derp_client.lset(
                self.info["namespace"][1:] + "." + self.info["device_name"] + ".detect.source",
                [cl_f]
            )
            print(f"Derp me updated with {cl_f}")


            # Check if human is the closest:
            wav = "Silent.wav"
            if closest == "humans":
                if closest_full["sound"] == 1:
                    if closest_full["lang"] == "EL":
                        wav = "greek_sentence.wav"
                    else:
                        wav = "english_sentence.wav"

            if closest == "sound_sources":
                if closest_full["lang"] == "EL":
                    wav = "greek_sentence.wav"
                else:
                    wav = "english_sentence.wav"

            fil = dirname + '/resources/' + wav
            self.logger.warning("Reading sound from " + fil)
            f = wave.open(fil, 'rb')
            channels = f.getnchannels()
            framerate = f.getframerate()
            sample_width = f.getsampwidth()
            data = bytearray()
            sample = f.readframes(256)
            while sample:
                for s in sample:
                    data.append(s)
                sample = f.readframes(256)
            f.close()
            source = base64.b64encode(data).decode("ascii")
            # file read

            now = time.time()
            self.logger.info("Recording...")
            while time.time() - now < duration:
                if goalh.cancel_event.is_set():
                    self.logger.info("Cancel got")
                    self.blocked = False
                    return ret
                time.sleep(0.1)
            self.logger.info("Recording done")

            ret["record"] = source
            ret["volume"] = 100

        else: # The real deal
            self.sensor.async_read(secs = duration, volume = 100, framerate = self.conf["framerate"])
            now = time.time()
            while time.time() - now < duration + 0.2:
                if goalh.cancel_event.is_set():
                    self.logger.info("Cancel got")
                    self.blocked = False
                    return ret
                time.sleep(0.1)
            ret["record"] = base64.b64encode(self.sensor.record).decode("ascii")

        self.logger.info("{} recording finished".format(self.name))
        self.blocked = False
        return ret

    def enable_callback(self, message, meta):
        self.info["enabled"] = True
        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        self.record_action_server.run()
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

    def stop(self):
        self.record_action_server._goal_rpc.stop()
        self.record_action_server._cancel_rpc.stop()
        self.record_action_server._result_rpc.stop()
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()

    def memory_write(self, data):
        del self.memory[-1]
        self.memory.insert(0, data)
