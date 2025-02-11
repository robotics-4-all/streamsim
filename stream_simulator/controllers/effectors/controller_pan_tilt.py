"""
File that contains the PanTiltController class.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging

from stream_simulator.base_classes import BaseThing

class PanTiltController(BaseThing):
    """
    PanTiltController is a class that controls a pan-tilt mechanism for a robot.
    Attributes:
        logger (logging.Logger): Logger for the controller.
        info (dict): Information about the pan-tilt mechanism.
        name (str): Name of the pan-tilt mechanism.
        base_topic (str): Base topic for communication.
        derp_data_key (str): Key for raw data communication.
        _yaw (float): Current yaw angle.
        _pitch (float): Current pitch angle.
        pan_tilt_set_sub (Subscriber): Subscriber for setting pan-tilt angles.
        enable_rpc_server (RPCService): RPC server for enabling the mechanism.
        disable_rpc_server (RPCService): RPC server for disabling the mechanism.
        data_publisher (Publisher): Publisher for pan-tilt data.
    Methods:
        enable_callback(message): Enables the pan-tilt mechanism.
        disable_callback(message): Disables the pan-tilt mechanism.
        start(): Starts the pan-tilt controller.
        stop(): Stops the pan-tilt controller.
        pan_tilt_set_callback(message): Sets the pan and tilt angles based on the message.
    """
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        id_ = "d_pan_tilt_" + str(BaseThing.id + 1)
        name = id_
        if 'name' in conf:
            name = conf['name']
        _category = "actuator"
        _class = "motion"
        _subclass = "pan_tilt"
        _pack = package["name"]
        _namespace = package["namespace"]
        super().__init__(id_, auto_start=False)

        info = {
            "type": "PAN_TILT",
            "brand": "pca9685",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": name,
            "place": conf["place"],
            "id": id_,
            "enabled": True,
            "orientation": float(conf["orientation"]),
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
            "namespace": _namespace
        }
        tf_package['host'] = package['device_name']
        tf_package['host_type'] = 'robot'
        if 'host' in conf:
            tf_package['host'] = conf['host']
            tf_package['host_type'] = 'pan_tilt'

        self.tf_declare_rpc.call(tf_package)
        # self.tf_declare_pub.publish(tf_package)

        # init values
        self._yaw = 0.0
        self._pitch = 0.0

        self.pan_tilt_set_sub = self.commlib_factory.get_subscriber(
            topic = self.base_topic + ".set",
            callback = self.pan_tilt_set_callback
        )
        self.data_publisher = self.commlib_factory.get_publisher(
            topic = self.base_topic + ".data"
        )
        self.state_publisher = self.commlib_factory.get_publisher(
            topic=self.base_topic + ".state"
        )

        self.commlib_factory.run()

    def start(self):
        """
        Starts the sensor and waits for the simulator to start.

        This method logs a message indicating that the sensor is waiting to start.
        It then enters a loop, repeatedly checking if the simulator has started.
        Once the simulator has started, it logs a message indicating that the sensor has started.

        Returns:
            None
        """
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)
        self.logger.info("Sensor %s started", self.name)

    def stop(self):
        """
        Stops the pan-tilt controller by invoking the stop method of the commlib_factory.

        This method is used to halt any ongoing operations or movements of the pan-tilt mechanism.
        """
        self.commlib_factory.stop()

    def pan_tilt_set_callback(self, message):
        """
        Callback function to handle incoming pan and tilt commands.
        Args:
            message (dict): A dictionary containing the pan and tilt values. 
                            Expected keys are 'pan' and 'tilt'.
        Raises:
            Exception: If the message is not properly formatted or does not contain the 
            expected keys.
        The function updates the internal yaw and pitch values based on the incoming message.
        It then publishes the new pan and tilt values along with the name of the effector.
        Logs the new pan and tilt command or an error if the message is wrongly formatted.
        """
        try:
            response = message
            self._yaw = response['pan']
            self._pitch = response['tilt']

            if self.info["mode"] == "mock":
                pass
            elif self.info["mode"] == "simulation":
                pass

            self.data_publisher.publish({
                'pan': self._yaw,
                'tilt': self._pitch,
                'name': self.name
            })
            self.state_publisher.publish({
                'state': {
                    'pan': self._yaw,
                    'tilt': self._pitch,
                    'name': self.name
                }
            })

            self.logger.info("%s: New pan tilt command: %s, %s", self.name, self._yaw, self._pitch)
        except Exception as e: # pylint: disable=broad-except
            self.logger.error("%s: pan_tilt is wrongly formatted: %s - %s", \
                self.name, str(e.__class__), str(e))
