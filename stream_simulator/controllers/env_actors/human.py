"""
File that contains the human actor.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
from stream_simulator.base_classes import BaseThing

class HumanActor(BaseThing):
    """
    HumanActor is a class that represents a human actor in the simulation environment.
    Attributes:
        logger (logging.Logger): Logger for the human actor.
        info (dict): Information about the human actor including type, configuration, id, and name.
        name (str): Name of the human actor.
        pose (dict): Pose of the human actor with x, y coordinates and theta.
        motion (str): Motion configuration of the human actor.
        sound (str): Sound configuration of the human actor.
        language (str): Language configuration of the human actor.
        range (int): Range of the human actor.
        speech (str): Speech configuration of the human actor.
        emotion (str): Emotion configuration of the human actor.
        gender (str): Gender configuration of the human actor.
        age (str): Age configuration of the human actor.
        id (int): ID of the human actor.
        host (str, optional): Host configuration of the human actor.
    Methods:
        __init__(conf=None, package=None): Initializes the HumanActor with the 
            given configuration and package.
    """
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger("human_" + str(conf["id"]))
        else:
            self.logger = package["logger"]

        super().__init__("human_" + str(conf["id"]), auto_start=False)
        id_ = BaseThing.id

        self.set_tf_communication(package)

        info = {
            "type": "HUMAN",
            "conf": conf,
            "id": id_,
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
