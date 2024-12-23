"""
This file contains the controller class for an environmental pH sensor.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import statistics
import random
from stream_simulator.base_classes import BasicSensor

class EnvPhSensorController(BasicSensor):
    """
    Controller class for the environmental pH sensor.
    Args:
        conf (dict, optional): Configuration dictionary for the sensor. Defaults to None.
        package (dict, optional): Package information dictionary. Defaults to None.
    Attributes:
        host (str): Host information for the sensor, if available.
        tf_declare_rpc (RPCClient): RPC client for declaring the sensor to the transformation 
        framework.
    Methods:
        __init__(conf=None, package=None): Initializes the EnvPhSensorController with the given 
        configuration and package.
    """
    def __init__(self, conf = None, package = None):

        _type = "PH_SENSOR"
        _category = "sensor"
        _class = "env"
        _subclass = "ph"
        _namespace = package["namespace"]
        super().__init__(
            conf = conf,
            package = package,
            _type = _type,
            _category = _category,
            _class = _class,
            _subclass = _subclass
        )

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

        # Create the RPC client to declare to tf
        self.tf_declare_rpc = self.commlib_factory.getRPCClient(
            rpc_name = package["tf_declare_rpc_topic"]
        )

        self.tf_declare_rpc.call(tf_package)

        # Default value management
        if "env" not in package or "ph" not in package['env']:
            self.env_properties = {
                'ph': 7.0
            }
        else:
            self.env_properties = package['env']

    def get_simulation_value(self):
        """
        Gets the simulation value for the sensor.
        Returns:
            float: The simulated pH value.
        """
        res = self.tf_affection_rpc.call({
            'name': self.name
        })

        # Logic
        amb = self.env_properties['ph']
        ph_values = []
        if res is None:
            return amb

        for a in res:
            ph_values.append(a['ph'])

        if len(ph_values) == 0:
            return amb + random.uniform(-0.1, 0.1)

        return statistics.mean(ph_values)
