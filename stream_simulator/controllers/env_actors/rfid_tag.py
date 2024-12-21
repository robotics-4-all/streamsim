"""
File that contains the RFID tag actor.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
from stream_simulator.base_classes import BaseThing

class RfidTagActor(BaseThing):
    """
    RfidTagActor is a class that represents an RFID tag actor in the system.
    Attributes:
        logger (logging.Logger): Logger instance for the RFID tag actor.
        info (dict): Information dictionary containing type, configuration, id, 
            and name of the RFID tag.
        name (str): Name of the RFID tag actor.
        pose (dict): Dictionary containing the x, y coordinates and theta orientation 
            of the RFID tag.
        message (str): Message associated with the RFID tag.
        id (int): Identifier for the RFID tag.
        host (str, optional): Host information if available in the configuration.
    Methods:
        __init__(conf=None, package=None): Initializes the RfidTagActor instance 
            with the given configuration and package.
    """
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger("rfid_tag_" + str(conf["id"]))
        else:
            self.logger = package["logger"]

        super().__init__("rfid_tag_" + str(conf["id"]), auto_start=False)
        id_ = BaseThing.id

        self.set_tf_communication(package)

        info = {
            "type": "RFID_TAG",
            "conf": conf,
            "id": id_,
            "name": "rfid_tag_" + str(conf["id"])
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
            "subtype": "rfid_tag",
            "pose": self.pose,
            "name": self.name,
            "id": self.id,
            "properties": {
                "message": self.message,
                "id": self.id
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
