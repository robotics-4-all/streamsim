"""
File that contains the EnvSpeakerController class.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging

from stream_simulator.base_classes import BaseThing

class EnvSpeakerController(BaseThing):
    """
    EnvSpeakerController is a class that manages the behavior and communication of a speaker device 
        in an environment simulation.
    Attributes:
        logger (logging.Logger): Logger for the controller.
        info (dict): Information about the speaker device.
        name (str): Name of the speaker device.
        base_topic (str): Base topic for communication.
        mode (str): Mode of operation (e.g., mock, simulation).
        place (str): Place where the speaker is located.
        pose (dict): Pose information of the speaker.
        host (str): Host information if available.
        blocked (bool): Flag to handle concurrent speaker calls.
    Methods:
        __init__(conf=None, package=None):
            Initializes the EnvSpeakerController with configuration and package information.
        set_communication_layer(package):
            Sets up the communication layer for the speaker device.
        enable_callback(message):
            Callback function to enable the speaker device.
        disable_callback(message):
            Callback function to disable the speaker device.
        start():
            Starts the speaker device and waits for the simulator to start.
        stop():
            Stops the speaker device and its communication servers.
        on_goal_play(goalh):
            Handles the play action for the speaker device.
        on_goal_speak(goalh):
            Handles the speak action for the speaker device.
    """
    def __init__(self,
                 conf = None,
                 package = None
                 ):

        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        super().__init__(conf["name"], auto_start=False)

        _type = "SPEAKERS"
        _category = "actuator"
        _class = "audio"
        _subclass = "speaker"

        _name = conf["name"]
        _pack = package["base"]
        _place = conf["place"]
        _namespace = package["namespace"]
        info = {
            "type": _type,
            "base_topic": f"{_namespace}.{_pack}.{_place}.{_category}.{_class}.{_subclass}.{_name}",
            "name": _name,
            "place": conf["place"],
            "enabled": True,
            "mode": conf["mode"],
            "conf": conf,
            "categorization": {
                "host_type": _pack,
                "place": _place,
                "category": _category,
                "class": _class,
                "subclass": [_subclass],
                "name": _name
            }
        }

        self.info = info
        self.name = info["name"]
        self.base_topic = info["base_topic"]
        self.mode = info["mode"]
        self.place = info["conf"]["place"]
        self.pose = info["conf"]["pose"]

        # tf handling
        tf_package = {
            "type": "env",
            "subtype": {
                "category": _category,
                "class": _class,
                "subclass": [_subclass]
            },
            "pose": self.pose,
            "base_topic": self.base_topic,
            "name": self.name
        }

        self.host = None
        if 'host' in info['conf']:
            self.host = info['conf']['host']
            tf_package['host'] = self.host
            # No other host type is available for env_devices
            tf_package['host_type'] = 'pan_tilt'

        self.set_communication_layer(package)
        self.commlib_factory.run()

        self.tf_declare_rpc.call(tf_package)

        self.blocked = False

    def set_communication_layer(self, package):
        """
        Sets up the communication layer for the speaker controller.
        This method initializes the communication channels required for the speaker
        controller to function. It sets up simulation communication, transforms
        communication, and enables/disables RPCs. Additionally, it creates action
        servers and publishers for play and speak actions.
        Args:
            package (dict): A dictionary containing configuration parameters. 
                            Expected keys include:
                            - "namespace": The namespace for the communication channels.
        """
        self.set_simulation_communication(package["namespace"])
        self.set_tf_communication(package)
        self.set_enable_disable_rpcs(self.base_topic, self.enable_callback, self.disable_callback)

        self.play_action_server = self.commlib_factory.getActionServer(
            callback = self.on_goal_play,
            action_name = self.base_topic + ".play"
        )
        self.speak_action_server = self.commlib_factory.getActionServer(
            callback = self.on_goal_speak,
            action_name = self.base_topic + ".speak"
        )

        self.play_pub = self.commlib_factory.getPublisher(
            topic = self.base_topic + ".play.notify"
        )
        self.speak_pub = self.commlib_factory.getPublisher(
            topic = self.base_topic + ".speak.notify"
        )

    def enable_callback(self, _):
        """
        Enables the callback by setting the "enabled" key in the info dictionary to True.
        Args:
            _ (Any): Placeholder argument, not used.
        Returns:
            dict: A dictionary with the key "enabled" set to True.
        """
        self.info["enabled"] = True

        # self.enable_rpc_server.run()
        # self.disable_rpc_server.run()

        # self.play_action_server.run()
        # self.speak_action_server.run()

        return {"enabled": True}

    def disable_callback(self, _):
        """
        Disables the speaker by setting the "enabled" status to False.

        Args:
            message (dict): The message containing information to process (not used in this method).

        Returns:
            dict: A dictionary indicating the new "enabled" status of the speaker.
        """
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        """
        Starts the sensor and waits for the simulator to start.
        This method logs a message indicating that the sensor is waiting to start.
        It then enters a loop, checking if the simulator has started, and sleeps for
        1 second between checks. Once the simulator has started, it logs a message
        indicating that the sensor has started.
        Note: The method contains commented-out code for enabling and disabling RPC
        servers and running play and speak action servers, which are not executed.
        """
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)
        self.logger.info("Sensor %s started", self.name)

        # self.enable_rpc_server.run()
        # self.disable_rpc_server.run()

        # self.play_action_server.run()
        # self.speak_action_server.run()

    def stop(self):
        """
        Stops the speaker controller by disabling the RPC servers and action servers.
        This method performs the following actions:
        - Sets the "enabled" flag in the info dictionary to False.
        - Stops the enable and disable RPC servers.
        - Stops the goal, cancel, and result RPCs for both the play and speak action servers.
        """
        self.info["enabled"] = False
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()

        self.play_action_server.stop()

    def on_goal_play(self, goalh):
        """
        Handles the goal to play a string with a specified volume.
        This method logs the start of the play action, checks if the speaker is enabled,
        handles concurrent speaker calls, and publishes the play action with the given
        string and volume. If the mode is "mock" or "simulation", it simulates the play
        action for 5 seconds or until a cancel event is set.
        Args:
            goalh (object): An object containing the play goal data with the following attributes:
                - data (dict): A dictionary containing:
                    - "string" (str): The string to be played.
                    - "volume" (int): The volume at which the string should be played.
                - cancel_event (threading.Event): An event that can be set to cancel the play 
                    action.
        Returns:
            dict: A dictionary containing the timestamp of when the play action finished.
        """
        self.logger.info("%s play started", self.name)
        if self.info["enabled"] is False:
            return {}

        # Concurrent speaker calls handling
        while self.blocked:
            time.sleep(0.1)
        self.logger.info("Speaker unlocked")
        self.blocked = True

        try:
            string = goalh.data["string"]
            volume = goalh.data["volume"]
        except Exception as e: # pylint: disable=broad-except
            self.logger.error("%s wrong parameters: %s", self.name, e)

        self.play_pub.publish({
            "text": string,
            "volume": volume
        })

        if self.info["mode"] in ["mock", "simulation"]:
            now = time.time()
            self.logger.info("Playing...")
            while time.time() - now < 5:
                if goalh.cancel_event.is_set():
                    self.logger.info("Cancel got")
                    self.blocked = False
                    return
                time.sleep(0.1)
            self.logger.info("Playing done")

        self.logger.info("%s Playing finished", self.name)
        self.blocked = False
        return {
            "timestamp": time.time()
        }

    def on_goal_speak(self, goalh):
        """
        Handles the goal to make the speaker speak.
        This method processes the goal to make the speaker speak the provided text with the 
            specified volume and language.
        It ensures that concurrent speaker calls are handled properly and notifies the UI about 
            the effector command.
        If the speaker is in "mock" or "simulation" mode, it simulates the speaking process for 
            5 seconds.
        Args:
            goalh (GoalHandle): The goal handle containing the data for the speak command.
        Returns:
            dict: A dictionary containing the timestamp of when the speaking finished.
        Raises:
            Exception: If there are wrong parameters in the goal handle data.
        """
        self.logger.info("%s speak started", self.name)
        if self.info["enabled"] is False:
            return {}

        # Concurrent speaker calls handling
        while self.blocked:
            time.sleep(0.1)
        self.logger.info("Speaker unlocked")
        self.blocked = True

        self.commlib_factory.notify_ui(
            type_ = "effector_command",
            data = {
                "name": self.name,
                "value": {
                    "text": goalh.data["text"]
                }
            }
        )

        try:
            texts = goalh.data["text"]
            volume = goalh.data["volume"]
            language = goalh.data["language"]
        except Exception as e: # pylint: disable=broad-except
            self.logger.error("%s wrong parameters: %s", self.name, e)

        self.speak_pub.publish({
            "text": texts,
            "volume": volume,
            "language": language,
            "speaker": self.name
        })

        if self.info["mode"] in ["mock", "simulation"]:
            now = time.time()
            self.logger.info("Speaking...")
            while time.time() - now < 5:
                if goalh.cancel_event.is_set():
                    self.logger.info("Cancel got")
                    self.blocked = False
                    return
                time.sleep(0.1)
            self.logger.info("Speaking done")

        self.logger.info("%s Speak finished", self.name)
        self.blocked = False
        return {
            'timestamp': time.time()
        }
