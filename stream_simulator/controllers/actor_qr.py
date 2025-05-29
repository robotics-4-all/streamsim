"""
File that contains the QR actor.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
from stream_simulator.base_classes import BaseThing

class QrActor(BaseThing):
    """
    QrActor is a class that represents a QR code actor in the simulation environment.
    Attributes:
        logger (logging.Logger): Logger instance for the QR actor.
        info (dict): Information dictionary containing type, configuration, id, and 
            name of the QR actor.
        name (str): Name of the QR actor.
        pose (dict): Pose information of the QR actor with x, y coordinates and theta.
        id (int): Identifier for the QR actor.
        message (str): Message associated with the QR actor.
        host (str, optional): Host information if available in the configuration.
    Methods:
        __init__(conf=None, package=None): Initializes the QrActor instance with 
            the given configuration and package.
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
            "type": "QR",
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
        self.id = conf["id"]
        self.message = conf['message']

        # tf handling
        tf_package = {
            "type": "actor",
            "subtype": "qr",
            "pose": self.pose,
            "name": self.name,
            "id": self.id,
            "properties": {
                "message": self.message
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
