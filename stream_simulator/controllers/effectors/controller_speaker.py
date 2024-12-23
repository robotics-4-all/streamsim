"""
File that exposes the speaker controller.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging

from stream_simulator.base_classes import BaseThing

class SpeakerController(BaseThing):
    """
    SpeakerController is a class that manages the speaker effector in a simulation or mock 
    environment. 
    It handles the initialization, configuration, and communication for the speaker, including
    playing and speaking actions.
    Attributes:
        logger (logging.Logger): Logger instance for logging information.
        info (dict): Dictionary containing speaker information and configuration.
        name (str): Name of the speaker.
        base_topic (str): Base topic for communication.
        global_volume (float): Global volume setting for the speaker.
        blocked (bool): Flag indicating if the speaker is currently blocked.
        play_action_server (ActionServer): Action server for handling play actions.
        speak_action_server (ActionServer): Action server for handling speak actions.
        enable_rpc_server (RPCService): RPC server for enabling the speaker.
        disable_rpc_server (RPCService): RPC server for disabling the speaker.
        play_pub (Publisher): Publisher for play notifications.
        speak_pub (Publisher): Publisher for speak notifications.
    Methods:
        __init__(conf=None, package=None): Initializes the SpeakerController with the given
        configuration and package.
        on_goal_speak(goalh): Handles the speak action goal.
        on_goal_play(goalh): Handles the play action goal.
        enable_callback(message): Callback for enabling the speaker.
        disable_callback(message): Callback for disabling the speaker.
        start(): Starts the speaker controller.
        stop(): Stops the speaker controller.
    """
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        id_ = "d_speaker_" + str(BaseThing.id + 1)
        name = id_
        if 'name' in conf:
            name = conf['name']
        _category = "actuator"
        _class = "audio"
        _subclass = "speaker"
        _pack = package["name"]
        _namespace = package["namespace"]
        super().__init__(id_, auto_start=False)

        info = {
            "type": "SPEAKERS",
            "brand": "usb_speaker",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": name,
            "place": conf["place"],
            "id": id_,
            "enabled": True,
            "orientation": float(conf["orientation"]),
            "queue_size": 0,
            "mode": package["mode"],
            "speak_mode": package["speak_mode"],
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

        self.global_volume = None
        self.blocked = False

        self.play_action_server = self.commlib_factory.getActionServer(
            callback = self.on_goal_play,
            action_name = self.base_topic + ".play"
        )
        self.speak_action_server = self.commlib_factory.getActionServer(
            callback = self.on_goal_speak,
            action_name = self.base_topic + ".speak"
        )
        self.enable_rpc_server = self.commlib_factory.getRPCService(
            callback = self.enable_callback,
            rpc_name = self.base_topic + ".enable"
        )
        self.disable_rpc_server = self.commlib_factory.getRPCService(
            callback = self.disable_callback,
            rpc_name = self.base_topic + ".disable"
        )

        self.play_pub = self.commlib_factory.getPublisher(
            topic = self.base_topic + ".play.notify"
        )
        self.speak_pub = self.commlib_factory.getPublisher(
            topic = self.base_topic + ".speak.notify"
        )

        self.commlib_factory.run()

    def on_goal_speak(self, goalh):
        """
        Handles the goal to make the speaker speak.
        This method performs the following steps:
        1. Logs the start of the speak action.
        2. Checks if the speaker is enabled; if not, returns an empty dictionary.
        3. Waits until the speaker is not blocked.
        4. Notifies the UI about the effector command.
        5. Extracts text, volume, and language from the goal handle.
        6. Publishes the speak command with the extracted parameters.
        7. Generates a timestamp for the response header.
        8. Simulates speaking for 5 seconds, checking for cancellation events.
        9. Logs the completion of the speak action and unblocks the speaker.
        Args:
            goalh: The goal handle containing the data for the speak action.
        Returns:
            dict: A dictionary containing the header with the timestamp.
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
            if self.global_volume is not None:
                volume = self.global_volume
                self.logger.info("Volume forced to %s", self.global_volume)
            language = goalh.data["language"]
        except Exception as e: # pylint: disable=broad-except
            self.logger.error("%s wrong parameters: %s", self.name, e)

        self.speak_pub.publish({
            "text": texts,
            "volume": volume,
            "language": language,
            "speaker": self.name
        })

        timestamp = time.time()
        secs = int(timestamp)
        nanosecs = int((timestamp-secs) * 10**(9))
        ret = {
            "header":{
                "stamp":{
                    "sec": secs,
                    "nanosec": nanosecs
                }
            }
        }
        if self.info["mode"] == "mock":
            now = time.time()
            self.logger.info("Speaking...")
            while time.time() - now < 5:
                if goalh.cancel_event.is_set():
                    self.logger.info("Cancel got")
                    self.blocked = False
                    return ret
                time.sleep(0.1)
            self.logger.info("Speaking done")

        elif self.info["mode"] == "simulation":
            now = time.time()
            self.logger.info("Speaking...")
            while time.time() - now < 5:
                if goalh.cancel_event.is_set():
                    self.logger.info("Cancel got")
                    self.blocked = False
                    return ret
                time.sleep(0.1)
            self.logger.info("Speaking done")

        self.logger.info("%s Speak finished", self.name)
        self.blocked = False
        return ret

    def on_goal_play(self, goalh):
        """
        Handles the goal to play a string with a specified volume.
        This method manages concurrent speaker calls, checks if the speaker is enabled,
        and publishes the play command with the provided string and volume. It also
        handles different modes of operation ("mock" and "simulation") and supports
        cancellation of the play action.
        Args:
            goalh: An object containing the goal data with the following attributes:
                - data: A dictionary with keys "string" (the text to play) and "volume" 
                    (the volume level).
                - cancel_event: An event object that can be set to cancel the play action.
        Returns:
            dict: A dictionary containing a header with a timestamp of when the play action was 
                initiated.
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
            if self.global_volume is not None:
                volume = self.global_volume
                self.logger.info("Volume forced to %s", self.global_volume)
        except Exception as e: # pylint: disable=broad-except
            self.logger.error("%s wrong parameters: %s", self.name, e)

        self.play_pub.publish({
            "text": string,
            "volume": volume
        })

        timestamp = time.time()
        secs = int(timestamp)
        nanosecs = int((timestamp-secs) * 10**(9))
        ret = {
            "header":{
                "stamp":{
                    "sec": secs,
                    "nanosec": nanosecs
                }
            }
        }
        if self.info["mode"] == "mock":
            now = time.time()
            self.logger.info("Playing...")
            while time.time() - now < 5:
                if goalh.cancel_event.is_set():
                    self.logger.info("Cancel got")
                    self.blocked = False
                    return ret
                time.sleep(0.1)
            self.logger.info("Playing done")

        elif self.info["mode"] == "simulation":
            now = time.time()
            self.logger.info("Playing...")
            while time.time() - now < 5:
                if goalh.cancel_event.is_set():
                    self.logger.info("Cancel got")
                    self.blocked = False
                    return ret
                time.sleep(0.1)
            self.logger.info("Playing done")

        self.logger.info("%s Playing finished", self.name)
        self.blocked = False
        return ret

    def enable_callback(self, _):
        """
        Enables the speaker controller by setting the "enabled" key in the info dictionary to True.

        Args:
            _ (Any): Unused argument.

        Returns:
            dict: A dictionary with the key "enabled" set to True.
        """
        self.info["enabled"] = True
        return {"enabled": True}

    def disable_callback(self, _):
        """
        Disables the speaker by setting the "enabled" key in the info dictionary to False.

        Args:
            _ (Any): Unused parameter.

        Returns:
            dict: A dictionary with the "enabled" key set to False.
        """
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        """
        Starts the sensor and waits for the simulator to start.

        This method logs a message indicating that the sensor is waiting to start.
        It then enters a loop, repeatedly checking if the simulator has started.
        Once the simulator has started, it logs a message indicating that the sensor has started.
        """
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)
        self.logger.info("Sensor %s started", self.name)

    def stop(self):
        """
        Stops the communication library factory.

        This method stops the commlib_factory, which is responsible for managing
        communication-related tasks.
        """
        self.commlib_factory.stop()
