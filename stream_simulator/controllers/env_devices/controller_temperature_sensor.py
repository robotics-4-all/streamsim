"""
This file contains the controller class for an environmental temperature sensor.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import statistics
import random
from stream_simulator.base_classes import BasicSensor

class EnvTemperatureSensorController(BasicSensor):
    """
    Controller for an environmental temperature sensor.
    This class extends the BasicSensor class and is responsible for managing
    the temperature sensor in an environment simulation. It initializes the
    sensor with specific configuration and package details, handles the 
    transformation (tf) package, and provides methods to get simulation values.
    Attributes:
        env_properties (dict): Environmental properties from the package.
        host (str): Host information from the configuration, if available.
    Methods:
        get_simulation_value():
            Calculates and returns the simulated temperature value based on
            environmental properties and transformation (tf) affection results.
    """

    def __init__(self, conf = None, package = None):
        """
        Initialize the Temperature Sensor Controller.
        Args:
            conf (dict, optional): Configuration dictionary for the controller. Defaults to None.
            package (dict, optional): Package containing environment properties and other necessary 
            information. Defaults to None.
        Attributes:
            env_properties (dict): Environment properties extracted from the package.
            host (str, optional): Host information if available in the configuration.
        """

        _type = "TEMPERATURE"
        _category = "sensor"
        _class = "env"
        _subclass = "temperature"
        _namespace = package["namespace"]

        super().__init__(
            conf = conf,
            package = package,
            _type = _type,
            _category = _category,
            _class = _class,
            _subclass = _subclass,
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
        """
        Calculate the simulated temperature value based on environmental properties and sensor data.
        This method retrieves temperature-affecting data from a remote procedure call (RPC) and 
        calculates the final temperature value by considering the ambient temperature and the 
        influence of other temperature sources within a certain range.
        Returns:
            float: The final simulated temperature value.
        """
        res = self.tf_affection_rpc.call({
            'name': self.name
        })

        # Logic
        amb = self.env_properties['temperature']
        temps = []
        if res is None:
            return amb

        for a in res:
            r = (1 - res[a]['distance'] / res[a]['range']) * res[a]['info']['temperature']
            temps.append(r)

        mms = 0
        if len(temps) > 0:
            mms = statistics.mean(temps)
        final = amb + mms + random.uniform(-0.1, 0.1)
        return final
