#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import random
import string
import time

from stream_simulator.connectivity import CommlibFactory
from stream_simulator.transformations import TfController

from .robot import Robot
from .world import World

### Dont know why but if I remove this no controllers are found
from stream_simulator.controllers import IrController

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
        self.commlib_factory.notify = self.commlib_factory.getPublisher(
            topic = f"{self.name}.notifications"
        )

        self.devices_rpc_server = self.commlib_factory.getRPCService(
            callback = self.devices_callback,
            rpc_name = self.name + '.get_device_groups'
        )

        self.configuration_rpc_server = self.commlib_factory.getRPCService(
            callback = self.configuration_callback,
            rpc_name = self.name + '.set_configuration'
        )
        print(self.name + '.set_configuration')

        self.simulation_start_pub = self.commlib_factory.getPublisher(
            topic = f"{self.name}.simulation_started"
        )

        # Start the CommlibFactory
        self.commlib_factory.run()

        self.tf = None
        self.world = None
        self.world_name = None
        self.robots = None
        self.robot_names = None
        self.logger.info("Simulator created. Waiting for configuration...")

    def devices_callback(self, message):
        return {
                "robots": self.robot_names,
                "world": self.world_name
        }

    def configuration_callback(self, message):
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
        self.tf = TfController(
            base = self.name,
            resolution = resolution,
            logger = None,
            env_properties = self.configuration["world"]["properties"],
        )

        # Initializing world
        self.world = World(uid=self.uid)
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
                        map = self.world.map,
                        tick = self.tick,
                        namespace = self.name,
                    )
                )
                self.robot_names.append(r["name"])

        # Create robots
        for i in range(0, len(self.robots)):
            _robot = self.robots[i]
            _robot.start()

            self.commlib_factory.notify_ui(
                type_ = "new_message",
                data = {
                    "type": "logs",
                    "message": f"Robot {_robot.name} launched"
                }
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
        return {"success": True}

    def stop(self):
        for r in self.robots:
            r.stop()
        self.world.stop()
        self.tf.stop()
        self.commlib_factory.stop()
        self.logger.warning("Simulation stopped")

    def start(self):
        self.logger.info("******** Simulator starting *********")

        # Communications report
        self.logger.info("Communications report:")
        total = 0
        for t in self.commlib_factory.stats:
            for k in self.commlib_factory.stats[t]:
                n = self.commlib_factory.stats[t][k]
                total += n
                if n == 0:
                    continue
                self.logger.info(f"\t{t} {k}: {n}")
        self.logger.info(f"Total connections: {total}")

        self.commlib_factory.print_topics()

        # Just to be informed for pose
        for i in range(0, len(self.robots)):
            self.robots[i].dispatch_pose_local()

        self.commlib_factory.notify_ui(
            type_ = "new_message",
            data = {
                "type": "logs",
                "message": "Simulator started"
            }
        )

        self.logger.warning("Simulation started")
        self.tf.print_tf_tree()
