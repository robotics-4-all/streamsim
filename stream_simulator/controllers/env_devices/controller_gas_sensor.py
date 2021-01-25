#!/usr/bin/python
# -*- coding: utf-8 -*-

from stream_simulator.base_classes import BasicSensor
from stream_simulator.connectivity import CommlibFactory
import statistics

class EnvGasSensorController(BasicSensor):
    def __init__(self, conf = None, package = None):

        _type = "GAS_SENSOR"
        _category = "sensor"
        _class = "env"
        _subclass = "gas"

        super(self.__class__, self).__init__(
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

        package["tf_declare"].call(tf_package)

    def get_simulation_value(self):
        res = CommlibFactory.get_tf_affection.call({
            'name': self.name
        })
        # Logic
        vals = []
        for a in res:
            vals.append(res[a])

        print(vals)
        return 0.5
