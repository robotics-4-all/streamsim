#!/usr/bin/python
# -*- coding: utf-8 -*-

from commlib.logger import Logger
from stream_simulator.controllers import GstreamerServerController

class GStreamerServerConf:
    logger = Logger("GStreamerServerConf")

    @staticmethod
    def configure(id = 0,
                  conf = None,
                  package = None):
        msg = {
            "type": "GSTREAMER_SERVER",
            "brand": "gstream",
            "base_topic": package["name"] + ".sensor.audio.gstreamer.d" + str(id),
            "name": "gstreamer_" + str(id),
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
            "endpoints":{
                "enable": "rpc",
                "disable": "rpc"
            },
            "data_models": {}
        }

        GStreamerServerConf.logger.info(f"Creating controller for {msg['name']}")
        controller = GstreamerServerController(
            info = msg,
            logger = package["logger"]
        )

        return {
            "device": msg,
            "controller": controller
        }
