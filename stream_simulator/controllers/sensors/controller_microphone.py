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

from stream_simulator.base_classes import BaseThing

class MicrophoneController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        id = "d_microphone_" + str(BaseThing.id + 1)
        name = id
        self.name = name
        if 'name' in conf:
            name = conf['name']

        _category = "sensor"
        _class = "audio"
        _subclass = "microphone"
        _pack = package["name"]

        # BaseThing initialization
        super().__init__(id)

        info = {
            "type": "MICROPHONE",
            "brand": "usb_mic",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": name,
            "place": conf["place"],
            "id": "id_" + str(id),
            "enabled": True,
            "orientation": conf["orientation"],
            "queue_size": 0,
            "mode": package["mode"],
            "speak_mode": package["speak_mode"],
            "namespace": package["namespace"],
            "sensor_configuration": conf["sensor_configuration"],
            "device_name": package["device_name"],
            "actors": package["actors"],
            "categorization": {
                "host_type": "robot",
                "place": _pack.split(".")[-1],
                "category": _category,
                "class": _class,
                "subclass": [_subclass],
                "name": name
            }
        }

        self.info = info
        self.base_topic = info["base_topic"]
        self.name = info["name"]
        self.conf = info["sensor_configuration"]

        self.set_tf_communication(package)

        # tf handling
        tf_package = {
            "type": "robot",
            "subtype": {
                "category": _category,
                "class": _class,
                "subclass": [_subclass]
            },
            "pose": conf["pose"],
            "base_topic": info['base_topic'],
            "name": self.name
        }
        tf_package['host'] = package['device_name']
        tf_package['host_type'] = 'robot'
        if 'host' in conf:
            tf_package['host'] = conf['host']
            tf_package['host_type'] = 'pan_tilt'
        
        self.tf_declare_rpc.call(tf_package)

        self.blocked = False

        # merge actors
        self.actors = []
        for i in info["actors"]:
            for h in info["actors"][i]:
                k = h
                h["type"] = i
                self.actors.append(k)

        self.record_action_server = self.commlib_factory.getActionServer(
            callback = self.on_goal,
            action_name = self.base_topic + ".record"
        )
        self.listen_action_server = self.commlib_factory.getActionServer(
            callback = self.on_goal_listen,
            action_name = self.base_topic  + ".listen"
        )
        self.enable_rpc_server = self.commlib_factory.getRPCService(
            callback = self.enable_callback,
            rpc_name = self.base_topic  + ".enable"
        )
        self.disable_rpc_server = self.commlib_factory.getRPCService(
            callback = self.disable_callback,
            rpc_name = self.base_topic  + ".disable"
        )

        self.record_pub = self.commlib_factory.getPublisher(
            topic = self.base_topic  + ".record.notify"
        )

        self.detect_speech_sub = self.commlib_factory.getSubscriber(
            topic = self.base_topic  + ".speech_detected",
            callback = self.speech_detected
        )

    def speech_detected(self, message):
        source = message["speaker"]
        text = message["text"]
        language = message["language"]
        self.logger.info(f"Speech detected from {source} [{language}]: {text}")

    def load_wav(self, path):
        # Read from file
        import wave
        import os
        from pathlib import Path
        dirname = Path(__file__).resolve().parent
        fil = str(dirname) + '/../../resources/' + path
        self.logger.info("Reading sound from " + fil)
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
        return source

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

        self.record_pub.publish({
            "duration": duration
        })

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
            # Ask tf for proximity sound sources or humans
            res = self.tf_affection_rpc.call({
                'name': self.name
            })
            # Get the closest:
            clos = None
            clos_d = 100000.0
            for x in res:
                if res[x]['distance'] < clos_d:
                    clos = x
                    clos_d = res[x]['distance']

            wav = "Silent.wav"
            if res[clos]['type'] == 'sound_source':
                if res[clos]['info']['language'] == 'EL':
                    wav = "greek_sentence.wav"
                else:
                    wav = "english_sentence.wav"
            elif res[clos]['type'] == "human":
                if res[clos]['info']["sound"] == 1:
                    if res[clos]['info']["language"] == "EL":
                        wav = "greek_sentence.wav"
                    else:
                        wav = "english_sentence.wav"

            now = time.time()
            self.logger.info(f"Recording... {res[clos]['type']}, {res[clos]['info']}")
            while time.time() - now < duration:
                if goalh.cancel_event.is_set():
                    self.logger.info("Cancel got")
                    self.blocked = False
                    return ret
                time.sleep(0.1)
            self.logger.info("Recording done")

            ret["record"] = self.load_wav(wav)
            ret["volume"] = 100

        self.logger.info("{} recording finished".format(self.name))
        self.blocked = False
        return ret

    def on_goal_listen(self, goalh):
        self.logger.info("{} listening started".format(self.name))
        if self.info["enabled"] == False:
            return {}

        # Concurrent speaker calls handling
        while self.blocked:
            time.sleep(0.1)
        self.logger.info("Microphone unlocked")
        self.blocked = True

        # NOTE!!! This is a dummy implementation
        text = "IMPLEMENT THIS FUNCTIONALITY!"

        try:
            duration = goalh.data["duration"]
            language = goalh.data["language"]
        except Exception as e:
            self.logger.error("{} goal had no duration and language as parameter".format(self.name))

        self.logger.info("Listening finished: " + str(text))
        self.blocked = False
        return {'text': text}

    def enable_callback(self, message):
        self.info["enabled"] = True
        return {"enabled": True}

    def disable_callback(self, message):
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        pass

    def stop(self):
        self.commlib_factory.stop()
