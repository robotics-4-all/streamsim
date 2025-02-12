"""
File that contains the EnvSpeakerController class.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging
import threading

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

        info = self.generate_info(conf, package, _type, _category, _class, _subclass)

        self.info = info
        self.name = info["name"]
        self.base_topic = info["base_topic"]
        self.mode = info["mode"]
        self.place = info["conf"]["place"]
        self.pose = info["conf"]["pose"]
        self.automation = info["conf"]["automation"] if "automation" in info["conf"] else None

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

        if self.automation is not None:
            self.logger.warning("Relay %s is automated", self.name)
            self.stopped = False
            self.active = True
            self.automation_thread = threading.Thread(target = self.automation_thread_loop)
            self.automation_thread.start()

    def automation_thread_loop(self):
        """
        Manages the automation loop for the device.
        This method runs in a separate thread and controls the device based on the 
        predefined automation steps. It supports reversing the steps and looping 
        through them based on the configuration.
        """
        self.logger.warning("Speaker %s automation starts", self.name)
        self.stopped = False
        automation_steps = self.automation["steps"]
        step_index = -1
        reverse_mode = False
        while self.active:
            step_index += 1
            if step_index >= len(automation_steps):
                if self.automation["reverse"] and reverse_mode is False:
                    automation_steps.reverse()
                    step_index = 1
                    reverse_mode = True
                elif self.automation["reverse"] and reverse_mode is True:
                    if self.automation["loop"]:
                        automation_steps.reverse()
                        step_index = 1
                        reverse_mode = False
                    else:
                        self.active = False
                        break
                elif self.automation["reverse"] is False and self.automation["loop"]:
                    step_index = 0
                else:
                    self.active = False
                    break
            step = automation_steps[step_index]
            self.speak_pub.publish({
                "text": automation_steps[step_index]['state']['text'],
                "volume": automation_steps[step_index]['state']['volume'],
                "language": automation_steps[step_index]['state']['language'],
                "speaker": self.name
            })
            self.logger.info("Speaker %s says: %s", self.name, \
                automation_steps[step_index]['state']['text'])
            sleep = step['duration']
            while sleep > 0 and self.active: # to be preemptable
                time.sleep(0.1)
                sleep -= 0.1

        self.stopped = True
        self.logger.warning("Relay %s automation stops", self.name)

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
        self.set_tf_distance_calculator_rpc(package)
        self.set_state_publisher_internal(package["namespace"])

        self.play_action_server = self.commlib_factory.get_action_server(
            callback = self.on_goal_play,
            action_name = self.base_topic + ".play"
        )
        self.speak_action_server = self.commlib_factory.get_action_server(
            callback = self.on_goal_speak,
            action_name = self.base_topic + ".speak"
        )

        self.play_pub = self.commlib_factory.get_publisher(
            topic = self.base_topic + ".play.notify"
        )
        self.speak_pub = self.commlib_factory.get_publisher(
            topic = self.base_topic + ".speak.notify"
        )

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

    def stop(self):
        """
        Stops the speaker controller by disabling the RPC servers and action servers.
        This method performs the following actions:
        - Sets the "enabled" flag in the info dictionary to False.
        - Stops the enable and disable RPC servers.
        - Stops the goal, cancel, and result RPCs for both the play and speak action servers.
        """
        self.info["enabled"] = False
        if self.automation is not None:
            self.active = False
            while not self.stopped:
                time.sleep(0.1)
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
        if self.automation is not None:
            self.logger.info("Speaker %s is automated, ignoring play command", self.name)
            return {}

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
        if self.automation is not None:
            self.logger.info("Speaker %s is automated, ignoring speak command", self.name)
            return {}

        self.logger.info("%s speak started", self.name)
        if self.info["enabled"] is False:
            return {}

        # Concurrent speaker calls handling
        while self.blocked:
            time.sleep(0.1)
        self.logger.info("Speaker unlocked")
        self.blocked = True

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
        self.state_publisher_internal.publish({
            "state": {
                "text": texts,
                "volume": volume,
                "language": language,
            },
            'origin': self.name
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
