"""
File that contains the color actor.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
from stream_simulator.base_classes import BaseThing

class ColorActor(BaseThing):
    """
    ColorActor is a class that represents an actor with color properties in 
        a simulation environment.
    Attributes:
        logger (logging.Logger): Logger instance for the actor.
        id (int): Unique identifier for the actor.
        info (dict): Information dictionary containing type, configuration, id, 
            and name of the actor.
        name (str): Name of the actor.
        pose (dict): Dictionary containing the position (x, y) and orientation (theta) of the actor.
        r (int): Red color component.
        g (int): Green color component.
        b (int): Blue color component.
        host (str, optional): Host information if available in the configuration.
    Methods:
        set_tf_communication(package): Sets up the communication for the actor.
        tf_declare_rpc.call(tf_package): Declares the actor's properties to the tf system.
        commlib_factory.run(): Runs the communication library factory.
    Args:
        conf (dict, optional): Configuration dictionary for the actor.
        package (dict, optional): Package dictionary containing additional information 
            such as logger.
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
            "type": "COLOR",
            "conf": conf,
            "id": id_,
            "name": conf['name']
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

        self.tf_declare_rpc.call(tf_package)

        self.commlib_factory.run()
