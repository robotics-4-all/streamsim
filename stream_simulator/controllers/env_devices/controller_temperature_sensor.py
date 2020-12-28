#!/usr/bin/python
# -*- coding: utf-8 -*-

from stream_simulator.base_classes import BasicSensor

class EnvTemperatureSensorController(BasicSensor):
    def __init__(self, conf = None, package = None):
        super(self.__class__, self).__init__(
            conf = conf,
            package = package,
            _type = "TEMPERATURE",
            _category = "environmental",
            _brand = "temp",
            _name_suffix = "thermal_",
            _endpoints = {
                "enable": "rpc",
                "disable": "rpc",
                "set_mode": "rpc",
                "get_mode": "rpc",
                "data": "pub"
            }
        )
