#!/usr/bin/python
# -*- coding: utf-8 -*-

from commlib.logger import Logger
from stream_simulator.base_classes import BaseThing
from stream_simulator.connectivity import CommlibFactory

class SupermanActor(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = Logger("superman_" + str(conf["id"]))
        else:
            self.logger = package["logger"]

        super(self.__class__, self).__init__()
        id = BaseThing.id

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

        self.logger.info(f"Actor {self.name} declared")
