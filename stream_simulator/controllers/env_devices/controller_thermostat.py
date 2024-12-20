#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import time

from stream_simulator.base_classes import BaseThing

class EnvThermostatController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        super().__init__(conf["name"], auto_start=False)

        _type = "THERMOSTAT"
        _category = "actuator"
        _class = "env"
        _subclass = "thermostat"

        _name = conf["name"]
        _pack = package["base"]
        _place = conf["place"]
        _namespace = package["namespace"]
        info = {
            "type": _type,
            "base_topic": f"{_namespace}.{_pack}.{_place}.{_category}.{_class}.{_subclass}.{_name}",
            "name": _name,
            "place": conf["place"],
            "enabled": True,
            "mode": conf["mode"],
            "conf": conf,
            "categorization": {
                "host_type": _pack,
                "place": _place,
                "category": _category,
                "class": _class,
                "subclass": [_subclass],
                "name": _name
            }
        }

        self.info = info
        self.pose = info["conf"]["pose"]
        self.name = info["name"]
        self.base_topic = info["base_topic"]
        self.place = info["conf"]["place"]
        self.temperature = info['conf']['temperature']
        self.range = info['conf']['range']

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
            "name": self.name,
            "range": self.range
        }

        self.host = None
        if 'host' in info['conf']:
            self.host = info['conf']['host']
            tf_package['host'] = self.host
            # No other host type is available for env_devices
            tf_package['host_type'] = 'pan_tilt'

        self.set_communication_layer(package)
        self.commlib_factory.run()

        self.tf_declare_rpc.call(tf_package)

    def set_communication_layer(self, package):
        self.set_simulation_communication(package["namespace"])
        self.set_tf_communication(package)
        self.set_enable_disable_rpcs(self.base_topic, self.enable_callback, self.disable_callback)
        self.set_effector_set_get_rpcs(self.base_topic, self.set_callback, self.get_callback)
        self.set_data_publisher(self.base_topic)

    def enable_callback(self, _):
        self.info["enabled"] = True

        # self.enable_rpc_server.run()
        # self.disable_rpc_server.run()
        # self.get_rpc_server.run()
        # self.set_rpc_server.run()

        return {"enabled": True}

    def disable_callback(self, _):
        self.info["enabled"] = False
        return {"enabled": False}

    def get_callback(self, _):
        return {"temperature": self.temperature}

    def set_callback(self, message):
        self.temperature = message["temperature"]
        self.publisher.publish(message)

        self.commlib_factory.notify_ui(
            type_ = "effector_command",
            data = {
                "name": self.name,
                "value": {
                    "temperature": message["temperature"]
                }
            }
        )

        return {}

    def start(self):
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)
        self.logger.info("Sensor %s started", self.name)

        # self.enable_rpc_server.run()
        # self.disable_rpc_server.run()
        # self.get_rpc_server.run()
        # self.set_rpc_server.run()

    def stop(self):
        self.info["enabled"] = False
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()
        self.get_rpc_server.stop()
        self.set_rpc_server.stop()
