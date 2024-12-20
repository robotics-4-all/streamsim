#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
from stream_simulator.base_classes import BaseThing

class SoundSourceActor(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger("sound_source_" + str(conf["id"]))
        else:
            self.logger = package["logger"]

        super().__init__("sound_source_" + str(conf["id"]), auto_start=False)
        id = BaseThing.id

        self.set_tf_communication(package)

        info = {
            "type": "SOUND_SOURCE",
            "conf": conf,
            "id": id,
            "name": "sound_source_" + str(conf["id"])
        }

        self.info = info
        self.name = info['name']
        self.pose = {
            'x': conf['x'],
            'y': conf['y'],
            'theta': None
        }
        self.language = conf['lang']
        self.speech = conf['speech']
        self.id = conf["id"]
        self.emotion = conf['emotion']
        self.range = 100 if 'range' not in conf else conf['range']

        # tf handling
        tf_package = {
            "type": "actor",
            "subtype": "sound_source",
            "pose": self.pose,
            "name": self.name,
            "range": self.range,
            "id": self.id,
            "properties": {
                'language': self.language,
                'speech': self.speech,
                'emotion': self.emotion
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
