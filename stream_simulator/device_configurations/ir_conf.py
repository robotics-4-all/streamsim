#!/usr/bin/python
# -*- coding: utf-8 -*-

from commlib.logger import Logger
from stream_simulator.controllers import IrController

class IrConf:
    logger = Logger("IrConf")

    @staticmethod
    def configure(id = 0,
                  conf = None,
                  package = None):
        msg = {
            "type": "IR",
            "brand": "ir",
            "base_topic": package["name"] + ".sensor.distance.ir.d" + str(id),
            "name": "ir_" + str(id),
            "place": conf["place"],
            "id": "id_" + str(id),
            "enabled": True,
            "orientation": conf["orientation"],
            "hz": conf["hz"],
            "queue_size": 100,
            "mode": package["mode"],
            "speak_mode": package["speak_mode"],
            "namespace": package["namespace"],
            "sensor_configuration": conf["sensor_configuration"],
            "max_range": conf["max_range"],
            "device_name": package["device_name"],
            "endpoints":{
                "enable": "rpc",
                "disable": "rpc",
                "data": "publisher"
            },
            "data_models": {
                "data": ["distance"]
            }
        }
        IrConf.logger.info(f"Creating controller for {msg['name']}")
        controller = IrController(
            info = msg,
            map = package["map"],
            logger = package["logger"]
        )

        return {
            "device": msg,
            "controller": controller
        }
