#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
from stream_simulator.base_classes import BaseThing
from stream_simulator.connectivity import CommlibFactory

class HumanActor(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger("human_" + str(conf["id"]))
        else:
            self.logger = package["logger"]

        super().__init__("human_" + str(conf["id"]), auto_start=False)
        id = BaseThing.id

        self.set_tf_communication(package)

        info = {
            "type": "HUMAN",
            "conf": conf,
            "id": id,
            "name": "human_" + str(conf["id"])
        }

        self.info = info
        self.name = info['name']
        self.pose = {
            'x': conf['x'],
            'y': conf['y'],
            'theta': None
        }
        self.motion = conf['move']
        self.sound = conf['sound']
        self.language = conf['lang']
        self.range = 80 if 'range' not in conf else conf['range']
        self.speech = "" if 'speech' not in conf else conf['speech']
        self.emotion = "neutral" if 'emotion' not in conf else conf['emotion']
        self.gender = "none" if 'gender' not in conf else conf['gender']
        self.age = "-1" if 'age' not in conf else conf['age']
        self.id = conf["id"]

        # tf handling
        tf_package = {
            "type": "actor",
            "subtype": "human",
            "pose": self.pose,
            "name": self.name,
            "range": self.range,
            "id": self.id,
            "properties": {
                'motion': self.motion,
                'sound': self.sound,
                'language': self.language,
                'speech': self.speech,
                'emotion': self.emotion,
                'gender': self.gender,
                'age': self.age
            }
        }

        self.host = None
        if 'host' in info['conf']:
            self.host = info['conf']['host']
            tf_package['host'] = self.host
            # No other host type is available for env_devices
            tf_package['host_type'] = 'pan_tilt'

        self.tf_declare_rpc.call(tf_package)

        self.commlib_factory.run()
