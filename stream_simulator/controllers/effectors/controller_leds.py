"""
File implementing the LedsController class.
"""
#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging

from stream_simulator.base_classes import BaseThing

class LedsController(BaseThing):
    """
    LedsController is a class that manages LED devices in a simulation or mock environment.
    Attributes:
        logger (logging.Logger): Logger for the controller.
        info (dict): Information about the LED device.
        name (str): Name of the LED device.
        base_topic (str): Base topic for communication.
        derp_data_key (str): Key for raw data communication.
        _color (dict): Current color of the LED.
        _luminosity (int): Current luminosity of the LED.
        leds_pub (Publisher): Publisher for LED commands.
        leds_wipe_pub (Publisher): Publisher for LED wipe commands.
        set_rpc_server (RPCService): RPC server for setting LED state.
        get_rpc_server (RPCService): RPC server for getting LED state.
        leds_wipe_server (RPCService): RPC server for wiping LED state.
        enable_rpc_server (RPCService): RPC server for enabling the LED.
        disable_rpc_server (RPCService): RPC server for disabling the LED.
    Methods:
        enable_callback(_): Enables the LED device.
        disable_callback(_): Disables the LED device.
        start(): Starts the LED controller.
        stop(): Stops the LED controller.
        leds_get_callback(_): Gets the current state of the LED.
        leds_set_callback(message): Sets the state of the LED based on the provided message.
        leds_wipe_callback(message): Wipes the LED state based on the provided message.
    """
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        id_ = "d_leds_" + str(BaseThing.id + 1)
        name = id_
        if 'name' in conf:
            name = conf['name']
        _category = "actuator"
        _class = "visual"
        _subclass = "leds"
        _pack = package["name"]
        _namespace = package["namespace"]

        super().__init__(id_, auto_start=False)

        info = {
            "type": "LED",
            "brand": "neopx",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": name,
            "place": conf["place"],
            "id": id_,
            "enabled": True,
            "orientation": float(conf["orientation"]),
            "queue_size": 0,
            "mode": package["mode"],
            "namespace": package["namespace"],
            "device_name": package["device_name"],
            "categorization": {
                "host_type": "robot",
                "place": _pack.split(".")[-1],
                "category": _category,
                "class": _class,
                "subclass": [_subclass],
                "name": name
            }
        }

        self.info = info
        self.name = info["name"]
        self.base_topic = info["base_topic"]
        self.derp_data_key = info["base_topic"] + ".raw"

        self.set_tf_communication(package)
        self.set_simulation_communication(_namespace)

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
            "namespace": _namespace,
            "range": conf["range"]
        }
        tf_package['host'] = package['device_name']
        tf_package['host_type'] = 'robot'
        if 'host' in conf:
            tf_package['host'] = conf['host']
            tf_package['host_type'] = 'pan_tilt'

        self.tf_declare_rpc.call(tf_package)

        self._color = {
                'r': 0.0,
                'g': 0.0,
                'b': 0.0
        }
        self._luminosity = 0

        self.leds_pub = self.commlib_factory.getPublisher(
            topic = self.info['device_name'] + ".leds"
        )

        self.set_rpc_server = self.commlib_factory.getRPCService(
            callback = self.leds_set_callback,
            rpc_name = self.base_topic + ".set"
        )
        self.get_rpc_server = self.commlib_factory.getRPCService(
            callback = self.leds_get_callback,
            rpc_name = self.base_topic + ".get"
        )

        self.commlib_factory.run()

    def start(self):
        """
        Starts the sensor and waits for the simulator to start.

        This method logs a message indicating that the sensor is waiting to start.
        It then enters a loop, sleeping for 1 second at a time, until the simulator
        has started. Once the simulator has started, it logs a message indicating
        that the sensor has started.
        """
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)
        self.logger.info("Sensor %s started", self.name)

    def stop(self):
        """
        Stops the communication library factory.

        This method stops the communication library factory, which is responsible
        for managing the communication with the LED controllers.
        """
        self.commlib_factory.stop()

    def leds_get_callback(self, _):
        """
        Callback function to retrieve the current state of the LEDs.

        Args:
            _ (Any): Unused argument.

        Returns:
            dict: A dictionary containing the current color and luminosity of the LEDs.
                - "color" (str): The current color of the LEDs.
                - "luminosity" (float): The current luminosity of the LEDs.
        """
        return {
            "color": self._color,
            "luminosity": self._luminosity
        }

    def leds_set_callback(self, message):
        """
        Callback function to set the LED values based on the received message.
        Args:
            message (dict): A dictionary containing the LED values. Expected keys are:
                - "r" (float): Red component of the color (default is 0.0).
                - "g" (float): Green component of the color (default is 0.0).
                - "b" (float): Blue component of the color (default is 0.0).
                - "luminosity" (float): Intensity of the LEDs (default is 0.0).
        Returns:
            dict: An empty dictionary.
        Raises:
            Exception: If the message is wrongly formatted.
        """
        try:
            response = message

            r = response["r"] if "r" in response else 0.0
            g = response["g"] if "g" in response else 0.0
            b = response["b"] if "b" in response else 0.0
            intensity = response["luminosity"] if "luminosity" in response else 0.0

            _values = {
                'r': r,
                'g': g,
                'b': b,
                'luminosity': intensity,
            }

            self.commlib_factory.notify_ui(
                type_ = "effector_command",
                data = {
                    "name": self.name,
                    "value": _values
                }
            )

            if self.info["mode"] == "mock":
                pass
            elif self.info["mode"] == "simulation":
                self._color["r"] = r
                self._color["g"] = g
                self._color["b"] = b
                self._luminosity = intensity

            self.logger.info("{%s: New leds command: %s", self.name, message)

        except Exception as e: # pylint: disable=broad-except
            self.logger.error("%s: leds_set is wrongly formatted: %s - %s", \
                self.name, str(e.__class__), str(e))

        return {}
