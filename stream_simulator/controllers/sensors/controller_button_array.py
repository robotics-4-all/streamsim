"""
File that contains the button array controller.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging
import threading
import random

from stream_simulator.base_classes import BaseThing

def current_milli_time():
    """
    Returns the current time in milliseconds since the epoch.

    This function uses the `time` module to get the current time in seconds
    since the epoch, multiplies it by 1000 to convert it to milliseconds,
    and then rounds and converts it to an integer.

    Returns:
        int: The current time in milliseconds.
    """
    return int(round(time.time() * 1000))

class ButtonArrayController(BaseThing):
    """
    ButtonArrayController is a class that manages a button array sensor. It handles the 
    initialization, configuration, and communication of the button array sensor.

    Attributes:
        logger (logging.Logger): Logger for the controller.
        info (dict): Information about the button array sensor.
        name (str): Name of the button array sensor.
        conf (dict): Sensor configuration.
        base_topic (str): Base topic for communication.
        buttons_base_topics (list): List of base topics for each button.
        publishers (dict): Dictionary of publishers for each button.
        number_of_buttons (int): Number of buttons in the array.
        values (list): List of boolean values representing the state of each button.
        button_places (list): List of places for each button.
        prev (int): Previous state of the button array.
        enable_rpc_server (RPCService): RPC service for enabling the sensor.
        disable_rpc_server (RPCService): RPC service for disabling the sensor.
        sim_button_pressed_sub (Subscriber): Subscriber for simulated button presses.
        sensor_read_thread (threading.Thread): Thread for reading sensor data.

    Methods:
        __init__(conf=None, package=None): Initializes the ButtonArrayController with the given 
        configuration and package.
        dispatch_information(_data, _button): Publishes button data to the stream.
        sim_button_pressed(data): Handles simulated button presses.
        sensor_read(): Reads sensor data and dispatches information.
        start(): Starts the sensor.
        stop(): Stops the sensor.
        enable_callback(message): Callback for enabling the sensor.
        disable_callback(message): Callback for disabling the sensor.
    """
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        id_ = "d_button_array_" + str(BaseThing.id + 1)

        name = id_
        _category = "sensor"
        _class = "button_array"
        _subclass = "tactile"
        _pack = package["name"]
        _namespace = package["namespace"]

        super().__init__(id_, auto_start=False)

        info = {
            "type": "BUTTON_ARRAY",
            "brand": "simple",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": "button_array_" + str(id_),
            "place": "UNKNOWN",
            "id": id_,
            "enabled": True,
            "orientation": 0,
            "hz": 4,
            "mode": package["mode"],
            "namespace": package["namespace"],
            "sensor_configuration": conf["sensor_configuration"],
            "device_name": package["device_name"]
        }

        self.set_tf_communication(package)
        self.set_simulation_communication(_namespace)

        self.info = info
        self.name = info["name"]
        self.conf = info["sensor_configuration"]
        self.base_topic = info["base_topic"]

        self.buttons_base_topics = self.conf["base_topics"]
        self.publishers = {}

        self.number_of_buttons = len(self.conf["places"])
        self.values = [True] * self.number_of_buttons         # multiple values
        self.button_places = self.conf["places"]
        self.prev = 0

        for b in self.buttons_base_topics:
            self.publishers[b] = self.commlib_factory.get_publisher(
                topic = self.buttons_base_topics[b] + ".data"
            )

        if self.info["mode"] == "simulation":
            self.sim_button_pressed_sub = self.commlib_factory.get_subscriber(
                topic = _namespace + "." + self.info['device_name'] + ".buttons_sim.internal",
                callback = self.sim_button_pressed
            )

        self.commlib_factory.run()

        self.sensor_read_thread = None

    def dispatch_information(self, _data, _button):
        """
        Dispatches information by publishing data to the specified button's stream.

        Args:
            _data (any): The data to be published.
            _button (str): The identifier for the button whose stream will receive the data.

        Returns:
            None
        """
        # Publish to stream
        self.publishers[_button].publish({
            "data": _data,
            "timestamp": time.time()
        })

    def sim_button_pressed(self, data):
        """
        Handles the simulated button press event.

        This method logs a warning indicating that a button has been pressed in the simulation.
        It then dispatches information about the button press and release events.

        Args:
            data (dict): A dictionary containing information about the button event.
                 Expected to have a key "button" which indicates the button identifier.

        """
        self.logger.warning("Button controller: Pressed from sim! %s", data)
        # Simulated press
        self.dispatch_information(1, data["button"])
        time.sleep(0.1)
        # Simulated release
        self.dispatch_information(0, data["button"])

    def sensor_read(self):
        """
        Reads sensor data for a button and dispatches the information.

        This method starts a thread that continuously reads sensor data for a button
        at a frequency specified by `self.info["hz"]`. If the sensor is in "mock" mode,
        it generates random values for the button state and randomly selects a button
        place to dispatch the information.

        The method logs the start and stop of the sensor read thread.

        Attributes:
            self.info (dict): A dictionary containing sensor configuration.
                - "id" (str): The identifier for the button.
                - "enabled" (bool): Flag to enable or disable the sensor read thread.
                - "hz" (float): Frequency at which the sensor data is read.
                - "mode" (str): Mode of operation, e.g., "mock".
            self.button_places (list): A list of possible button places.
            self.logger (Logger): Logger instance for logging information.

        Dispatches:
            Calls `self.dispatch_information` with the generated value and button place.
        """
        self.logger.info("Button %s sensor read thread started", self.info['id'])
        while self.info["enabled"]:
            time.sleep(1.0 / self.info["hz"])
            if self.info["mode"] == "mock":
                _val = float(random.randint(0,1))
                _place = random.randint(0, len(self.button_places) - 1)

                self.dispatch_information(_val, self.button_places[_place])

        self.logger.info("Button %s sensor read thread stopped", self.info['id'])

    def start(self):
        """
        Starts the sensor and begins reading data if the simulator has started.

        This method logs the initial state of the sensor and waits for the simulator to start.
        Once the simulator has started, it logs the start event and, if the sensor is in "mock" 
        mode, it starts a new thread to read sensor data at the specified frequency.

        Attributes:
            simulator_started (bool): A flag indicating whether the simulator has started.
            info (dict): A dictionary containing sensor information, including mode, id, and hz.
            sensor_read_thread (threading.Thread): The thread responsible for reading sensor data.
        """
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)
        self.logger.info("Sensor %s started", self.name)

        if self.info["mode"] == "mock":
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info("Button %s reads with %s Hz", self.info['id'], self.info['hz'])

    def stop(self):
        """
        Stops the button array controller.

        This method disables the button array controller by setting the "enabled" 
        key in the info dictionary to False. It also stops the communication 
        library factory associated with the controller.
        """
        self.info["enabled"] = False
        self.commlib_factory.stop()
