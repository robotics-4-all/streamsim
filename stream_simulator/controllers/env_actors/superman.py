"""
File that contains the superman actor.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
from stream_simulator.base_classes import BaseThing

class SupermanActor(BaseThing):
    """
    A class representing a Superman actor in the simulation environment.
    Attributes:
        logger (logging.Logger): Logger instance for the actor.
        info (dict): Information about the actor including type, configuration, id, and name.
        pose (dict): Pose information of the actor including x, y coordinates and theta.
        motion (str): Motion configuration for the actor.
        sound (str): Sound configuration for the actor.
        language (str): Language configuration for the actor.
        message (str): Message configuration for the actor.
        text (str): Text configuration for the actor.
        name (str): Name of the actor.
        id (int): ID of the actor.
        host (str, optional): Host configuration for the actor.
    Methods:
        __init__(conf=None, package=None): Initializes the SupermanActor instance.
    """
    def __init__(self, conf = None, package = None, precision_mode = False):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf['name'])
        else:
            self.logger = package["logger"]

        super().__init__(conf['name'], auto_start=False)
        id_ = BaseThing.id

        self.set_tf_communication(package)

        info = {
            "type": "SUPERMAN",
            "conf": conf,
            "id": id_,
            "name": conf['name']
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

        self.commlib_factory.run()
