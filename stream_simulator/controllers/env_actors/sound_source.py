"""
File that contains the sound source actor.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
from stream_simulator.base_classes import BaseThing

class SoundSourceActor(BaseThing):
    """
    SoundSourceActor is a class that represents a sound source actor in the simulation environment.
    Attributes:
        logger (logging.Logger): Logger instance for logging messages.
        info (dict): Information dictionary containing type, configuration, id, and name 
            of the sound source.
        name (str): Name of the sound source.
        pose (dict): Dictionary containing the x, y coordinates and theta (orientation) 
            of the sound source.
        language (str): Language of the sound source.
        speech (str): Speech content of the sound source.
        id (int): Identifier of the sound source.
        emotion (str): Emotion associated with the sound source.
        range (int): Range of the sound source.
        host (str, optional): Host information if available in the configuration.
    Methods:
        __init__(conf=None, package=None): Initializes the SoundSourceActor with t
            he given configuration and package.
    """
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger("sound_source_" + str(conf["id"]))
        else:
            self.logger = package["logger"]

        super().__init__("sound_source_" + str(conf["id"]), auto_start=False)
        id_ = BaseThing.id

        self.set_tf_communication(package)

        info = {
            "type": "SOUND_SOURCE",
            "conf": conf,
            "id": id_,
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
