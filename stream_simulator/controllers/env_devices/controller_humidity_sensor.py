"""
File that contains the humidity sensor controller.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import statistics
import random

from stream_simulator.base_classes import BasicSensor

class EnvHumiditySensorController(BasicSensor):
    """
    Controller class for an environmental humidity sensor.
    Args:
        conf (dict, optional): Configuration dictionary for the sensor.
        package (dict, optional): Package dictionary containing sensor details.
    Attributes:
        env_properties (dict): Environmental properties from the package.
        host (str): Host information for the sensor, if available.
    Methods:
        get_simulation_value():
            Retrieves the simulated humidity value based on environmental properties and sensor 
            affections.
    """
    def __init__(self, conf = None, package = None):

        _type = "HUMIDITY"
        _category = "sensor"
        _class = "env"
        _subclass = "humidity"

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

        self.dynamic_value = None

    def get_simulation_value(self):
        """
        Calculate the simulated humidity value based on environmental properties and external 
            factors.
        This method retrieves the current humidity affection values from an external source,
        calculates the mean affection, and adjusts the ambient humidity accordingly. It also
        adds a small random variation to simulate natural fluctuations.
        Returns:
            float: The simulated humidity value.
        """
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

        final_value = ambient
        if self.dynamic_value is None:
            self.dynamic_value = final_value
        else:
            self.dynamic_value += (final_value - self.dynamic_value)/6
        return self.dynamic_value + random.uniform(-0.5, 0.5)
