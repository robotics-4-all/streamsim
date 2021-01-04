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

class RfidReaderController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = Logger(conf["name"])
        else:
            self.logger = package["logger"]

        super(self.__class__, self).__init__()
        id = BaseThing.id

        info = {
            "type": "RFID_READER",
            "brand": "unknown",
            "base_topic": package["name"] + ".sensor.rf.rfid_reader.d" + str(id),
            "name": "rfid_reader_" + str(id),
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
            "temperature": conf["sim_temperature"],
            "humidity": conf["sim_humidity"],
            "gas": conf["sim_air_quality"],
            "pressure": conf["sim_pressure"],
            "endpoints":{
                "enable": "rpc",
                "disable": "rpc",
                "data": "publisher"
            },
            "data_models": {
                "data": {
                    "data": ["temperature", "pressure", "humidity", "gas"]
                }
            }
        }

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]
        self.base_topic = info["base_topic"]
        self.derp_data_key = info["base_topic"] + ".raw"

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
                val["temperature"] = self.info["temperature"] + \
                    random.uniform(-3, 3)
                val["pressure"] = self.info["pressure"] + random.uniform(-3, 3)
                val["humidity"] = self.info["humidity"] + random.uniform(-3, 3)
                val["gas"] = self.info["gas"] + random.uniform(-3, 3)
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
