#!/usr/bin/python
# -*- coding: utf-8 -*-

from stream_simulator.base_classes import BasicSensor

class EnvGasSensorController(BasicSensor):
    def __init__(self, conf = None, package = None):
        super(self.__class__, self).__init__(
            conf = conf,
            package = package,
            _type = "GAS_SENSOR",
            _category = "sensor",
            _class = "env",
            _subclass = "gas",
            _endpoints = {
                "enable": "rpc",
                "disable": "rpc",
                "set_mode": "rpc",
                "get_mode": "rpc",
                "data": "pub"
            }
        )

        # tf handling
        tf_package = {
            "type": "env",
            "subtype": "gas",
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

        package["tf_declare"].call(tf_package)
