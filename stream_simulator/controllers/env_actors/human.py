#!/usr/bin/python
# -*- coding: utf-8 -*-

from stream_simulator.base_classes import BaseThing
from stream_simulator.connectivity import CommlibFactory

class HumanActor(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = Logger(conf["name"])
        else:
            self.logger = package["logger"]

        super(self.__class__, self).__init__()
        id = BaseThing.id

        info = {
            "type": "HUMAN",
            "conf": conf,
            "id": id,
            "name": conf["id"]
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
