"""
File that implements the MotionController class.
"""
#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging

from stream_simulator.base_classes import BaseThing

class MotionController(BaseThing):
    """
    MotionController is a class that handles the motion control of a robot using skid steering.
    Attributes:
        logger (logging.Logger): Logger instance for logging messages.
        resolution (int): Resolution of the motion controller.
        info (dict): Dictionary containing information about the motion controller.
        name (str): Name of the motion controller.
        base_topic (str): Base topic for communication.
        derp_data_key (str): Key for raw data communication.
        _linear (float): Linear velocity.
        _angular (float): Angular velocity.
        vel_sub (Subscriber): Subscriber for velocity commands.
        motion_duration_sub (RPCService): RPC service for handling movement duration commands.
        motion_distance_sub (RPCService): RPC service for handling movement distance commands.
        turn_sub (RPCService): RPC service for handling turn commands.
        enable_rpc_server (RPCService): RPC service for enabling the motion controller.
        disable_rpc_server (RPCService): RPC service for disabling the motion controller.
    Methods:
        __init__(conf=None, package=None):
            Initializes the MotionController instance.
        enable_callback(message):
            Callback function to enable the motion controller.
        disable_callback(message):
            Callback function to disable the motion controller.
        start():
            Starts the motion controller.
        stop():
            Stops the motion controller.
        move_duration_callback(message):
        move_distance_callback(message):
            Callback function to handle movement distance messages.
        turn_callback(message):
            Callback function to handle turn messages.
        cmd_vel(message):
            Callback function to handle velocity commands.
    """
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        self.resolution = 0
        id_ = "d_skid_steering_" + str(BaseThing.id + 1)
        name = id_
        if 'name' in conf:
            name = conf['name']
        _category = "actuator"
        _class = "motion"
        _subclass = "twist"
        _pack = package["name"]
        _namespace = package["namespace"]

        super().__init__(id_, auto_start=False)

        info = {
            "type": "SKID_STEER",
            "brand": "twist",
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
            "namespace": _namespace
        }
        tf_package['host'] = package['device_name']
        tf_package['host_type'] = 'robot'

        self.tf_declare_rpc.call(tf_package)

        self._linear = 0
        self._angular = 0

        self.vel_sub = self.commlib_factory.get_subscriber(
            topic = self.base_topic + ".set",
            callback = self.cmd_vel
        )
        self.motion_duration_sub = self.commlib_factory.get_rpc_service(
            rpc_name = self.base_topic + ".move.duration",
            callback = self.move_duration_callback
        )
        self.motion_distance_sub = self.commlib_factory.get_rpc_service(
            rpc_name = self.base_topic + ".move.distance",
            callback = self.move_distance_callback
        )
        self.turn_sub = self.commlib_factory.get_rpc_service(
            rpc_name = self.base_topic + ".move.turn",
            callback = self.turn_callback
        )

        self.commlib_factory.run()

    def get_linear(self):
        """
        Returns the linear velocity of the robot.

        Returns:
            float: The linear velocity of the robot.
        """
        return self._linear

    def get_angular(self):
        """
        Returns the angular velocity of the robot.

        Returns:
            float: The angular velocity of the robot.
        """
        return self._angular

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

    def move_duration_callback(self, message):
        """
        Callback function to handle movement duration messages.
        Args:
            message (dict): A dictionary containing movement parameters:
                - 'linear' (float or str): Linear movement value.
                - 'angular' (float or str): Angular movement value.
                - 'duration' (float or str): Duration for the movement.
        Raises:
            ValueError: If 'linear', 'angular', or 'duration' are not valid float values.
        Logs:
            Error: If the message is wrongly formatted.
        """
        try:
            response = message

            # Checks for types
            try:
                float(response['linear'])
                float(response['angular'])
                float(response['duration'])
            except Exception as exe: # pylint: disable=broad-exception-caught
                if not response['linear'].isdigit():
                    raise ValueError("Linear is no integer nor float") from exe
                if not response['angular'].isdigit():
                    raise ValueError("Angular is no integer nor float") from exe
                if not response['duration'].isdigit():
                    raise ValueError("Angular is no integer nor float") from exe

            self._linear = response['linear']
            self._angular = response['angular']
            motion_started = time.time()
            while True:
                if time.time() - motion_started >= response["duration"]:
                    self._linear = 0
                    self._angular = 0
                    break
                time.sleep(0.05)
        except Exception as e: # pylint: disable=broad-exception-caught
            self.logger.error("%s: move_duration is wrongly formatted: %s - %s", \
                self.name, str(e.__class__), str(e))
            return {"status": "failed"}

        return {"status": "done"}

    def move_distance_callback(self, message):
        """
        Callback function to handle movement distance messages.
        Args:
            message (dict): A dictionary containing movement parameters.
                - 'linear' (float or str): The linear speed of the movement.
                - 'distance' (float or str): The distance to be moved.
        Returns:
            dict: A dictionary indicating the status of the operation.
                - 'status' (str): "done" if the operation was successful, "failed" otherwise.
        Raises:
            ValueError: If 'linear' or 'distance' are not valid float or integer values.
        """
        try:
            response = message
            # Checks for types
            print(response)
            try:
                float(response['linear'])
                float(response['distance'])
            except Exception as exe: # pylint: disable=broad-exception-caught
                if not response['linear'].isdigit():
                    raise ValueError("Linear is no integer nor float") from exe
                if not response['distance'].isdigit():
                    raise ValueError("Distance is no integer nor float") from exe

            self._linear = response['linear']
            self._angular = 0
            # print("time to sleep is: ", response["distance"] / response["linear"])
            time.sleep(response["distance"] / response["linear"])
            self._linear = 0
        except Exception as e: # pylint: disable=broad-exception-caught
            self.logger.error("%s: move_duration is wrongly formatted: %s - %s", \
                self.name, str(e.__class__), str(e))
            return {"status": "failed"}

        return {"status": "done"}

    def turn_callback(self, message):
        """
        Callback function to handle turning motion based on the provided message.
        Args:
            message (dict): A dictionary containing the keys 'angular' and 'angle'.
                            'angular' represents the angular velocity.
                            'angle' represents the angle to turn.
        Returns:
            dict: A dictionary with the status of the operation. 
                  Returns {"status": "done"} if successful, otherwise {"status": "failed"}.
        Raises:
            ValueError: If 'angular' or 'angle' in the message are not valid numbers.
        """
        try:
            response = message

            # Checks for types
            try:
                float(response['angular'])
                float(response['angle'])
            except Exception as exe: # pylint: disable=broad-exception-caught
                if not response['angular'].isdigit():
                    raise ValueError("Angular is no integer nor float") from exe
                if not response['angle'].isdigit():
                    raise ValueError("Angle is no integer nor float") from exe

            self._linear = 0
            self._angular = response['angular']
            # print("time to sleep is: ", response["angle"] / response["angular"])
            time.sleep(response["angle"] / response["angular"])
            self._angular = 0
        except Exception as e: # pylint: disable=broad-exception-caught
            self.logger.error("%s: turn is wrongly formatted: %s - %s", \
                self.name, str(e.__class__), str(e))
            return {"status": "failed"}

        return {"status": "done"}

    def cmd_vel(self, message):
        """
        Processes a velocity command message and updates the controller's linear 
        and angular velocities.
        Args:
            message (dict): A dictionary containing the velocity command with keys 
            'linear', 'angular', and 'raw'.
        Raises:
            Exception: If 'linear' or 'angular' values are not integers or floats.
        Notes:
            - The 'linear' and 'angular' values are expected to be convertible to float.
            - Logs an error if the message is wrongly formatted.
        """
        try:
            response = message

            # Checks for types
            try:
                float(response['linear'])
                float(response['angular'])
            except Exception as exc: # pylint: disable=broad-exception-caught
                if not response['linear'].isdigit():
                    raise Exception("Linear is no integer nor float") from exc # pylint: disable=broad-exception-raised
                if not response['angular'].isdigit():
                    raise Exception("Angular is no integer nor float") from exc # pylint: disable=broad-exception-raised

            self._linear = response['linear']
            self._angular = response['angular']
        except Exception as e: # pylint: disable=broad-exception-caught
            self.logger.error("%s: cmd_vel is wrongly formatted: %s - %s", \
                self.name, str(e.__class__), str(e))
