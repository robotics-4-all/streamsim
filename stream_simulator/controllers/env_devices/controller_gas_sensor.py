#!/usr/bin/python
# -*- coding: utf-8 -*-

import random
from stream_simulator.base_classes import BasicSensor

class EnvGasSensorController(BasicSensor):
    """
    Controller class for an environmental gas sensor.
    Args:
        conf (dict, optional): Configuration dictionary for the sensor. Defaults to None.
        package (dict, optional): Package containing sensor properties. Defaults to None.
    Attributes:
        env_properties (dict): Environmental properties from the package.
        host (str): Host information from the configuration, if available.
    Methods:
        get_simulation_value():
            Calculates and returns the simulated gas concentration value in parts per million (ppm).
    """
    def __init__(self, conf = None, package = None):

        _type = "GAS_SENSOR"
        _category = "sensor"
        _class = "env"
        _subclass = "gas"
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

        # humans max: 1000 ppm each
        # fires max: 5000 ppm

        ppm = 400 # typical environmental

        # Logic
        for a in res:
            rel_range = res[a]['distance'] / res[a]['range']
            if res[a]['type'] == 'human':
                ppm += 1000.0 * rel_range
            elif res[a]['type'] == 'fire':
                ppm += 5000.0 * rel_range

        return ppm + random.uniform(-10, 10)
