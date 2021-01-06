#!/usr/bin/python
# -*- coding: utf-8 -*-

from stream_simulator.base_classes import BasicSensor

class EnvPhSensorController(BasicSensor):
    def __init__(self, conf = None, package = None):
        super(self.__class__, self).__init__(
            conf = conf,
            package = package,
            _type = "PH_SENSOR",
            _category = "chemical",
            _brand = "phmeter",
            _name_suffix = "ph_sensor_",
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
            "subtype": "ph",
            "pose": self.pose,
            "base_topic": self.base_topic,
            "name": self.name
        }

        self.host = None
        if 'host' in self.info['conf']:
            self.host = self.info['conf']['host']
            tf_package['host'] = self.host

        package["tf_declare"].call(tf_package)
