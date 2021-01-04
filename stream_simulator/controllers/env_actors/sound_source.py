#!/usr/bin/python
# -*- coding: utf-8 -*-

from commlib.logger import Logger
from stream_simulator.base_classes import BaseThing
from stream_simulator.connectivity import CommlibFactory

class SoundSourceActor(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = Logger("sound_source_" + str(conf["id"]))
        else:
            self.logger = package["logger"]

        super(self.__class__, self).__init__()
        id = BaseThing.id

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

        self.logger.info(f"Actor {self.name} declared")
