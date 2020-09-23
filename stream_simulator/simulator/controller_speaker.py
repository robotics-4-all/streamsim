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
    from commlib.transports.amqp import ActionServer, RPCService
elif ConnParams.type == "redis":
    from commlib.transports.redis import ActionServer, RPCService

class SpeakerController:
    def __init__(self, info = None, logger = None):
        if logger is None:
            self.logger = Logger(info["name"] + "-" + info["id"])
        else:
            self.logger = logger

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]

        self.global_volume = None
        self.blocked = False

        self.memory = 100 * [0]

        if self.info["mode"] == "real":
            from pidevices import Speaker
            self.speaker = Speaker(dev_name = self.conf["dev_name"], name = self.name, max_data_length = self.conf["max_data_length"])

            if self.info["speak_mode"] == "espeak":
                from espeakng import ESpeakNG
                self.esng = ESpeakNG()
            elif self.info["speak_mode"] == "google":
                import os
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/pi/google_ttsp.json"

                from google.cloud import texttospeech
                self.client = texttospeech.TextToSpeechClient()
                self.audio_config = texttospeech.AudioConfig(
                    audio_encoding = texttospeech.AudioEncoding.LINEAR16,
                    sample_rate_hertz = 44100)

        _topic = info["base_topic"] + "/play"
        self.play_action_server = ActionServer(
            conn_params=ConnParams.get("redis"),
            on_goal=self.on_goal_play,
            action_name=_topic)
        self.logger.info(f"{Fore.GREEN}Created redis ActionServer {_topic}{Style.RESET_ALL}")

        _topic = info["base_topic"] + "/speak"
        self.speak_action_server = ActionServer(
            conn_params=ConnParams.get("redis"),
            on_goal=self.on_goal_speak,
            action_name=_topic)
        self.logger.info(f"{Fore.GREEN}Created redis ActionServer {_topic}{Style.RESET_ALL}")

        _topic = "device.global.volume"
        self.global_volume_rpc_server = RPCService(
            conn_params=ConnParams.get("redis"),
            on_request=self.set_global_volume_callback,
            rpc_name=_topic)
        self.logger.info(f"{Fore.GREEN}Created redis RPCService {_topic}{Style.RESET_ALL}")

        self.enable_rpc_server = RPCService(
            conn_params=ConnParams.get("redis"),
            on_request=self.enable_callback,
            rpc_name=info["base_topic"] + "/enable")
        self.disable_rpc_server = RPCService(
            conn_params=ConnParams.get("redis"),
            on_request=self.disable_callback,
            rpc_name=info["base_topic"] + "/disable")

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
                path = "/home/pi/manos_espeak.wav"
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
            import alsaaudio
            m = alsaaudio.Mixer("PCM")
            m.setvolume(int(self.global_volume))
            self.logger.info(f"{Fore.MAGENTA}Alsamixer audio set to {self.global_volume}{Style.RESET_ALL}")
            return {}
        except Exception as e:
            err = f"Something went wrong with global volume set: {str(e)}. Is the alsaaudio python library installed?"
            self.logger.error(err)
            raise ValueError(err)

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

    def memory_write(self, data):
        del self.memory[-1]
        self.memory.insert(0, data)
