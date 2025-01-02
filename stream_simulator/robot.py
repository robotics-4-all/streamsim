"""
File name: robot.py
"""
#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import math
import logging
import threading

from stream_simulator.connectivity import CommlibFactory

class Robot:
    """
    A class to represent a robot in a simulated environment.
    Attributes
    ----------
    configuration : dict
        Configuration settings for the robot.
    world : dict
        The world/environment properties and configuration.
    map : numpy.ndarray
        The map of the environment.
    tick : float
        The time interval for each simulation step.
    namespace : str
        The namespace for the robot.
    Methods
    -------
    register_controller(c):
        Registers a controller for the robot.
    device_lookup():
        Looks up and registers devices for the robot.
    leds_redis(message):
        Handles LED messages from Redis.
    execution_nodes_redis(message):
        Handles execution node messages from Redis.
    detects_redis(message):
        Handles detection messages from Redis.
    button_amqp(message):
        Handles button press messages from AMQP.
    start():
        Starts the robot and its controllers.
    stop():
        Stops the robot and its controllers.
    devices_callback(message):
        Callback for retrieving connected devices.
    reset_pose_callback(message):
        Callback for resetting the robot's pose.
    initialize_resources():
        Initializes resources for the robot.
    check_ok(x, y, prev_x, prev_y):
        Checks if the robot's position is valid.
    dispatch_pose_local():
        Publishes the robot's internal pose.
    simulation_thread():
        The main simulation thread for the robot.
    """
    def __init__(self,
                 configuration = None,
                 world = None,
                 map_ = None,
                 tick = 0.1,
                 namespace = "_default_",
                 mqtt_notifier = None):

        self.env_properties = world.env_properties
        world = world.configuration

        self.configuration = configuration
        self.logger = logging.getLogger(__name__)
        self.namespace = namespace
        self.mqtt_notifier = mqtt_notifier

        # Create the CommlibFactory
        self.commlib_factory = CommlibFactory(node_name = self.configuration["name"])

        self.tf_base = world['tf_base']
        self.tf_declare_rpc = self.commlib_factory.getRPCClient(
            rpc_name=self.tf_base + ".declare"
        )

        self.common_logging = False

        self.motion_controller = None

        self.raw_name = self.configuration["name"]
        self.name = self.namespace + "." + self.configuration["name"]
        self.dt = tick

        # intial robot pose - remains remains constant throughout streamsim launch
        self._init_x = 0
        self._init_y = 0
        self._init_theta = 0

        # current robot pose - varies during execution
        self._x = 0
        self._y = 0
        self._theta = 0

        self._curr_node = -1
        self.stopped = False
        self.error_log_msg = ""

        self.detection_threshold = 1

        # Yaml configuration management
        self.world = world
        self.map = map_
        self.width = self.map.shape[0]
        self.height = self.map.shape[1]
        self.resolution = self.world["map"]["resolution"]
        self.logger.info("Robot %s: map set", self.name)

        self._x = 0
        self._y = 0
        self._theta = 0
        if "starting_pose" in self.configuration:
            pose = self.configuration['starting_pose']
            self._init_x = pose['x'] * self.resolution
            self._init_y = pose['y'] * self.resolution
            self._init_theta = pose['theta'] / 180.0 * math.pi
            self.logger.info("Robot %s pose set: %s, %s, %s",
                self.name, self._x, self._y, self._theta)

            self._x = self._init_x
            self._y = self._init_y
            self._theta = self._init_theta

        # Devices set
        self.mode = self.configuration["mode"]
        if self.mode not in ["mock", "simulation"]:
            self.logger.error("Selected mode is invalid: %s", self.mode)
            exit(1)

        _logger = None
        if self.common_logging is True:
            _logger = self.logger

        self.devices = []
        self.controllers = {}
        self.device_lookup()

        # rpc service which resets the robot pose to the initial given values
        self.reset_pose_rpc_server = self.commlib_factory.getRPCService(
            callback = self.reset_pose_callback,
            rpc_name = self.name + '.reset_robot_pose'
        )
        self.set_pose_rpc_server = self.commlib_factory.getRPCService(
            callback = self.set_pose_callback,
            rpc_name = self.name + '.teleport'
        )
        self.devices_rpc_server = self.commlib_factory.getRPCService(
            callback = self.devices_callback,
            rpc_name = self.name + '.nodes_detector.get_connected_devices'
        )
        self.internal_pose_pub = self.commlib_factory.getPublisher(
            topic = self.name + ".pose.internal"
        )
        # print("IN ROBOT: ", self.name, self.name + ".pose.internal")

        # SIMULATOR ------------------------------------------------------------
        if self.configuration['remote_inform'] is True:
            final_dete_top = self.name + ".detect"
            final_leds_top = self.name + ".leds"

            # AMQP Publishers  -----------------------------------------------
            self.detects_pub = self.commlib_factory.getPublisher(
                topic = final_dete_top
            )
            self.leds_pub = self.commlib_factory.getPublisher(
                topic = final_leds_top
            )

            # AMQP Subscribers  -----------------------------------------------
            self.commlib_factory.getSubscriber(
                topic = self.name + ".buttons",
                callback = self.button_amqp
            )

            # REDIS Publishers  -----------------------------------------------

            self.buttons_sim_pub = self.commlib_factory.getPublisher(
                topic = self.name + ".buttons_sim.internal"
            )

            # REDIS Subscribers -----------------------------------------------
            self.detects_redis_sub = self.commlib_factory.getSubscriber(
                topic = self.name + ".detects.internal",
                callback = self.detects_redis
            )
            self.leds_redis_sub = self.commlib_factory.getSubscriber(
                topic = self.name + ".leds.internal",
                callback = self.leds_redis
            )

        # Start the CommlibFactory
        self.commlib_factory.run()
        # Threads
        self.simulator_thread = threading.Thread(target = self.simulation_thread)

        self.logger.info("Device %s set-up", self.name)

    def register_controller(self, c):
        """
        Registers a controller with the robot.
        Args:
            c (Controller): The controller to be registered. It should have 'name' and 'info' 
            attributes.
        Behavior:
            - If the controller's name is already in the controllers dictionary, logs an error.
            - If the controller's type is not "BUTTON_ARRAY", adds the controller's info to the 
            devices list.
            - If the controller's type is "BUTTON", logs a warning and skips adding it to the 
            controllers dictionary.
            - If the controller's type is "SKID_STEER", sets it as the motion controller and 
            assigns the resolution.
            - Logs the creation of the controller.
        Logging:
            - Logs an error if the controller is declared twice.
            - Logs a warning if a button controller is skipped.
            - Logs the creation of the controller.
        """
        if c.name in self.controllers:
            self.logger.error("Device %s declared twice", c.name)
        else:
            # Do not put button array in devices
            if c.info["type"] != "BUTTON_ARRAY":
                self.devices.append(c.info)

            if c.info["type"] == "BUTTON":
                # Do not put in controllers but add in devices
                self.logger.warning("Button %s skipped from controllers", c.name)
                return
            self.controllers[c.name] = c

        if c.info["type"] == "SKID_STEER":
            self.motion_controller = c
            self.controllers[c.name].resolution = self.resolution

        self.logger.info("%s controller created", c.name)

    def device_lookup(self):
        """
        Initializes and registers device controllers based on the robot's configuration.
        This method performs the following steps:
        1. Retrieves the list of actors from the world configuration if available.
        2. Prepares a package dictionary containing various robot attributes and configurations.
        3. Imports the necessary controller classes from the stream_simulator.controllers module.
        4. Iterates over the devices specified in the robot's configuration and initializes the 
        corresponding controllers.
        5. Registers each initialized controller with the robot.
        6. Handles the configuration and registration of button devices, if any.
        The method expects the robot's configuration to contain a "devices" key with device 
        specifications.
        Each device specification should include a "pose" key with "x", "y", and "theta" 
        attributes, which are set to default values if not provided.
        The method also configures button devices by creating a button configuration dictionary 
        and registering a ButtonArrayController if any buttons are found.
        Returns:
            None
        """
        actors = {}
        if "actors" in self.world:
            actors = self.world["actors"]
        p = {
            "name": self.name,
            "mode": self.mode,
            "namespace": self.namespace,
            "device_name": self.configuration["name"],
            "logger": self.logger,
            "map": self.map,
            "actors": actors,
            'tf_declare': self.tf_declare_rpc,
            "env_properties": self.env_properties,
            'tf_declare_rpc_topic': self.tf_base + '.declare',
            'tf_affection_rpc_topic': self.tf_base + '.get_affections',
        }
        str_sim = __import__("stream_simulator")
        str_contro = getattr(str_sim, "controllers")
        map_ = {
           "sonar": getattr(str_contro, "SonarController"),
           "camera": getattr(str_contro, "CameraController"),
           "skid_steer": getattr(str_contro, "MotionController"),
           "microphone": getattr(str_contro, "MicrophoneController"),
           "imu": getattr(str_contro, "ImuController"),
           "env": getattr(str_contro, "EnvController"),
           "speaker": getattr(str_contro, "SpeakerController"),
           "leds": getattr(str_contro, "LedsController"),
           "pan_tilt": getattr(str_contro, "PanTiltController"),
           "button": getattr(str_contro, "ButtonController"),
           "button_array": getattr(str_contro, "ButtonArrayController"),
           "rfid_reader": getattr(str_contro, "RfidReaderController"),
        }
        if "devices" not in self.configuration:
            return
        for s in self.configuration["devices"]:
            for m in self.configuration["devices"][s]:
                # Handle pose
                if 'pose' not in m:
                    m['pose'] = {'x': 0, 'y': 0, 'theta': None}
                else:
                    if 'x' not in m['pose']:
                        m['pose']['x'] = 0
                    if 'y' not in m['pose']:
                        m['pose']['y'] = 0
                    if 'theta' not in m['pose']:
                        m['pose']['theta'] = None

                tmp_controller = map_[s](conf = m, package = p)
                self.register_controller(tmp_controller)

        # Handle the buttons
        self.button_configuration = {
                "places": [],
                "base_topics": {},
                "direction": "down",
                "bounce": 200,
        }
        buttons = [x for x in self.devices if x["type"] == "BUTTON"]
        for d in buttons:
            self.logger.info("Button %s added in button_array", d['id'])
            self.button_configuration["places"].append(d["place"])
            self.button_configuration["base_topics"][d["id"]] = d["base_topic"]
        if len(self.button_configuration["places"]) > 0:
            m = {
                "sensor_configuration": self.button_configuration
            }
            self.register_controller(map_["button_array"](conf = m, package = p))

    # Change this
    def leds_redis(self, message):
        """
        Handles LED messages received from Redis.

        This method logs the received LED message, then publishes it to an AMQP notifier.

        Args:
            message (str): The LED message received from Redis.
        """
        self.logger.debug("Got leds from redis %s", message)
        self.logger.warning("Sending to amqp notifier: %s", message)
        self.leds_pub.publish(message)

    # NOTE: Change this
    def detects_redis(self, message):
        """
        Handles detection messages from Redis.
        This method logs a warning when a detection message is received from Redis.
        It then waits for a source to be available, logging the status periodically.
        Once the source is available, it updates the `actor_id` in the message based 
        on the source value.
        Finally, it publishes the updated message to the AMQP notifier.
        Args:
            message (dict): The detection message received from Redis.
        Returns:
            None
        """
        self.logger.warning("Got detect from redis %s", message)
        # Wait for source
        done = False
        while not done:
            try:
                v2 = "" ## Change this!
                self.logger.info("Got the source!")
                done = True
            except: # pylint: disable=bare-except
                time.sleep(0.1)
                self.logger.info("Source not written yet...")

        if v2 != "empty":
            message["actor_id"] = ""
        else:
            message["actor_id"] = -1
        self.logger.warning("Sending to amqp notifier: %s", message)
        self.detects_pub.publish(message)

    def button_amqp(self, message):
        """
        Handle button press messages received via AMQP.

        This method logs a warning message indicating that a button press
        was received from AMQP and publishes the button press information
        to the buttons simulation publisher.

        Args:
            message (dict): A dictionary containing the button press information.
                            Expected to have a key "button" with the button identifier.

        Returns:
            None
        """
        self.logger.warning("Got button press from amqp %s", str(message))
        self.buttons_sim_pub.publish({
            "button": message["button"]
        })

    def start(self):
        """
        Starts the robot simulation by initializing and starting all controller threads
        and the main simulator thread.
        This method performs the following actions:
        1. Iterates through all controllers and starts each one in a new thread.
        2. Sets the `stopped` attribute to False.
        3. Starts the main simulator thread.
        Note:
            Ensure that `self.controllers` is a dictionary of controller objects,
            each having a `start` method, and `self.simulator_thread` is a properly
            initialized thread object before calling this method.
        """
        for _, controller in self.controllers.items():
            threading.Thread(target = controller.start).start()

        self.stopped = False
        self.simulator_thread.start()

    def stop(self):
        """
        Stops all controllers and the communication library factory, and sets the robot's 
        stopped flag to True.
        This method iterates through all controllers, logs a warning message for each, and 
        calls their stop method.
        It then stops the communication library factory and logs a warning message indicating 
        that the robot thread is being stopped.
        Finally, it sets the robot's stopped attribute to True.
        """
        for c, controller in self.controllers:
            self.logger.warning("Trying to stop controller %s", c)
            controller.stop()

        self.commlib_factory.stop()

        self.logger.warning("Trying to stop robot thread")
        self.stopped = True

    def devices_callback(self, _):
        """
        Callback function to retrieve the current devices and timestamp.

        Args:
            _ (Any): Placeholder argument, not used in the function.

        Returns:
            dict: A dictionary containing:
                - "devices" (list): The list of current devices.
                - "timestamp" (float): The current time in seconds since the epoch.
        """
        return {
                "devices": self.devices,
                "timestamp": time.time()
        }

    def reset_pose_callback(self, _):
        """
        Callback function to reset the robot's pose to its initial state.

        This function is triggered by an external event and resets the robot's
        position (x, y) and orientation (theta) to their initial values. It also
        logs a warning message indicating that the robot's pose is being reset.

        Args:
            _ (Any): Placeholder for the argument passed by the callback mechanism.

        Returns:
            dict: An empty dictionary.
        """
        self.logger.warning("Resetting robot pose")
        self._x = self._init_x
        self._y = self._init_y
        self._theta = self._init_theta
        self.dispatch_pose_local()
        return {}

    def set_pose_callback(self, msg):
        """
        Callback function to set the robot's pose.

        This function is triggered to update the robot's position and orientation.
        It logs a warning message indicating that the robot is being teleported,
        updates the internal state variables `_x`, `_y`, and `_theta` with the
        values from the provided message, and then dispatches the updated pose
        locally.

        Args:
            msg (dict): A dictionary containing the new pose of the robot with keys
                        "x" (float), "y" (float), and "theta" (float).

        Returns:
            dict: An empty dictionary.
        """
        self.logger.warning("Teleporting robot @ %s, %s, %s", msg["x"], msg["y"], msg["theta"])
        self._x = msg["x"]
        self._y = msg["y"]
        self._theta = msg["theta"]
        self.dispatch_pose_local()
        return {}

    def initialize_resources(self):
        """
        Initialize the resources required for the robot simulation.

        This method is intended to set up any necessary resources or configurations
        needed for the robot to operate within the simulation environment. Currently,
        it does not perform any actions, but it can be extended in the future to
        include resource initialization logic.
        """

    def check_ok(self, x, y, prev_x, prev_y):
        """
        Check if the given coordinates are valid and do not result in a collision.
        This method performs the following checks:
        1. Out of bounds check: Ensures that the coordinates (x, y) are within the valid range.
        2. Collision check: Ensures that the path from (prev_x, prev_y) to (x, y) does not collide
        with any obstacles.
        Args:
            x (float): The current x-coordinate.
            y (float): The current y-coordinate.
            prev_x (float): The previous x-coordinate.
            prev_y (float): The previous y-coordinate.
        Returns:
            bool: True if the coordinates are out of bounds or if there is a collision, 
            False otherwise.
        """
        # Check out of bounds
        if x < 0 or y < 0:
            self.error_log_msg = "Out of bounds - negative x or y"
            self.logger.error("%s: %s", self.name, self.error_log_msg)
            return True
        if x / self.resolution > self.width or y / self.resolution > self.height:
            self.error_log_msg = "Out of bounds"
            self.logger.error("%s: %s", self.name, self.error_log_msg)
            return True

        # Check collision to obstacles

        x_i = int(x / self.resolution)
        x_i_p = int(prev_x / self.resolution)
        if x_i > x_i_p:
            x_i, x_i_p = x_i_p, x_i

        y_i = int(y / self.resolution)
        y_i_p = int(prev_y / self.resolution)
        if y_i > y_i_p:
            y_i, y_i_p = y_i_p, y_i

        if x_i == x_i_p:
            for i in range(y_i, y_i_p):
                if self.map[x_i, i] == 1:
                    self.error_log_msg = "Crashed on a Wall"
                    self.logger.error("%s: %s", self.name, self.error_log_msg)
                    return True
        elif y_i == y_i_p:
            for i in range(x_i, x_i_p):
                if self.map[i, y_i] == 1:
                    self.error_log_msg = "Crashed on a Wall"
                    self.logger.error("%s: %s", self.name, self.error_log_msg)
                    return True
        else: # we have a straight line
            th = math.atan2(y_i_p - y_i, x_i_p - x_i)
            dist = math.hypot(x_i_p - x_i, y_i_p - y_i)
            d = 0
            while d < dist:
                xx = x_i + d * math.cos(th)
                yy = y_i + d * math.sin(th)
                if self.map[int(xx), int(yy)] == 1:
                    self.error_log_msg = "Crashed on a Wall"
                    self.logger.error("%s: %s", self.name, self.error_log_msg)
                    return True
                d += 1.0

        return False

    def dispatch_pose_local(self):
        """
        Publishes the robot's current pose to the internal_pose_pub topic.

        The pose includes the following information:
        - x: The x-coordinate of the robot's position.
        - y: The y-coordinate of the robot's position.
        - theta: The orientation of the robot in radians.
        - resolution: The resolution of the robot's position data.
        - name: The name of the robot.

        Returns:
            None
        """
        self.internal_pose_pub.publish({
            "x": self._x,
            "y": self._y,
            "theta": self._theta,
            "resolution": self.resolution,
            "name": self.name, # is this needed?
            "raw_name": self.raw_name
        })

    def simulation_thread(self):
        """
        Runs the simulation thread for the robot.
        This method continuously updates the robot's position and orientation 
        based on the motion controller's linear and angular velocities. 
        It publishes the new pose to the pose publisher and logs the updated
        pose. If the robot's position is not valid, it reverts to the previous 
        position and notifies the UI about the error.
        The simulation runs in a loop until the `stopped` attribute is set 
        to True. The loop updates the position and orientation at intervals defined by `self.dt`.
        Attributes:
            self._x (float): The current x-coordinate of the robot.
            self._y (float): The current y-coordinate of the robot.
            self._theta (float): The current orientation (theta) of the robot.
            self.motion_controller (object): The motion controller providing 
            linear and angular velocities.
            self.pose_pub (object): The publisher for the robot's pose.
            self.logger (object): The logger for logging messages.
            self.resolution (float): The resolution of the robot's pose.
            self.raw_name (str): The raw name of the robot.
            self.error_log_msg (str): The error message to log when the position is invalid.
            self.commlib_factory (object): The communication library factory for notifying the UI.
            self.dt (float): The time interval for updating the position and orientation.
            self.stopped (bool): Flag to stop the simulation thread.
        """
        self.logger.warning("Started %s simulation thread", self.name)
        t = time.time()

        self.dispatch_pose_local()
        while self.stopped is False:
            if self.motion_controller is not None:
                # update time interval
                dt = time.time() - t
                t = time.time()

                prev_x = self._x
                prev_y = self._y
                prev_th = self._theta

                lin_ = self.motion_controller.get_linear()
                ang_ = self.motion_controller.get_angular()

                if ang_ == 0:
                    self._x += lin_ * dt * math.cos(self._theta)
                    self._y += lin_ * dt * math.sin(self._theta)
                else:
                    arc = lin_ / ang_
                    self._x += - arc * math.sin(self._theta) + \
                        arc * math.sin(self._theta + dt * ang_)
                    self._y -= - arc * math.cos(self._theta) + \
                        arc * math.cos(self._theta + dt * ang_)
                self._theta += ang_ * dt

                xx = round(float(self._x), 2)
                yy = round(float(self._y), 2)
                theta2 = round(float(self._theta), 2)

                if self._x != prev_x or self._y != prev_y or self._theta != prev_th:
                    self.logger.info("%s: New pose: %f, %f, %f", self.raw_name, xx, yy, theta2)

                    # Send internal pose
                    self.dispatch_pose_local()

                if self.check_ok(self._x, self._y, prev_x, prev_y):
                    self._x = prev_x
                    self._y = prev_y
                    self._theta = prev_th

                    # notify mqtt about the error in robot's position
                    self.mqtt_notifier.dispatch_log(
                        f"Robot: {self.raw_name} {self.error_log_msg}"
                    )

            time.sleep(self.dt)
