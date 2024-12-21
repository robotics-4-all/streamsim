"""
File that contains the barcode actor.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
from stream_simulator.base_classes import BaseThing

class BarcodeActor(BaseThing):
    """
    BarcodeActor is a class that represents a barcode actor in the simulation environment.
    Attributes:
        logger (logging.Logger): Logger instance for logging messages.
        info (dict): Information dictionary containing type, configuration, id, and name 
            of the barcode actor.
        name (str): Name of the barcode actor.
        pose (dict): Dictionary containing the x, y coordinates and theta orientation 
            of the barcode actor.
        message (str): Message associated with the barcode actor.
        id (int): Identifier for the barcode actor.
        host (str, optional): Host information if available in the configuration.
    Methods:
        set_tf_communication(package): Sets up the communication for the barcode actor.
    """

    def __init__(self, conf = None, package = None):
        """
        Initializes the Barcode actor with the given configuration and package.
        Args:
            conf (dict, optional): Configuration dictionary containing the following keys:
                - id (int): Unique identifier for the barcode.
                - x (float): X-coordinate of the barcode's position.
                - y (float): Y-coordinate of the barcode's position.
                - message (str): Message associated with the barcode.
                - host (str, optional): Host information for the barcode.
            package (dict, optional): Package dictionary containing the following keys:
                - logger (logging.Logger, optional): Logger instance for the barcode.
        Attributes:
            logger (logging.Logger): Logger instance for the barcode.
            info (dict): Information dictionary containing barcode details.
            name (str): Name of the barcode.
            pose (dict): Dictionary containing the position (x, y) and orientation 
                (theta) of the barcode.
            message (str): Message associated with the barcode.
            id (int): Unique identifier for the barcode.
            host (str, optional): Host information for the barcode.
        """
        if package["logger"] is None:
            self.logger = logging.getLogger("barcode_" + str(conf["id"]))
        else:
            self.logger = package["logger"]

        super().__init__("barcode_" + str(conf["id"]), auto_start=False)
        id_ = BaseThing.id

        self.set_tf_communication(package)

        info = {
            "type": "BARCODE",
            "conf": conf,
            "id": id_,
            "name": "barcode_" + str(conf["id"])
        }

        self.info = info
        self.name = info['name']
        self.pose = {
            'x': conf['x'],
            'y': conf['y'],
            'theta': None
        }
        self.message = conf['message']
        self.id = conf["id"]

        # tf handling
        tf_package = {
            "type": "actor",
            "subtype": "barcode",
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
