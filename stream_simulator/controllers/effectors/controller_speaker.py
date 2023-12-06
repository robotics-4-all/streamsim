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

from stream_simulator.connectivity import CommlibFactory
from stream_simulator.base_classes import BaseThing

class SpeakerController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        super(self.__class__, self).__init__()
        id = "d_" + str(BaseThing.id)
        name = id
        if 'name' in conf:
            name = conf['name']
        _category = "actuator"
        _class = "audio"
        _subclass = "speaker"
        _pack = package["name"]

        info = {
            "type": "SPEAKERS",
            "brand": "usb_speaker",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": name,
            "place": conf["place"],
            "id": id,
            "enabled": True,
            "orientation": conf["orientation"],
            "queue_size": 0,
            "mode": package["mode"],
            "speak_mode": package["speak_mode"],
            "namespace": package["namespace"],
            "sensor_configuration": conf["sensor_configuration"],
            "device_name": package["device_name"],
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
        self.name = info["name"]
        self.conf = info["sensor_configuration"]

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
        package["tf_declare"].call(tf_package)

        self.global_volume = None
        self.blocked = False

        self.play_action_server = CommlibFactory.getActionServer(
            broker = "redis",
            callback = self.on_goal_play,
            action_name = info["base_topic"] + ".play"
        )
        self.speak_action_server = CommlibFactory.getActionServer(
            broker = "redis",
            callback = self.on_goal_speak,
            action_name = info["base_topic"] + ".speak"
        )
        self.global_volume_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.set_global_volume_callback,
            rpc_name = "device.global.volume"
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

        self.play_pub = CommlibFactory.getPublisher(
            topic = info["base_topic"] + ".play.notify"
        )
        self.speak_pub = CommlibFactory.getPublisher(
            topic = info["base_topic"] + ".speak.notify"
        )

    def on_goal_speak(self, goalh):
        self.logger.info("{} speak started".format(self.name))
        if self.info["enabled"] == False:
            return {}

        # Concurrent speaker calls handling
        while self.blocked:
            time.sleep(0.1)
        self.logger.info("Speaker unlocked")
        self.blocked = True

        CommlibFactory.notify_ui(
            type = "effector_command",
            data = {
                "name": self.name,
                "value": {
                    "text": goalh.data["text"]
                }
            }
        )

        try:
            texts = goalh.data["text"]
            volume = goalh.data["volume"]
            if self.global_volume is not None:
                volume = self.global_volume
                self.logger.info(f"{Fore.MAGENTA}Volume forced to {self.global_volume}{Style.RESET_ALL}")
            language = goalh.data["language"]
        except Exception as e:
            self.logger.error("{} wrong parameters: {}".format(self.name, ))

        self.speak_pub.publish({
            "text": texts,
            "volume": volume,
            "language": language,
            "speaker": self.name
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
            }
        }
        if self.info["mode"] == "mock":
            now = time.time()
            self.logger.info("Speaking...")
            while time.time() - now < 5:
                if goalh.cancel_event.is_set():
                    self.logger.info("Cancel got")
                    self.blocked = False
                    return ret
                time.sleep(0.1)
            self.logger.info("Speaking done")

        elif self.info["mode"] == "simulation":
            now = time.time()
            self.logger.info("Speaking...")
            while time.time() - now < 5:
                if goalh.cancel_event.is_set():
                    self.logger.info("Cancel got")
                    self.blocked = False
                    return ret
                time.sleep(0.1)
            self.logger.info("Speaking done")

        self.logger.info("{} Speak finished".format(self.name))
        self.blocked = False
        return ret

    def on_goal_play(self, goalh):
        self.logger.info("{} play started".format(self.name))
        if self.info["enabled"] == False:
            return {}

        # Concurrent speaker calls handling
        while self.blocked:
            time.sleep(0.1)
        self.logger.info("Speaker unlocked")
        self.blocked = True

        try:
            string = goalh.data["string"]
            volume = goalh.data["volume"]
            if self.global_volume is not None:
                volume = self.global_volume
                self.logger.info(f"{Fore.MAGENTA}Volume forced to {self.global_volume}{Style.RESET_ALL}")
        except Exception as e:
            self.logger.error("{} wrong parameters: {}".format(self.name, ))

        self.play_pub.publish({
            "text": string,
            "volume": volume
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
            }
        }
        if self.info["mode"] == "mock":
            now = time.time()
            self.logger.info("Playing...")
            while time.time() - now < 5:
                if goalh.cancel_event.is_set():
                    self.logger.info("Cancel got")
                    self.blocked = False
                    return ret
                time.sleep(0.1)
            self.logger.info("Playing done")

        elif self.info["mode"] == "simulation":
            now = time.time()
            self.logger.info("Playing...")
            while time.time() - now < 5:
                if goalh.cancel_event.is_set():
                    self.logger.info("Cancel got")
                    self.blocked = False
                    return ret
                time.sleep(0.1)
            self.logger.info("Playing done")

        self.logger.info("{} Playing finished".format(self.name))
        self.blocked = False
        return ret

    # check if this is needed
    def set_global_volume(self):
        try:
            import alsaaudio
            m = alsaaudio.Mixer("PCM")
            m.setvolume(int(self.global_volume))
            self.logger.info(f"{Fore.MAGENTA}Alsamixer audio set to {self.global_volume}{Style.RESET_ALL}")
        except Exception as e:
            err = f"Something went wrong with global volume set: {str(e)}. Is the alsaaudio python library installed?"
            self.logger.error(err)
            raise ValueError(err)

        try:
            #Write global volume to persistent storage
            CommlibFactory.derp_client.set(
                "device.global_volume.persistent",
                self.global_volume,
                persistent = True
            )
            self.logger.info(f"{Fore.MAGENTA}Derpme updated for global volume{Style.RESET_ALL}")
        except Exception as e:
            err = f"Could not store volume in persistent derp me"
            self.logger.error(err)
            raise ValueError(err)

    def set_global_volume_callback(self, message):
        try:
            _vol = message["volume"]
            if _vol < 0 or _vol > 100:
                err = f"Global volume must be between 0 and 100"
                self.logger.error(err)
                raise ValueError(err)
            self.global_volume = _vol
            self.logger.info(f"{Fore.MAGENTA}Global volume set to {self.global_volume}{Style.RESET_ALL}")
        except Exception as e:
            err = f"Global volume message is erroneous: {message}"
            self.logger.error(err)
            raise ValueError(err)

        try:
            self.set_global_volume()
        except Exception as e:
            err = f"Something went wrong with global volume set: {str(e)}"
            self.logger.error(err)
            raise ValueError(err)

        return {}

    def enable_callback(self, message):
        self.info["enabled"] = True
        return {"enabled": True}

    def disable_callback(self, message):
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        self.play_action_server.run()
        self.speak_action_server.run()
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()
        self.global_volume_rpc_server.run()

    def stop(self):
        self.play_action_server._goal_rpc.stop()
        self.play_action_server._cancel_rpc.stop()
        self.play_action_server._result_rpc.stop()
        self.speak_action_server._goal_rpc.stop()
        self.speak_action_server._cancel_rpc.stop()
        self.speak_action_server._result_rpc.stop()
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()
        self.global_volume_rpc_server.stop()
