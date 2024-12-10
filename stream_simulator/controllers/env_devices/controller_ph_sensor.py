#!/usr/bin/python
# -*- coding: utf-8 -*-

from stream_simulator.base_classes import BasicSensor
from stream_simulator.connectivity import CommlibFactory
import statistics
import time

class EnvPhSensorController(BasicSensor):
    def __init__(self, conf = None, package = None):

        _type = "PH_SENSOR"
        _category = "sensor"
        _class = "env"
        _subclass = "ph"

        super().__init__(
            conf = conf,
            package = package,
            _type = _type,
            _category = _category,
            _class = _class,
            _subclass = _subclass
        )

        # tf handling
        tf_package = {
            "type": "env",
            "subtype": {
                "category": _category,
                "class": _class,
                "subclass": [_subclass]
            },
            "pose": self.pose,
            "base_topic": self.base_topic,
            "name": self.name
        }

        self.host = None
        if 'host' in self.info['conf']:
            self.host = self.info['conf']['host']
            tf_package['host'] = self.host
            # No other host type is available for env_devices
            tf_package['host_type'] = 'pan_tilt'

        # Create the RPC client to declare to tf
        self.tf_declare_rpc = self.commlib_factory.getRPCClient(
            rpc_name = package["tf_declare_rpc_topic"]
        )

        self.tf_declare_rpc.call(tf_package)

