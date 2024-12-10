#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
from stream_simulator.base_classes import BasicSensor
import statistics
import pprint

class EnvTemperatureSensorController(BasicSensor):
    def __init__(self, conf = None, package = None):

        _type = "TEMPERATURE"
        _category = "sensor"
        _class = "env"
        _subclass = "temperature"

        super().__init__(
            conf = conf,
            package = package,
            _type = _type,
            _category = _category,
            _class = _class,
            _subclass = _subclass        
        )

        self.env_properties = package['env']

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

        self.tf_declare_rpc.call(tf_package)

    def get_simulation_value(self):
        res = self.tf_affection_rpc.call({
            'name': self.name
        })

        # Logic
        amb = self.env_properties['temperature']
        temps = []
        if res == None:
            return amb

        for a in res:
            r = (1 - res[a]['distance'] / res[a]['range']) * res[a]['info']['temperature']
            temps.append(r)

        mms = 0
        if len(temps) > 0:
            mms = statistics.mean(temps)
        final = amb + mms
        return final
