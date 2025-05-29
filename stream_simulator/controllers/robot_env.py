"""
File that contains the environment sensor controller.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging
import threading
import random

from stream_simulator.base_classes import BaseThing

class EnvController(BaseThing):
    """
    EnvController is a class that simulates an environmental sensor. It inherits from BaseThing 
    and is responsible for
    initializing the sensor, setting up communication, and reading sensor data.
    Attributes:
        logger (logging.Logger): Logger for the controller.
        info (dict): Information about the sensor.
        name (str): Name of the sensor.
        base_topic (str): Base topic for communication.
        derp_data_key (str): Key for raw data.
        env_properties (dict): Environmental properties from the package.
        publisher (Publisher): Publisher for sensor data.
        enable_rpc_server (RPCService): RPC service for enabling the sensor.
        disable_rpc_server (RPCService): RPC service for disabling the sensor.
        sensor_read_thread (threading.Thread): Thread for reading sensor data.
    Methods:
        __init__(conf=None, package=None): Initializes the EnvController with configuration and
        package details.
        sensor_read(): Reads sensor data and publishes it at a specified frequency.
        enable_callback(message): Callback to enable the sensor.
        disable_callback(message): Callback to disable the sensor.
        start(): Starts the sensor.
        stop(): Stops the sensor.
    """
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        id_ = "d_env_" + str(BaseThing.id + 1)
        name = id_
        if 'name' in conf:
            name = conf['name']
        _category = "sensor"
        _class = "env"
        _subclass = "temp_hum_pressure_gas"
        _pack = package["name"]
        _namespace = package["namespace"]

        super().__init__(id_, auto_start=False)
        self.set_simulation_communication(_namespace)

        info = {
            "type": "ENV",
            "brand": "bme680",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": name,
            "place": conf["place"],
            "id": id_,
            "enabled": True,
            "orientation": float(conf["orientation"]),
            "hz": conf["hz"],
            "mode": package["mode"],
            "namespace": package["namespace"],
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
        self.base_topic = info["base_topic"]
        self.derp_data_key = info["base_topic"] + ".raw"
        self.env_properties = package["env_properties"]

        self.set_tf_communication(package)

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
            "name": self.name,
            "namespace": _namespace
        }
        tf_package['host'] = package['device_name']
        tf_package['host_type'] = 'robot'
        if 'host' in conf:
            tf_package['host'] = conf['host']
            tf_package['host_type'] = 'pan_tilt'

        self.publisher = self.commlib_factory.get_publisher(
            topic = self.base_topic + ".data"
        )

        self.commlib_factory.run()

        self.tf_declare_rpc.call(tf_package)

        self.sensor_read_thread = None
        self.stopped = False

        self.dynamic_value = {
            "temperature": None,
            "pressure": None,
            "humidity": None,
            "gas": None
        }

    def sensor_read(self):
        """
        Reads sensor data in a loop and publishes it at a specified frequency.
        This method starts a thread that continuously reads sensor data based on the mode specified
        in `self.info["mode"]`.
        It supports two modes: "mock" and "simulation". In "mock" mode, it generates random sensor 
        values. In "simulation" mode, it retrieves sensor data from a remote procedure call (RPC)
        and calculates the values based on environmental properties and affections.
        The sensor data includes temperature, pressure, humidity, and gas levels. 
        The data is published with a timestamp using `self.publisher.publish()`.
        The loop runs until `self.info["enabled"]` is set to False.
        Logging:
            Logs the start and stop of the sensor read thread.
        Raises:
            KeyError: If required keys are missing in `self.info` or `self.env_properties`.
        Note:
            This method assumes that `self.logger`, `self.info`, `self.tf_affection_rpc`, 
            `self.env_properties`, and `self.publisher` are properly initialized before calling 
            this method.
        """
        self.logger.info("Env %s sensor read thread started", self.info["id"])
        while self.info["enabled"]:
            time.sleep(1.0 / self.info["hz"])

            val = {
                "temperature": 0,
                "humidity": 0,
                "gas": 0
            }
            if self.info["mode"] == "mock":
                val["temperature"] = float(random.uniform(30, 10))
                val["pressure"] = float(random.uniform(30, 10))
                val["humidity"] = float(random.uniform(30, 10))
                val["gas"] = float(random.uniform(30, 10))

            elif self.info["mode"] == "simulation":
                res = self.tf_affection_rpc.call({
                    'name': self.name
                })

                gas_aff = res['affections']["gas"]
                hum_aff = res['affections']["humidity"]
                tem_aff = res['affections']["temperature"]

                # temperature
                amb = res['env_properties']['temperature']
                temps = []
                for a in tem_aff:
                    r = (1 - tem_aff[a]['distance'] / tem_aff[a]['range']) * \
                        tem_aff[a]['info']['temperature']
                    temps.append(r)

                final_temp = amb
                if len(temps) != 0:
                    final_temp = max(temps)
                final_temp = amb if amb > final_temp else final_temp
                if self.dynamic_value['temperature'] is None:
                    self.dynamic_value['temperature'] = final_temp
                else:
                    self.dynamic_value['temperature'] += \
                        (final_temp - self.dynamic_value['temperature'])/6
                val["temperature"] = self.dynamic_value['temperature'] + random.uniform(-0.1, 0.1)

                # humidity
                ambient = res['env_properties']['humidity']
                if len(hum_aff) == 0:
                    val["humidity"] = ambient + random.uniform(-0.5, 0.5)
                vs = []
                affections = 0
                for a in hum_aff:
                    vs.append((1 - hum_aff[a]['distance'] / hum_aff[a]['range']) * \
                        hum_aff[a]['info']['humidity'])
                if len(vs) > 0:
                    affections = max(vs)

                final_hum = ambient if ambient > affections else affections
                if self.dynamic_value['humidity'] is None:
                    self.dynamic_value['humidity'] = final_hum
                else:
                    self.dynamic_value['humidity'] += (final_hum - self.dynamic_value['humidity'])/6
                val["humidity"] = self.dynamic_value['humidity'] + random.uniform(-0.1, 0.1)

                # gas
                ppm = 400 # typical environmental
                for a in gas_aff:
                    rel_range = 1 - gas_aff[a]['distance'] / gas_aff[a]['range']
                    if gas_aff[a]['type'] == 'human':
                        ppm += 1000.0 * rel_range
                    elif gas_aff[a]['type'] == 'fire':
                        ppm += 5000.0 * rel_range

                final_gas = ppm
                if self.dynamic_value['gas'] is None:
                    self.dynamic_value['gas'] = final_gas
                else:
                    self.dynamic_value['gas'] += (final_gas - self.dynamic_value['gas'])/6
                val["gas"] = self.dynamic_value['gas'] + random.uniform(-5, 5)

                # pressure
                val["pressure"] = 27.3 + random.uniform(-3, 3)

            # Publishing value:
            # print(val)
            self.publisher.publish({
                "data": val,
                "timestamp": time.time()
            })

        self.logger.info("Env %s sensor read thread stopped", self.info["id"])
        self.stopped = True

    def start(self):
        """
        Starts the sensor and begins reading data if enabled.
        This method logs the initial state of the sensor and waits for the simulator to start.
        Once the simulator has started, it checks if the sensor is enabled. If enabled, it starts
        a new thread to read sensor data at the specified frequency.
        Logging:
            Logs the waiting state of the sensor.
            Logs when the sensor has started.
            Logs the sensor reading frequency if the sensor is enabled.
        Threading:
            Starts a new thread to read sensor data if the sensor is enabled.
        """
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)
        self.logger.info("Sensor %s started", self.name)

        if self.info["enabled"]:
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info("Env %s reads with %s Hz", self.info["id"], self.info["hz"])

    def stop(self):
        """
        Stops the sensor controller by disabling it and stopping the communication library.

        This method sets the "enabled" flag in the info dictionary to False, indicating that the 
        sensor controller is no longer active. 
        It also calls the stop method on the commlib_factory to halt any ongoing communication
        processes.
        """
        self.info["enabled"] = False
        while not self.stopped:
            time.sleep(0.1)
        self.logger.warning("Sensor %s stopped", self.name)
        self.commlib_factory.stop()
