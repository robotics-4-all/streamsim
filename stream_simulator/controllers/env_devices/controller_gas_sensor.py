#!/usr/bin/python
# -*- coding: utf-8 -*-

from stream_simulator.base_classes import BasicSensor

class EnvGasSensorController(BasicSensor):
    def __init__(self, conf = None, package = None):
        super(self.__class__, self).__init__(
            conf = conf,
            package = package,
            _type = "GAS_SENSOR",
            _category = "chemical",
            _brand = "co2",
            _name_suffix = "gas_",
            _endpoints = {
                "enable": "rpc",
                "disable": "rpc",
                "set_mode": "rpc",
                "get_mode": "rpc",
                "data": "pub"
            }
        )
