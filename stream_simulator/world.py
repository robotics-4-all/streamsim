"""
This file contains the World class, which represents a simulated environment with various 
properties, devices, and actors. The World class is responsible for loading the environment 
configuration, initializing properties, devices, and actors, and setting up the map and obstacles 
based on the configuration. It also registers controllers for devices and actors, and starts the 
communication library factory.
"""
#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging
import math
import threading
import numpy

from stream_simulator.connectivity import CommlibFactory

class World:
    """
    The World class represents a simulated environment with various properties, devices, and actors.
    Attributes:
        commlib_factory (CommlibFactory): Factory for communication library.
        logger (Logger): Logger for the World class.
        uid (str): Unique identifier for the world.
        configuration (dict): Configuration settings for the environment.
        tf_base (str): Base topic for transformation.
        tf_declare_rpc (RPCClient): RPC client for declaring transformations.
        name (str): Name of the world.
        env_properties (dict): Environmental properties such as temperature, humidity, 
            luminosity, and pH.
        env_devices (list): List of environmental devices.
        actors (list): List of actors in the environment.
        devices (list): List of devices in the environment.
        controllers (dict): Dictionary of controllers for the devices.
        devices_rpc_server (RPCService): RPC service for device callbacks.
        width (int): Width of the map.
        height (int): Height of the map.
        map (numpy.ndarray): Map of the environment.
        resolution (int): Resolution of the map.
        obstacles (list): List of obstacles in the map.
        actors_configurations (list): List of actor configurations.
        actors_controllers (dict): Dictionary of controllers for the actors.
    Methods:
        __init__(uid):
            Initializes the World instance with a unique identifier.
        load_environment(configuration=None):
            Loads the environment configuration and initializes properties, devices, and actors.
        devices_callback(message):
            Callback function for device RPC service.
        setup():
            Sets up the map and obstacles based on the configuration.
        register_controller(c):
            Registers a controller for a device.
        device_lookup():
            Looks up and registers all devices in the environment.
        actors_lookup():
            Looks up and registers all actors in the environment.
        stop():
            Stops the communication library factory.
    """
    def __init__(self, uid, mqtt_notifier = None):
        self.commlib_factory = CommlibFactory(node_name = "World")
        self.logger = logging.getLogger(__name__)
        self.uid = uid
        self.configuration = None
        self.tf_base = None
        self.tf_declare_rpc = None
        self.env_devices = None
        self.actors = None
        self.devices = None
        self.controllers = None
        self.devices_rpc_server = None
        self.width = None
        self.height = None
        self.map = None
        self.resolution = None
        self.obstacles = None
        self.actors_configurations = None
        self.actors_controllers = None
        self.mqtt_notifier = mqtt_notifier

        self.name = self.uid
        self.env_properties = {
            'temperature': 20,
            'humidity': 50,
            'luminosity': 100,
            'ph': 7,
        }

    def load_environment(self, configuration = None):
        """
        Loads the environment configuration and initializes various components.
        Args:
            configuration (dict, optional): The configuration dictionary containing
                environment settings, properties, devices, and actors.
        Attributes:
            configuration (dict): The configuration dictionary.
            tf_base (str): The base name for TensorFlow-related RPCs.
            tf_declare_rpc (RPCClient): The RPC client for declaring TensorFlow-related services.
            env_properties (dict): The properties of the environment.
            env_devices (list): The list of environment devices.
            actors (list): The list of actors in the environment.
            devices (list): The list of devices in the environment.
            controllers (dict): The dictionary of controllers in the environment.
            devices_rpc_server (RPCService): The RPC service for handling device-related callbacks.
            actors_configurations (list): The list of actor configurations.
            actors_controllers (dict): The dictionary of actor controllers.
        Methods:
            setup(): Sets up the environment.
            device_lookup(): Looks up and initializes devices.
            actors_lookup(): Looks up and initializes actors.
        """
        self.configuration = configuration

        self.tf_base = self.configuration['tf_base']
        self.tf_declare_rpc = self.commlib_factory.getRPCClient(
            rpc_name = self.tf_base + ".declare"
        )

        if "world" in self.configuration:
            if 'properties' in self.configuration['world']:
                prop = self.configuration['world']['properties']
                for p, _ in self.env_properties.items():
                    if p in prop:
                        self.env_properties[p] = prop[p]

        self.env_devices = []
        if "env_devices" in self.configuration:
            self.env_devices = self.configuration["env_devices"]

        self.actors = []
        if "actors" in self.configuration:
            self.actors = self.configuration["actors"]

        # self.logger.info("World loaded")
        self.devices = []
        self.controllers = {}

        self.devices_rpc_server = self.commlib_factory.getRPCService(
            callback = self.devices_callback,
            rpc_name = \
                f"{self.tf_base.split('.')[0]}.{self.name}.nodes_detector.get_connected_devices"
        )

        self.setup()
        self.device_lookup()

        self.actors_configurations = []
        self.actors_controllers = {}
        self.actors_lookup()

        # All communications have been set up, start the factory
        self.commlib_factory.run()

        # Start all controllers
        for c in self.controllers:
            # start controllers in threads
            threading.Thread(target = self.controllers[c].start).start()

    def devices_callback(self, _):
        """
        Callback function to handle device messages.

        Args:
            message (Any): The incoming message related to devices.

        Returns:
            dict: A dictionary containing the current devices and a timestamp.
                - "devices" (list): The list of current devices.
                - "timestamp" (float): The current time in seconds since the epoch.
        """
        return {
            "devices": self.devices,
            "timestamp": time.time()
        }

    def setup(self):
        """
        Sets up the world map and obstacles based on the configuration.
        Initializes the width, height, resolution, and map attributes. If the configuration
        contains map information, it sets the resolution, width, and height of the map and
        creates a numpy array to represent the map. If obstacles are defined in the configuration,
        it adds them to the map.
        The obstacles are defined as lines with start and end coordinates (x1, y1) and (x2, y2).
        The method handles both vertical and horizontal lines, as well as tilted lines, and marks
        the corresponding positions in the map array.
        Attributes:
            width (int): The width of the map in grid cells.
            height (int): The height of the map in grid cells.
            map (numpy.ndarray): A 2D array representing the map grid.
            resolution (int): The resolution of the map.
            obstacles (list): A list of obstacles defined in the configuration.
        Returns:
            None
        """
        self.width = 0
        self.height = 0
        self.map = None
        self.resolution = 0
        self.obstacles = []
        if 'map' in self.configuration:
            self.resolution = self.configuration['map']['resolution']
            self.width = int(self.configuration['map']['width'] / self.resolution)
            self.height = int(self.configuration['map']['height'] / self.resolution)
            self.map = numpy.zeros((self.width, self.height))

            if 'obstacles' not in self.configuration['map']:
                return

            # Add obstacles information in map
            self.obstacles = self.configuration['map']['obstacles']['lines']
            for obst in self.obstacles:
                x1 = max(min(int(obst['x1']), self.width - 1), 0)
                x2 = max(min(int(obst['x2']), self.width - 1), 0)
                y1 = max(min(int(obst['y1']), self.height - 1), 0)
                y2 = max(min(int(obst['y2']), self.height - 1), 0)

                if x1 == x2:
                    if y1 > y2:
                        tmp = y2
                        y2 = y1
                        y1 = tmp
                    for i in range(y1, y2 + 1):
                        self.map[x1, i] = 1
                elif y1 == y2:
                    if x1 > x2:
                        tmp = x2
                        x2 = x1
                        x1 = tmp
                    for i in range(x1, x2 + 1):
                        self.map[i, y1] = 1
                else: # we have a tilted line
                    f_ang = math.atan2(y2 - y1, x2 - x1)
                    dist = math.sqrt(
                        math.pow(x2 - x1, 2) + math.pow(y2 - y1, 2)
                    )
                    dist = int(dist) + 1
                    d = 0
                    while d <= dist:
                        tmpx = int(x1 + d * math.cos(f_ang))
                        tmpy = int(y1 + d * math.sin(f_ang))
                        d += 1
                        self.map[tmpx, tmpy] = 1

    def register_controller(self, c):
        """
        Registers a controller with the world.

        Args:
            c (Controller): The controller to be registered. It must have 'name' and 
                'info' attributes.

        Raises:
            Logs an error if a controller with the same name is already registered.
        """
        if c.name in self.controllers:
            self.logger.error("Device %s declared twice", c.name)
        else:
            self.devices.append(c.info)
            self.controllers[c.name] = c

    def device_lookup(self):
        """
        Registers controllers for various environmental devices based on the configuration.
        This method initializes a dictionary of parameters and imports the necessary
        controllers from the `stream_simulator` module. It then iterates over the
        environmental devices specified in `self.env_devices`, and for each device,
        it registers the appropriate controller.
        The method performs the following steps:
        1. Initializes a dictionary `p` with configuration parameters.
        2. Dynamically imports the `stream_simulator` module and retrieves the `controllers` 
            attribute.
        3. Creates a mapping of device types to their corresponding controller classes.
        4. Iterates over the devices in `self.env_devices`.
        5. For each device, ensures that the 'theta' attribute in the device's pose is set.
        6. Registers the controller for the device using the `register_controller` method.
        Attributes:
            self.configuration (dict): The configuration dictionary for the simulation.
            self.tf_base (str): The base topic for transformation-related RPCs.
            self.env_properties (dict): The properties of the environment.
            self.map (dict): The map of the environment.
            self.resolution (float): The resolution of the environment.
            self.env_devices (dict): A dictionary of environmental devices to be registered.
        Raises:
            AttributeError: If a required attribute is missing from the device configuration.
        """
        p = {
            "base": "world",
            "logger": None,
            "namespace": self.configuration["simulation"]["name"],
            'tf_declare_rpc_topic': self.tf_base + '.declare',
            'tf_affection_rpc_topic': self.tf_base + '.get_affections',
            'env': self.env_properties,
            "map": self.map,
            "resolution": self.resolution
        }
        str_sim = __import__("stream_simulator")
        str_contro = getattr(str_sim, "controllers")
        mapping = {
           "relays": getattr(str_contro, "EnvRelayController"),
           "ph_sensors": getattr(str_contro, "EnvPhSensorController"),
           "temperature_sensors": getattr(str_contro, "EnvTemperatureSensorController"),
           "humidity_sensors": getattr(str_contro, "EnvHumiditySensorController"),
           "gas_sensors": getattr(str_contro, "EnvGasSensorController"),
           "camera_sensors": getattr(str_contro, "EnvCameraController"),
           "distance_sensors": getattr(str_contro, "EnvDistanceController"),
           "alarms_linear": getattr(str_contro, "EnvLinearAlarmController"),
           "alarms_area": getattr(str_contro, "EnvAreaAlarmController"),
           "ambient_light_sensor": getattr(str_contro, "EnvAmbientLightController"),
           "pan_tilt": getattr(str_contro, "EnvPanTiltController"),
           "speakers": getattr(str_contro, "EnvSpeakerController"),
           "lights": getattr(str_contro, "EnvLightController"),
           "thermostats": getattr(str_contro, "EnvThermostatController"),
           "microphones": getattr(str_contro, "EnvMicrophoneController"),
           "humidifiers": getattr(str_contro, "EnvHumidifierController"),
        }
        for d in self.env_devices:
            devices = self.env_devices[d]
            for dev in devices:
                # Handle pose theta
                if 'theta' not in dev['pose']:
                    dev['pose']['theta'] = None

                self.register_controller(mapping[d](conf = dev, package = p))

    def actors_lookup(self):
        """
        Initializes and configures actor controllers based on the provided actor types and 
            configurations.

        This method performs the following steps:
        1. Defines a dictionary `p` with configuration parameters for the actors.
        2. Dynamically imports the `stream_simulator` module and retrieves the `controllers` 
            attribute.
        3. Creates a mapping `map` of actor types to their corresponding controller classes.
        4. Iterates over the actor types and their configurations in `self.actors`.
        5. For each actor configuration, it instantiates the corresponding controller class with 
            the configuration and package `p`.
        6. Checks if the actor's name is already declared; if so, logs an error. Otherwise, it 
            appends the actor's configuration to `self.actors_configurations`, adds the controller 
            to `self.actors_controllers`, and logs the declaration.

        Raises:
            AttributeError: If the actor type does not exist in the `map` dictionary.
        """
        p = {
            "logger": None,
            'tf_declare_rpc_topic': self.tf_base + '.declare',
            'tf_affection_rpc_topic': self.tf_base + '.get_affections',
            'resolution': self.resolution,
        }
        str_sim = __import__("stream_simulator")
        str_contro = getattr(str_sim, "controllers")
        mapping = {
           "humans": getattr(str_contro, "HumanActor"),
           "superman": getattr(str_contro, "SupermanActor"),
           "sound_sources": getattr(str_contro, "SoundSourceActor"),
           "qrs": getattr(str_contro, "QrActor"),
           "barcodes": getattr(str_contro, "BarcodeActor"),
           "colors": getattr(str_contro, "ColorActor"),
           "texts": getattr(str_contro, "TextActor"),
           "rfid_tags": getattr(str_contro, "RfidTagActor"),
           "fires": getattr(str_contro, "FireActor"),
           "waters": getattr(str_contro, "WaterActor"),
        }
        for type_ in self.actors:
            actors = self.actors[type_]
            for act in actors:
                c = mapping[type_](conf = act, package = p)
                if c.name in self.actors:
                    self.logger.error("Device %s declared twice", c.name)
                else:
                    self.actors_configurations.append(c.info)
                    self.actors_controllers[c.name] = c
                    self.logger.info("Actor %s declared", c.name)

    def stop(self):
        """
        Stops the communication library factory.

        This method stops the commlib_factory, which is responsible for managing
        communication within the simulation. It ensures that all communication
        processes are properly terminated.
        """
        self.commlib_factory.stop()
