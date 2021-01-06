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
from stream_simulator.connectivity import CommlibFactory
from stream_simulator.base_classes import BaseThing

class SpeakerController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = Logger(conf["name"])
        else:
            self.logger = package["logger"]

        super(self.__class__, self).__init__()
        id = BaseThing.id

        info = {
            "type": "SPEAKERS",
            "brand": "usb_speaker",
            "base_topic": package["name"] + ".actuator.audio.speaker.usb_speaker.d" + str(id),
            "name": "speaker_" + str(id),
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
            "endpoints":{
                "enable": "rpc",
                "disable": "rpc",
                "play": "action",
                "speak": "action"
            },
            "data_models": []
        }

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]

        # tf handling
        tf_package = {
            "type": "robot",
            "subtype": "speaker",
            "pose": conf["pose"],
            "base_topic": info['base_topic'],
            "name": self.name
        }
        tf_package['host'] = package['device_name']
        tf_package['host_type'] = 'robot'
        package["tf_declare"].call(tf_package)

        self.global_volume = None
        self.blocked = False

        if self.info["mode"] == "real":
            from pidevices import Speaker
            self.speaker = Speaker(dev_name = self.conf["dev_name"], name = self.name, max_data_length = self.conf["max_data_length"])

            if self.info["speak_mode"] == "espeak":
                from espeakng import ESpeakNG

                self.esng = ESpeakNG()
                #self.esng.pitch = 32
                #self.esng.speed = 150

            elif self.info["speak_mode"] == "google":
                import os
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/pi/google_ttsp.json"

                from google.cloud import texttospeech
                self.client = texttospeech.TextToSpeechClient()
                self.audio_config = texttospeech.AudioConfig(
                    audio_encoding = texttospeech.AudioEncoding.LINEAR16,
                    sample_rate_hertz = 44100)

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

        # Try to get global volume:
        res = CommlibFactory.derp_client.get(
            "device.global_volume.persistent",
            persistent = True
        )
        if res['val'] is not None:
            self.global_volume = int(res['val'])
            self.set_global_volume()

    def on_goal_speak(self, goalh):
        self.logger.info("{} speak started".format(self.name))
        if self.info["enabled"] == False:
            return {}

        # Concurrent speaker calls handling
        while self.blocked:
            time.sleep(0.1)
        self.logger.info("Speaker unlocked")
        self.blocked = True

        try:
            texts = goalh.data["text"]
            volume = goalh.data["volume"]
            if self.global_volume is not None:
                volume = self.global_volume
                self.logger.info(f"{Fore.MAGENTA}Volume forced to {self.global_volume}{Style.RESET_ALL}")
            language = goalh.data["language"]
        except Exception as e:
            self.logger.error("{} wrong parameters: {}".format(self.name, ))

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

        else: # The real deal
            if self.info["speak_mode"] == "espeak":
                path = "/home/pi/tektrain-robot-sw/wav_sounds/file_example_WAV_1MG.wav"
                self.esng.voice = language
                self.esng._espeak_exe([texts, "-w", path], sync = True)
                self.speaker.volume = volume
                self.speaker.async_write(path, file_flag=True)
                while self.speaker.playing:
                    if goalh.cancel_event.is_set():
                        self.logger.info("Cancel got")
                        self.blocked = False
                        return ret
                    time.sleep(0.1)
            else: # google
                from google.cloud import texttospeech
                self.voice = texttospeech.VoiceSelectionParams(\
                    language_code = language,\
                    ssml_gender = texttospeech.SsmlVoiceGender.FEMALE)

                synthesis_input = texttospeech.SynthesisInput(text = texts)
                response = self.client.synthesize_speech(input = synthesis_input, voice = self.voice, audio_config = self.audio_config)

                self.speaker.volume = volume
                self.speaker.async_write(response.audio_content, file_flag=False)
                while self.speaker.playing:
                    print("Speaking...")
                    time.sleep(0.1)

        self.logger.info("{} Speak finished".format(self.name))
        self.blocked = False
        return ret

    def google_speak(self, language = None, texts = None, volume = None):
        from google.cloud import texttospeech
        self.voice = texttospeech.VoiceSelectionParams(\
            language_code = language,\
            ssml_gender = texttospeech.SsmlVoiceGender.FEMALE)

        synthesis_input = texttospeech.SynthesisInput(text = texts)
        response = self.client.synthesize_speech(input = synthesis_input, voice = self.voice, audio_config = self.audio_config)

        self.speaker.volume = volume
        self.speaker.async_write(response.audio_content, file_flag=False)
        while self.speaker.playing:
            print("Speaking...")
            time.sleep(0.1)

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

        else: # The real deal
            source = base64.b64decode(string.encode("ascii"))
            self.speaker.async_write(source, file_flag = False)
            while self.speaker.playing:
                print("Playing...")
                time.sleep(0.1)

        self.logger.info("{} Playing finished".format(self.name))
        self.blocked = False
        return ret

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
            self.derp_client.set(
                "device.global_volume.persistent",
                self.global_volume,
                persistent = True
            )
            self.logger.info(f"{Fore.MAGENTA}Derpme updated for global volume{Style.RESET_ALL}")
        except Exception as e:
            err = f"Could not store volume in persistent derp me"
            self.logger.error(err)
            raise ValueError(err)

    def set_global_volume_callback(self, message, meta):
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

    def enable_callback(self, message, meta):
        self.info["enabled"] = True
        return {"enabled": True}

    def disable_callback(self, message, meta):
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
