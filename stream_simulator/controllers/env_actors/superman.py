#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
from stream_simulator.base_classes import BaseThing
from stream_simulator.connectivity import CommlibFactory

class SupermanActor(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger("superman_" + str(conf["id"]))
        else:
            self.logger = package["logger"]

        super().__init__("superman_" + str(conf["id"]))
        id = BaseThing.id

        self.set_tf_communication(package)

        info = {
            "type": "SUPERMAN",
            "conf": conf,
            "id": id,
            "name": "superman_" + str(conf["id"])
        }

        self.info = info
        self.pose = {
            'x': conf['x'],
            'y': conf['y'],
            'theta': None
        }
        self.motion = conf['move']
        self.sound = conf['sound']
        self.language = conf['lang']
        self.message = conf['message']
        self.text = conf['text']
        self.name = info['name']
        self.id = conf["id"]

        # tf handling
        tf_package = {
            "type": "actor",
            "subtype": "superman",
            "pose": self.pose,
            "name": self.name,
            "id": self.id
        }

        self.host = None
        if 'host' in info['conf']:
            self.host = info['conf']['host']
            tf_package['host'] = self.host
            # No other host type is available for env_devices
            tf_package['host_type'] = 'pan_tilt'

        self.tf_declare_rpc.call(tf_package)
