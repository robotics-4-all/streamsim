#!/usr/bin/python
# -*- coding: utf-8 -*-

from stream_simulator.base_classes import BasicSensor

class EnvHumiditySensorController(BasicSensor):
    def __init__(self, conf = None, package = None):
        super(self.__class__, self).__init__(
            conf = conf,
            package = package,
            _type = "HUMIDITY",
            _category = "humidity",
            _brand = "hum",
            _name_suffix = "humidity_",
            _endpoints = {
                "enable": "rpc",
                "disable": "rpc",
                "set_mode": "rpc",
                "get_mode": "rpc",
                "data": "pub"
            }
        )
