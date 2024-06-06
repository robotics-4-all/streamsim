#!/usr/bin/python
# -*- coding: utf-8 -*-

from stream_simulator.base_classes import BasicSensor
from stream_simulator.connectivity import CommlibFactory
import statistics
import time

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

         # Create the RPC client to declare to tf
        self.tf_declare_rpc = self.commlib_factory.getRPCClient(
            rpc_name = package["tf_declare_rpc_topic"]
        )

        self.tf_affection_rpc = self.commlib_factory.getRPCClient(
            rpc_name = package["tf_affection_rpc_topic"]
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

        return ppm
