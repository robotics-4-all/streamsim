"""
File that contains the microphone controller.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging
from pathlib import Path
import base64
import wave

from stream_simulator.base_classes import BaseThing

class EnvMicrophoneController(BaseThing):
    """
    EnvMicrophoneController is a class that simulates a microphone sensor in an environment.
    Attributes:
        logger (logging.Logger): Logger for the controller.
        info (dict): Information about the microphone sensor.
        name (str): Name of the microphone sensor.
        base_topic (str): Base topic for communication.
        mode (str): Mode of the microphone sensor (e.g., "mock", "simulation").
        place (str): Place where the microphone sensor is located.
        pose (dict): Pose information of the microphone sensor.
        host (str): Host information if available.
        blocked (bool): Flag to indicate if the microphone is blocked.
    Methods:
        __init__(conf=None, package=None):
            Initializes the EnvMicrophoneController with configuration and package information.
        set_communication_layer(package):
            Sets up the communication layer for the microphone sensor.
        speech_detected(message):
            Callback function for handling detected speech messages.
        enable_callback(message):
            Callback function for enabling the microphone sensor.
        disable_callback(message):
            Callback function for disabling the microphone sensor.
        start():
            Starts the microphone sensor.
        stop():
            Stops the microphone sensor.
        on_goal_record(goalh):
            Handles the goal for recording audio.
        load_wav(path):
            Loads a WAV file and returns its base64 encoded content.
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

        _type = "MICROPHONE"
        _category = "sensor"
        _class = "audio"
        _subclass = "microphone"

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
            "name": self.name,
            "namespace": _namespace
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
        Sets up the communication layer for the microphone controller.
        This method initializes various communication interfaces required for the
        microphone controller to function. It sets up simulation communication,
        TF communication, and enables/disables RPCs. Additionally, it sets up
        action servers, publishers, and subscribers for recording and speech
        detection functionalities.
        Args:
            package (dict): A dictionary containing configuration parameters for
                            setting up the communication layer. Expected keys are:
                            - "namespace": The namespace for the simulation communication.
        """
        self.set_simulation_communication(package["namespace"])
        self.set_tf_communication(package)
        self.set_enable_disable_rpcs(self.base_topic, self.enable_callback, self.disable_callback)

        self.record_action_server = self.commlib_factory.getActionServer(
            callback = self.on_goal_record,
            action_name = self.base_topic + ".record"
        )
        self.record_pub = self.commlib_factory.getPublisher(
            topic = self.base_topic + ".record.notify"
        )
        self.detect_speech_sub = self.commlib_factory.getSubscriber(
            topic = self.base_topic + ".speech_detected",
            callback = self.speech_detected
        )

    def speech_detected(self, message):
        """
        Handles the event when speech is detected.

        Args:
            message (dict): A dictionary containing information about the detected speech.
                - "speaker" (str): The source of the speech.
                - "text" (str): The detected speech text.
                - "language" (str): The language of the detected speech.

        Logs:
            Logs the detected speech information including the source, language, and text.
        """
        source = message["speaker"]
        text = message["text"]
        language = message["language"]
        self.logger.info("Speech detected from %s [%s]: %s", source, language, text)

    def enable_callback(self, _):
        """
        Enables the microphone callback and updates the internal state.
        Args:
            _ (Any): Placeholder argument, not used.
        Returns:
            dict: A dictionary indicating that the microphone has been enabled.
        """
        self.info["enabled"] = True

        # self.enable_rpc_server.run()
        # self.disable_rpc_server.run()

        # self.record_action_server.run()

        return {"enabled": True}

    def disable_callback(self, _):
        """
        Disables the microphone callback.

        This method sets the "enabled" status of the microphone to False 
        and returns a dictionary indicating the disabled status.

        Args:
            _ (any): A placeholder argument that is not used.

        Returns:
            dict: A dictionary with the key "enabled" set to False.
        """
        self.info["enabled"] = False
        return {"enabled": False}

    def start(self):
        """
        Starts the sensor and waits for the simulator to start.
        This method logs a message indicating that the sensor is waiting to start.
        It then enters a loop, checking if the simulator has started, and sleeps for 1 second
        intervals until the simulator is started. Once the simulator is started, it logs a message
        indicating that the sensor has started.
        Note: The RPC server actions (enable, disable, record) are currently commented out.
        """
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)
        self.logger.info("Sensor %s started", self.name)

        # self.enable_rpc_server.run()
        # self.disable_rpc_server.run()

        # self.record_action_server.run()

    def stop(self):
        """
        Stops the microphone controller by disabling the enabled flag and stopping
        the RPC servers and the record action server.
        This method performs the following actions:
        1. Sets the "enabled" flag in the info dictionary to False.
        2. Stops the enable RPC server.
        3. Stops the disable RPC server.
        4. Stops the record action server.
        """
        self.info["enabled"] = False
        self.enable_rpc_server.stop()
        self.disable_rpc_server.stop()

        self.record_action_server.stop()

    def on_goal_record(self, goalh):
        """
        Handles the goal to start recording from the microphone.
        Args:
            goalh (GoalHandle): The goal handle containing the recording parameters.
        Returns:
            dict: A dictionary containing the timestamp of the recording and, if applicable, the 
            recorded data and volume.
        Behavior:
            - Logs the start of the recording.
            - Checks if the microphone is enabled. If not, returns an empty dictionary.
            - Waits if the microphone is currently blocked by another process.
            - Extracts the duration from the goal handle.
            - Publishes the recording duration.
            - Depending on the mode ("mock" or "simulation"), handles the recording process:
                - In "mock" mode, simulates a recording for the specified duration.
                - In "simulation" mode, interacts with a tf_affection_rpc service to determine 
                the closest sound source or human and simulates recording based on the proximity.
            - Handles cancellation events during the recording process.
            - Logs the completion of the recording and unblocks the microphone.
        """
        self.logger.info("%s recording started", self.name)
        if self.info["enabled"] is False:
            return {}

        # Concurrent speaker calls handling
        while self.blocked:
            time.sleep(0.1)
        self.logger.info("Microphone unlocked")
        self.blocked = True

        try:
            duration = goalh.data["duration"]
        except Exception: # pylint: disable=broad-except
            self.logger.error("%s goal had no duration as parameter", self.name)

        self.record_pub.publish({
            "duration": duration
        })

        ret = {
            'timestamp': time.time()
        }
        if self.info["mode"] == "mock":
            now = time.time()
            self.logger.info("Recording...")
            while time.time() - now < duration:
                if goalh.cancel_event.is_set():
                    self.logger.info("Cancel got")
                    self.blocked = False
                    return ret
                time.sleep(0.1)

            ret["record"] = base64.b64encode(b'0x55').decode("ascii")
            ret["volume"] = 100

        elif self.info["mode"] == "simulation":
            # Ask tf for proximity sound sources or humans
            res = self.tf_affection_rpc.call({
                'name': self.name
            })
            # Get the closest:
            clos = None
            clos_type = None
            clos_info = None
            clos_d = 100000.0
            for x in res:
                if res[x]['distance'] < clos_d:
                    clos = x
                    clos_d = res[x]['distance']

            wav = "Silent.wav"
            if clos is None:
                pass
            elif res[clos]['type'] == 'sound_source':
                clos_type = 'sound_source'
                clos_info = res[clos]['info']
                if res[clos]['info']['language'] == 'EL':
                    wav = "greek_sentence.wav"
                else:
                    wav = "english_sentence.wav"
            elif res[clos]['type'] == "human":
                clos_type = 'human'
                clos_info = res[clos]['info']
                if res[clos]['info']["sound"] == 1:
                    if res[clos]['info']["language"] == "EL":
                        wav = "greek_sentence.wav"
                    else:
                        wav = "english_sentence.wav"

            now = time.time()
            self.logger.info("Recording... %s, %s", clos_type, clos_info)
            while time.time() - now < duration:
                if goalh.cancel_event.is_set():
                    self.logger.info("Cancel got")
                    self.blocked = False
                    return ret
                time.sleep(0.1)
            self.logger.info("Recording done")

            ret["record"] = self.load_wav(wav)
            ret["volume"] = 100

        self.logger.info("%s recording finished", self.name)
        self.blocked = False
        return ret

    def load_wav(self, path):
        """
        Load a WAV file, read its contents, and encode it in base64.

        Args:
            path (str): The relative path to the WAV file within the resources directory.

        Returns:
            str: The base64 encoded string of the WAV file's binary data.
        """
        # Read from file
        dirname = Path(__file__).resolve().parent
        fil = str(dirname) + '/../../resources/' + path
        self.logger.info("Reading sound from %s", fil)
        f = wave.open(fil, 'rb')
        data = bytearray()
        sample = f.readframes(256)
        while sample:
            for s in sample:
                data.append(s)
            sample = f.readframes(256)
        f.close()
        source = base64.b64encode(data).decode("ascii")
        return source
