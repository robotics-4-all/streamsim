#!/usr/bin/python
# -*- coding: utf-8 -*-

from commlib.logger import Logger
from stream_simulator.controllers import MicrophoneController

class MicrophoneConf:
    logger = Logger("MicrophoneConf")

    @staticmethod
    def configure(id = 0,
                  conf = None,
                  package = None):

        msg = {
            "type": "MICROPHONE",
            "brand": "usb_mic",
            "base_topic": package["name"] + ".sensor.audio.microphone.d" + str(id),
            "name": "microphone_" + str(id),
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
            "endpoints":{
                "enable": "rpc",
                "disable": "rpc",
                "record": "action"
            },
            "data_models": {
                "record": ["record"]
            }
        }

        MicrophoneConf.logger.info(f"Creating controller for {msg['name']}")
        controller = MicrophoneController(
            info = msg,
            logger = package["logger"]
        )

        return {
            "device": msg,
            "controller": controller
        }
