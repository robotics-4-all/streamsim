"""
File that contains the water actor.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
from stream_simulator.base_classes import BaseThing

class WaterActor(BaseThing):
    """
    WaterActor is a class that represents a water actor in the simulation environment.
    Attributes:
        logger (logging.Logger): Logger instance for the water actor.
        info (dict): Information dictionary containing type, configuration, id, and 
            name of the water actor.
        name (str): Name of the water actor.
        pose (dict): Dictionary containing the x, y coordinates and theta orientation 
            of the water actor.
        range (int): Range of the water actor.
        humidity (int): Humidity level of the water actor.
        id (int): Identifier of the water actor.
        host (str, optional): Host information if available in the configuration.
    Methods:
        __init__(conf=None, package=None): Initializes the WaterActor instance with 
            the given configuration and package.
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
            "type": "WATER",
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
        self.range = 100 if 'range' not in conf else conf['range']
        self.humidity = 100
        self.id = conf["id"]

        # tf handling
        tf_package = {
            "type": "actor",
            "subtype": "water",
            "pose": self.pose,
            "name": self.name,
            "range": self.range,
            "id": self.id,
            "properties": {
                "humidity": self.humidity
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
