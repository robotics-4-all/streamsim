#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging
from pathlib import Path
import base64
import wave

from stream_simulator.base_classes import BaseThing

class EnvMicrophoneController(BaseThing):
    def __init__(self,
                 conf = None,
                 package = None
                 ):

        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        super().__init__(conf["name"])

        _type = "MICROPHONE"
        _category = "sensor"
        _class = "audio"
        _subclass = "microphone"

        _name = conf["name"]
        _pack = package["base"]
        _place = conf["place"]
        _namespace = package["namespace"]
        id = "d_" + str(BaseThing.id)
        info = {
            "type": _type,
            "base_topic": f"{_namespace}.{_pack}.{_place}.{_category}.{_class}.{_subclass}.{_name}",
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

        self.info = info
        self.name = info["name"]
        self.base_topic = info["base_topic"]
        self.mode = info["mode"]
        self.place = info["conf"]["place"]
        self.pose = info["conf"]["pose"]

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
            "name": self.name,
            "namespace": _namespace
        }

        self.host = None
        if 'host' in info['conf']:
            self.host = info['conf']['host']
            tf_package['host'] = self.host
            # No other host type is available for env_devices
            tf_package['host_type'] = 'pan_tilt'

        self.set_communication_layer(package)

        self.tf_declare_rpc.call(tf_package)

        self.blocked = False

    def set_communication_layer(self, package):
        self.set_tf_communication(package)
        self.set_enable_disable_rpcs(self.base_topic, self.enable_callback, self.disable_callback)
        
        self.record_action_server = self.commlib_factory.getActionServer(
            callback = self.on_goal_record,
            action_name = self.base_topic + ".record"
        )
        self.record_pub = self.commlib_factory.getPublisher(
            topic = self.base_topic + ".record.notify"
        )
        self.detect_speech_sub = self.commlib_factory.getSubscriber(
            topic = self.base_topic + ".speech_detected",
            callback = self.speech_detected
        )

    def speech_detected(self, message):
        source = message["speaker"]
        text = message["text"]
        language = message["language"]
        self.logger.info(f"Speech detected from {source} [{language}]: {text}")

    def enable_callback(self, message):
        self.info["enabled"] = True

        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        self.record_action_server.run()

        return {"enabled": True}

    def disable_callback(self, message):
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        self.record_action_server.run()

    def stop(self):
        self.info["enabled"] = False
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()

        self.record_action_server._goal_rpc.stop()
        self.record_action_server._cancel_rpc.stop()
        self.record_action_server._result_rpc.stop()

    def on_goal_record(self, goalh):
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

        ret = {
            'timestamp': time.time()
        }
        if self.info["mode"] == "mock":
            now = time.time()
            self.logger.info("Recording...")
            while time.time() - now < duration:
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
            clos_type = None
            clos_info = None
            clos_d = 100000.0
            for x in res:
                if res[x]['distance'] < clos_d:
                    clos = x
                    clos_d = res[x]['distance']

            wav = "Silent.wav"
            if clos is None:
                pass
            elif res[clos]['type'] == 'sound_source':
                clos_type = 'sound_source'
                clos_info = res[clos]['info']
                if res[clos]['info']['language'] == 'EL':
                    wav = "greek_sentence.wav"
                else:
                    wav = "english_sentence.wav"
            elif res[clos]['type'] == "human":
                clos_type = 'human'
                clos_info = res[clos]['info']
                if res[clos]['info']["sound"] == 1:
                    if res[clos]['info']["language"] == "EL":
                        wav = "greek_sentence.wav"
                    else:
                        wav = "english_sentence.wav"

            now = time.time()
            self.logger.info("Recording... %s, %s", clos_type, clos_info)
            while time.time() - now < duration:
                if goalh.cancel_event.is_set():
                    self.logger.info("Cancel got")
                    self.blocked = False
                    return ret
                time.sleep(0.1)
            self.logger.info("Recording done")

            ret["record"] = self.load_wav(wav)
            ret["volume"] = 100

        self.logger.info("%s recording finished", self.name)
        self.blocked = False
        return ret

    def load_wav(self, path):
        # Read from file
        dirname = Path(__file__).resolve().parent
        fil = str(dirname) + '/../../resources/' + path
        self.logger.info("Reading sound from %s", fil)
        f = wave.open(fil, 'rb')
        data = bytearray()
        sample = f.readframes(256)
        while sample:
            for s in sample:
                data.append(s)
            sample = f.readframes(256)
        f.close()
        source = base64.b64encode(data).decode("ascii")
        return source
