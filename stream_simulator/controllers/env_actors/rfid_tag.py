#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
from stream_simulator.base_classes import BaseThing
from stream_simulator.connectivity import CommlibFactory

class RfidTagActor(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger("rfid_tag_" + str(conf["id"]))
        else:
            self.logger = package["logger"]

        super().__init__("rfid_tag_" + str(conf["id"]))
        id = BaseThing.id

        self.set_tf_communication(package)

        info = {
            "type": "RFID_TAG",
            "conf": conf,
            "id": id,
            "name": "rfid_tag_" + str(conf["id"])
        }

        self.info = info
        self.name = info['name']
        self.pose = {
            'x': conf['x'],
            'y': conf['y'],
            'theta': None
        }
        self.message = conf['message']
        self.id = conf["id"]

        # tf handling
        tf_package = {
            "type": "actor",
            "subtype": "rfid_tag",
            "pose": self.pose,
            "name": self.name,
            "id": self.id,
            "properties": {
                "message": self.message,
                "id": self.id
            }
        }

        self.host = None
        if 'host' in info['conf']:
            self.host = info['conf']['host']
            tf_package['host'] = self.host
            # No other host type is available for env_devices
            tf_package['host_type'] = 'pan_tilt'

        self.tf_declare_rpc.call(tf_package)
