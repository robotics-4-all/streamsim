#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random

from colorama import Fore, Style

from commlib.logger import Logger
from stream_simulator.connectivity import CommlibFactory
from stream_simulator.base_classes import BaseThing

class EnvController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = Logger(conf["name"])
        else:
            self.logger = package["logger"]

        super(self.__class__, self).__init__()
        id = "d_" + str(BaseThing.id)
        name = id
        if 'name' in conf:
            name = conf['name']
        _category = "sensor"
        _class = "env"
        _subclass = "temp_hum_pressure_gas"
        _pack = package["name"]

        info = {
            "type": "ENV",
            "brand": "bme680",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": name,
            "place": conf["place"],
            "id": id,
            "enabled": True,
            "orientation": conf["orientation"],
            "hz": conf["hz"],
            "mode": package["mode"],
            "speak_mode": package["speak_mode"],
            "namespace": package["namespace"],
            "sensor_configuration": conf["sensor_configuration"],
            "device_name": package["device_name"],
            "categorization": {
                "host_type": "robot",
                "place": _pack.split(".")[-1],
                "category": _category,
                "class": _class,
                "subclass": ['temperature', 'humidity', 'pressure', 'gas'],
                "name": name
            }
        }

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]
        self.base_topic = info["base_topic"]
        self.derp_data_key = info["base_topic"] + ".raw"
        self.env_properties = package["env_properties"]

        # tf handling
        tf_package = {
            "type": "robot",
            "subtype": {
                "category": _category,
                "class": _class,
                "subclass": [_subclass]
            },
            "pose": conf["pose"],
            "base_topic": info['base_topic'],
            "name": self.name
        }
        tf_package['host'] = package['device_name']
        tf_package['host_type'] = 'robot'
        if 'host' in conf:
            tf_package['host'] = conf['host']
            tf_package['host_type'] = 'pan_tilt'
        package["tf_declare"].call(tf_package)

        self.publisher = CommlibFactory.getPublisher(
            broker = "redis",
            topic = self.base_topic + ".data"
        )

        if self.info["mode"] == "real":
            from pidevices import BME680
            self.sensor = BME680(self.conf["bus"], self.conf["slave"],
                                 t_oversample=self.conf["t_over"],
                                 h_oversample=self.conf["h_over"],
                                 p_oversample=self.conf["p_over"],
                                 iir_coef=self.conf["iir_coef"],
                                 gas_status=self.conf["g_status"],
                                 name=self.name,
                                 max_data_length=self.conf["max_data_length"])
            self.sensor.set_heating_temp([0], [320])
            self.sensor.set_heating_time([0], [100])
            self.sensor.set_nb_conv(0)

        self.enable_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.enable_callback,
            rpc_name = info["base_topic"] + ".enable"
        )
        self.disable_rpc_server = CommlibFactory.getRPCService(
            broker = "redis",
            callback = self.disable_callback,
            rpc_name = info["base_topic"] + ".disable"
        )

    def sensor_read(self):
        while CommlibFactory.get_tf_affection == None:
            time.sleep(0.1)

        self.logger.info("Env {} sensor read thread started".format(self.info["id"]))
        while self.info["enabled"]:
            time.sleep(1.0 / self.info["hz"])

            val = {
                "temperature": 0,
                "pressure": 0,
                "humidity": 0,
                "gas": 0
            }
            if self.info["mode"] == "mock":
                val["temperature"] = float(random.uniform(30, 10))
                val["pressure"] = float(random.uniform(30, 10))
                val["humidity"] = float(random.uniform(30, 10))
                val["gas"] = float(random.uniform(30, 10))

            elif self.info["mode"] == "simulation":
                while CommlibFactory.get_tf_affection == None:
                    time.sleep(0.1)
                res = CommlibFactory.get_tf_affection.call({
                    'name': self.name
                })

                import statistics
                gas_aff = res["gas"]
                hum_aff = res["humidity"]
                tem_aff = res["temperature"]

                # temperature
                amb = self.env_properties['temperature']
                temps = []
                for a in tem_aff:
                    r = (1 - tem_aff[a]['distance'] / tem_aff[a]['range']) * tem_aff[a]['info']['temperature']
                    temps.append(r)
                val["temperature"] = amb
                if len(temps) != 0:
                    val["temperature"] = amb + statistics.mean(temps)

                # humidity
                ambient = self.env_properties['humidity']
                if len(hum_aff) == 0:
                    val["humidity"] = ambient + random.uniform(-0.5, 0.5)
                vs = []
                for a in hum_aff:
                    vs.append((1 - hum_aff[a]['distance'] / hum_aff[a]['range']) * hum_aff[a]['info']['humidity'])
                if len(vs) > 0:
                    affections = statistics.mean(vs)
                    if ambient > affections:
                        ambient += affections * 0.1
                    else:
                        ambient = affections - (affections - ambient) * 0.1
                val["humidity"] = ambient

                # gas
                ppm = 400 # typical environmental
                for a in gas_aff:
                    rel_range = (1 - gas_aff[a]['distance'] / gas_aff[a]['range'])
                    if gas_aff[a]['type'] == 'human':
                        ppm += 1000.0 * rel_range
                    elif gas_aff[a]['type'] == 'fire':
                        ppm += 5000.0 * rel_range
                val["gas"] = ppm

                # pressure
                val["pressure"] = 27.3 + random.uniform(-3, 3)
            else: # The real deal
                data = self.sensor.read()

                val["temperature"] = data.temp
                val["pressure"] = data.pres
                val["humidity"] = data.hum
                val["gas"] = data.gas

            # Publishing value:
            self.publisher.publish({
                "data": val,
                "timestamp": time.time()
            })

            # Storing value:
            r = CommlibFactory.derp_client.lset(
                self.derp_data_key,
                [{
                    "data": val,
                    "timestamp": time.time()
                }]
            )

        self.logger.info("Env {} sensor read thread stopped".format(self.info["id"]))

    def enable_callback(self, message, meta):
        self.info["enabled"] = True
        self.info["hz"] = message["hz"]
        self.info["queue_size"] = message["queue_size"]

        self.sensor_read_thread = threading.Thread(target = self.sensor_read)
        self.sensor_read_thread.start()
        return {"enabled": True}

    def disable_callback(self, message, meta):
        self.info["enabled"] = False
        self.logger.info("Env {} stops reading".format(self.info["id"]))
        return {"enabled": False}

    def start(self):
        self.enable_rpc_server.run()
        self.disable_rpc_server.run()

        if self.info["enabled"]:
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info("Env {} reads with {} Hz".format(self.info["id"], self.info["hz"]))

    def stop(self):
        self.info["enabled"] = False
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()
