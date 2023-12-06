#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
from stream_simulator.base_classes import BaseThing
from stream_simulator.connectivity import CommlibFactory

class ColorActor(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger("color_" + str(conf["id"]))
        else:
            self.logger = package["logger"]

        super(self.__class__, self).__init__()
        id = BaseThing.id

        info = {
            "type": "COLOR",
            "conf": conf,
            "id": id,
            "name": "color_" + str(conf["id"])
        }

        self.id = conf["id"]

        self.info = info
        self.name = info['name']
        self.pose = {
            'x': conf['x'],
            'y': conf['y'],
            'theta': None
        }
        self.r = conf['r']
        self.g = conf['g']
        self.b = conf['b']

        # tf handling
        tf_package = {
            "type": "actor",
            "subtype": "color",
            "pose": self.pose,
            "name": self.name,
            "id": self.id,
            "properties": {
                'r': self.r,
                'g': self.g,
                'b': self.b
            }
        }

        self.host = None
        if 'host' in info['conf']:
            self.host = info['conf']['host']
            tf_package['host'] = self.host
            # No other host type is available for env_devices
            tf_package['host_type'] = 'pan_tilt'

        package["tf_declare"].call(tf_package)
