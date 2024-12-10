#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
from stream_simulator.base_classes import BaseThing
from stream_simulator.connectivity import CommlibFactory

class TextActor(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger("text_" + str(conf["id"]))
        else:
            self.logger = package["logger"]

        super().__init__("text_" + str(conf["id"]))
        id = BaseThing.id

        self.set_tf_communication(package)

        info = {
            "type": "TEXT",
            "conf": conf,
            "id": id,
            "name": "text_" + str(conf["id"])
        }

        self.info = info
        self.name = info['name']
        self.pose = {
            'x': conf['x'],
            'y': conf['y'],
            'theta': None
        }
        self.text = conf['text']
        self.id = conf["id"]

        # tf handling
        tf_package = {
            "type": "actor",
            "subtype": "text",
            "pose": self.pose,
            "name": self.name,
            "id": self.id,
            "properties": {
                "text": self.text
            }
        }

        self.host = None
        if 'host' in info['conf']:
            self.host = info['conf']['host']
            tf_package['host'] = self.host
            # No other host type is available for env_devices
            tf_package['host_type'] = 'pan_tilt'

        self.tf_declare_rpc.call(tf_package)