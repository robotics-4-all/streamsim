"""
File that contains the fire actor.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
from stream_simulator.base_classes import BaseThing

class FireActor(BaseThing):
    """
    FireActor is a class that represents a fire entity in the simulation environment.
    Attributes:
        logger (logging.Logger): Logger instance for the fire actor.
        info (dict): Information about the fire actor including type, configuration, id, and name.
        name (str): Name of the fire actor.
        pose (dict): Position of the fire actor with keys 'x', 'y', and 'theta'.
        id (int): Unique identifier for the fire actor.
        temperature (int): Temperature of the fire actor. Defaults to 150 if not 
            specified in the configuration.
        range (int): Range of the fire actor. Defaults to 100 if not specified in the configuration.
        host (str): Host information if available in the configuration.
    Methods:
        __init__(conf=None, package=None): Initializes the FireActor instance with 
            the given configuration and package.
    """
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger("fire_" + str(conf["id"]))
        else:
            self.logger = package["logger"]

        super().__init__("fire_" + str(conf["id"]), auto_start=False)
        id_ = BaseThing.id

        self.set_tf_communication(package)

        info = {
            "type": "FIRE",
            "conf": conf,
            "id": id_,
            "name": "fire_" + str(conf["id"])
        }

        self.info = info
        self.name = info['name']
        self.pose = {
            'x': conf['x'],
            'y': conf['y'],
            'theta': None
        }
        self.id = conf["id"]

        self.temperature = 150 if 'temperature' not in conf else conf['temperature']
        self.range = 100 if 'range' not in conf else conf['range']

        # tf handling
        tf_package = {
            "type": "actor",
            "subtype": "fire",
            "pose": self.pose,
            "name": self.name,
            "range": self.range,
            "id": self.id,
            "properties": {
                "temperature": self.temperature
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
