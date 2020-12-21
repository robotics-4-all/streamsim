#!/usr/bin/python
# -*- coding: utf-8 -*-

from commlib.logger import Logger
from stream_simulator.controllers import RelayController

class RelayEnvConf:
    logger = Logger("RelayEnvConf")

    @staticmethod
    def configure(id = 0,
                  conf = None,
                  package = None):
        msg = {
            "type": "RELAY",
            "brand": "relay",
            "base_topic": package["base"] + conf["place"] + ".effector.mechanical.relay.d" + str(id),
            "name": "relay_" + str(id),
            "place": conf["place"],
            "enabled": True,
            "mode": package["mode"],
            "conf": conf,
            "endpoints":{
                "enable": "rpc",
                "disable": "rpc",
                "set": "rpc",
                "get": "rpc"
            }
        }
        RelayEnvConf.logger.info(f"Creating controller for {msg['name']}")
        controller = RelayController(
            info = msg,
            logger = package["logger"]
        )

        return {
            "device": msg,
            "controller": controller
        }
