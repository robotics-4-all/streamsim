"""
File that contains the text actor.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
from stream_simulator.base_classes import BaseThing

class TextActor(BaseThing):
    """
    A class to represent a TextActor which inherits from BaseThing.
    Attributes:
    -----------
    logger : logging.Logger
        Logger instance for the TextActor.
    info : dict
        Dictionary containing information about the TextActor.
    name : str
        Name of the TextActor.
    pose : dict
        Dictionary containing the position (x, y) and orientation (theta) of the TextActor.
    text : str
        Text content of the TextActor.
    id : int
        Identifier for the TextActor.
    host : str, optional
        Host information if available in the configuration.
    Methods:
    --------
    __init__(conf=None, package=None):
        Initializes the TextActor with the given configuration and package.
    """
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf['name'])
        else:
            self.logger = package["logger"]

        super().__init__(conf['name'], auto_start=False)
        id_ = BaseThing.id

        self.set_tf_communication(package)

        info = {
            "type": "TEXT",
            "conf": conf,
            "id": id_,
            "name": conf['name']
        }

        self.info = info
        self.name = info['name']
        self.pose = {
            'x': conf['x'],
            'y': conf['y'],
            'theta': None
        }
        self.text = conf['text']
        self.id = conf["id"]

        # tf handling
        tf_package = {
            "type": "actor",
            "subtype": "text",
            "pose": self.pose,
            "name": self.name,
            "id": self.id,
            "properties": {
                "text": self.text
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
