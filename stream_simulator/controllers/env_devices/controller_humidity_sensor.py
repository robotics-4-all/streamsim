#!/usr/bin/python
# -*- coding: utf-8 -*-

from stream_simulator.base_classes import BasicSensor
from stream_simulator.connectivity import CommlibFactory
import statistics
import time
import random

class EnvHumiditySensorController(BasicSensor):
    def __init__(self, conf = None, package = None):

        _type = "HUMIDITY"
        _category = "sensor"
        _class = "env"
        _subclass = "humidity"
        _namespace = package["namespace"]

        super().__init__(
            conf = conf,
            package = package,
            _type = _type,
            _category = _category,
            _class = _class,
            _subclass = _subclass
        )

        self.env_properties = package['env']
        self.set_simulation_communication(_namespace)

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

        ambient = self.env_properties['humidity']
        if len(res) == 0:
            return ambient + random.uniform(-0.5, 0.5)

        vs = []
        for a in res:
            vs.append((1 - res[a]['distance'] / res[a]['range']) * res[a]['info']['humidity'])
        affections = statistics.mean(vs)

        if ambient > affections:
            ambient += affections * 0.1
        else:
            ambient = affections - (affections - ambient) * 0.1

        ambient += random.uniform(-0.5, 0.5)

        return ambient
