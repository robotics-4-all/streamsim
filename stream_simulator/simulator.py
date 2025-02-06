"""
File that contains the Simulator class.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import random
import string
import time

from stream_simulator.connectivity import CommlibFactory
from stream_simulator.transformations import TfController
from stream_simulator.controllers import SonarController # pylint: disable=unused-import

from .robot import Robot
from .world import World
from .mqtt_notifier import MQTTNotifier

### Dont know why but if I remove this no controllers are found

class Simulator:
    """
    A class to represent a simulator for stream simulation.
    Attributes
    ----------
    tick : float
        The time interval for each simulation tick.
    logger : logging.Logger
        Logger for the simulator.
    configuration : dict
        Configuration settings for the simulator.
    name : str
        Name of the simulation.
    commlib_factory : CommlibFactory
        Factory for communication library.
    tf : TfController
        Controller for transformation frames.
    world : World
        The simulation world.
    world_name : str
        Name of the simulation world.
    robots : list
        List of robots in the simulation.
    robot_names : list
        List of robot names in the simulation.
    Methods
    -------
    __init__(tick=0.1, conf_file=None, configuration=None, device=None):
        Initializes the simulator with given parameters.
    devices_callback(message):
        Callback function for device-related messages.
    parseConfiguration(conf_file, configuration):
        Parses the configuration from a file or dictionary.
    loadYaml(yaml_file):
        Loads and parses a YAML file.
    recursiveConfParse(conf, curr_dir):
        Recursively parses the configuration dictionary.
    stop():
        Stops the simulation and all its components.
    start():
        Starts the simulation and all its components.
    """
    def __init__(self,
                 tick = 0.1,
                 uid = None
                 ):

        self.tick = tick
        self.logger = logging.getLogger(__name__)
        self.mqtt_notifier = None

        characters = string.ascii_lowercase + string.digits
        self.uid = uid
        if self.uid is None:
            self.uid = ''.join(random.choice(characters) for _ in range(16))
        self.logger.critical("Simulator UID is: %s", self.uid)

        self.name = f"streamsim.{self.uid}"

        # Wait for configuration from broker
        self.configuration = None

         # Create the CommlibFactory
        self.commlib_factory = CommlibFactory(node_name = "Simulator")

        self.logger.info("Created %s.notifications publisher!", self.name)
        self.commlib_factory.notify = self.commlib_factory.get_publisher(
            topic = f"{self.name}.notifications"
        )

        self.devices_rpc_server = self.commlib_factory.get_rpc_service(
            callback = self.devices_callback,
            rpc_name = self.name + '.get_device_groups'
        )

        self.devices_rpc_server = self.commlib_factory.get_rpc_service(
            callback = self.reset,
            rpc_name = self.name + '.reset'
        )

        self.simulation_start_pub = self.commlib_factory.get_publisher(
            topic = f"{self.name}.simulation_started"
        )

        self.configuration_rpc_server = self.commlib_factory.get_rpc_service(
            callback = self.configuration_callback,
            rpc_name = self.name + '.set_configuration_local'
        )

        # MQTT Connection for Locsys
        self.mqtt_commlib_factory = CommlibFactory(node_name = "SimulatorMQTT", interface = "mqtt")

        self.configuration_subscriber = self.mqtt_commlib_factory.get_subscriber(
            callback = self.configuration_callback,
            topic = self.name + '.set_configuration'
        )

        # Start the CommlibFactory
        self.commlib_factory.run()
        self.mqtt_commlib_factory.run()

        self.mqtt_commlib_factory.print_topics()

        # Create the MQTTNotifier
        self.mqtt_notifier = MQTTNotifier(uid = self.uid)

        self.tf = TfController(mqtt_notifier = self.mqtt_notifier)
        self.world = None
        self.world_name = None
        self.robots = None
        self.robot_names = None
        self.logger.info("Simulator created. Waiting for configuration...")

    def reset(self, _):
        """
        Callback function to reset the simulation environment.
        This function stops the simulation and resets the transformation controller (tf),
        the world, and the robots. It also starts the robots and publishes a simulation 
        start message.

        Args:
            _ (Any): Placeholder argument, not used in the function.

        Returns:
            dict: A dictionary indicating the success of the reset with a key "success" set to True.
        """
        self.logger.warning("Resetting simulation...")
        # Cleaning robots
        if self.robots is not None:
            for _, robot in enumerate(self.robots):
                self.logger.info("[simulator] Stopping robot %s", robot.name)
                robot.stop()
                self.logger.info("[simulator] Robot %s stopped", robot.name)
                del robot
        del self.robots
        del self.robot_names
        self.logger.info("Robots cleaned")

        # Cleaning world
        if self.world is not None:
            self.world.stop()
        del self.world
        del self.world_name
        self.logger.info("World cleaned")

        # Cleaning tf
        try:
            if self.tf is not None:
                self.tf.stop()
                self.logger.info("Tf cleaned")
        except Exception as e: # pylint: disable=broad-except
            self.logger.error("Error cleaning tf: %s", e)

        # Reinitializing variables
        self.world = None
        self.world_name = None
        self.robots = None
        self.robot_names = None
        self.logger.info("Simulation reset")

        return {
            "success": True
        }

    def devices_callback(self, _):
        """
        Callback function to retrieve the names of robots and the world.

        Args:
            _ (Any): Placeholder argument, not used in the function.

        Returns:
            dict: A dictionary containing the names of robots and the world.
                  The dictionary has the following structure:
                  {
                      "robots": list of robot names,
                      "world": name of the world
        """
        return {
            "robots": self.robot_names,
            "world": self.world_name
        }

    def configuration_callback(self, message):
        """
        Callback function to handle the configuration message.
        This function is responsible for setting up the simulation environment
        based on the received configuration message. It initializes the 
        transformation controller (tf), the world, and the robots as specified 
        in the configuration. It also starts the robots and publishes a 
        simulation start message.
        Args:
            message (dict): The configuration message containing the setup 
                            details for the simulation.
        Returns:
            dict: A dictionary indicating the success of the configuration 
                  setup with a key "success" set to True.
        """
        # Wait for mqtt notifier setup
        while self.mqtt_notifier is None:
            time.sleep(0.1)

        self.logger.info("Received configuration")
        self.configuration = message
        self.configuration['tf_base'] = self.name + ".tf"
        self.configuration['simulation'] = {
            "name": self.name,
        }

        resolution = 0.2
        if 'map' in self.configuration and 'resolution' in self.configuration['map']:
            resolution = self.configuration['map']['resolution']

        # Initializing tf
        self.tf.initialize(
            base = self.name,
            resolution = resolution,
            # env_properties = self.configuration["world"]["properties"],
        )

        # Initializing world
        self.world = World(uid=self.uid, mqtt_notifier=self.mqtt_notifier, tf=self.tf)
        self.world.load_environment(configuration = self.configuration)
        self.world_name = self.world.name

        # Initializing robots
        self.robots = []
        self.robot_names = []
        if "robots" in self.configuration:
            for r in self.configuration["robots"]:
                self.robots.append(
                    Robot(
                        configuration = r,
                        world = self.world,
                        map_ = self.world.map,
                        tick = self.tick,
                        namespace = self.name,
                        mqtt_notifier = self.mqtt_notifier,
                    )
                )
                self.robot_names.append(r["name"])

        # Create robots
        for _, value in enumerate(self.robots):
            _robot = value
            _robot.start()

            self.mqtt_notifier.dispatch_log(
                f"Robot {_robot.name} launched"
            )

        # Initializing tf
        self.logger.info("Setting up tf")
        self.tf.setup()
        self.logger.info("Tf setup done")

        # Start all devices NOTE: Should this be here???
        self.simulation_start_pub.publish({
            "uid": self.uid
        })

        self.start()
        self.logger.info("Configuration setup done")

    def stop(self):
        """
        Stops the simulation by stopping all robots, the world, the transformation framework,
        the communication library factory, and logs a warning message indicating that the 
        simulation has been stopped.
        """
        self.logger.critical("Stopping simulation...")
        for r in self.robots:
            self.logger.critical("Stopping robot %s", r.raw_name)
            r.stop()
            self.logger.critical("Robot %s stopped", r.raw_name)
        self.world.stop()
        self.tf.stop()
        self.commlib_factory.stop()
        self.logger.warning("Simulation stopped")

    def start(self):
        """
        Starts the simulator and logs the initial status.
        This method performs the following actions:
        1. Logs the start of the simulator.
        2. Logs a communications report, detailing the number of connections for each type.
        3. Dispatches the local pose for each robot.
        4. Notifies the UI that the simulator has started.
        5. Logs a warning indicating that the simulation has started.
        """
        self.logger.info("******** Simulator starting *********")

        # Communications report
        self.logger.info("Communications report:")
        total = 0
        for t, stat in self.commlib_factory.stats.items():
            for k, inner_stat in stat.items():
                total += inner_stat
                if inner_stat == 0:
                    continue
                self.logger.info("\t%s %s: %d", t, k, inner_stat)
        self.logger.info("Total connections: %d", total)

        self.commlib_factory.print_topics()
        # Just to be informed for pose
        for _, robot in enumerate(self.robots):
            robot.dispatch_pose_local()

        self.mqtt_notifier.dispatch_log(
            "Simulator started"
        )

        self.logger.warning("Simulation started")
        self.tf.print_tf_tree()
