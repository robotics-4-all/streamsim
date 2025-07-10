"""
File that contains the microphone controller.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging
import base64
# import wave
from pathlib import Path

from stream_simulator.base_classes import BaseThing

class MicrophoneController(BaseThing):
    """
    MicrophoneController is a class that simulates a microphone sensor in a robotic system.
    Attributes:
        logger (logging.Logger): Logger instance for logging information.
        name (str): Name of the microphone controller.
        info (dict): Dictionary containing microphone information and configuration.
        base_topic (str): Base topic for communication.
        blocked (bool): Flag indicating if the microphone is currently blocked.
        actors (list): List of actors associated with the microphone.
        record_action_server (ActionServer): Action server for recording actions.
        listen_action_server (ActionServer): Action server for listening actions.
        enable_rpc_server (RPCService): RPC service for enabling the microphone.
        disable_rpc_server (RPCService): RPC service for disabling the microphone.
        record_pub (Publisher): Publisher for recording notifications.
        detect_speech_sub (Subscriber): Subscriber for speech detection notifications.
    Methods:
        __init__(conf=None, package=None): Initializes the MicrophoneController with the 
        given configuration and package.
        speech_detected(message): Callback function for handling detected speech messages.
        load_wav(path): Loads a WAV file from the specified path and returns its base64 
        encoded content.
        on_goal(goalh): Callback function for handling recording goals.
        on_goal_listen(goalh): Callback function for handling listening goals.
        enable_callback(message): Callback function for enabling the microphone.
        disable_callback(message): Callback function for disabling the microphone.
        start(): Starts the microphone controller.
        stop(): Stops the microphone controller.
    """
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        id_ = "d_microphone_" + str(BaseThing.id + 1)
        name = id_
        self.name = name
        if 'name' in conf:
            name = conf['name']

        _category = "sensor"
        _class = "audio"
        _subclass = "microphone"
        _pack = package["name"]
        _namespace = package["namespace"]

        # BaseThing initialization
        super().__init__(id_, auto_start=False)
        self.set_simulation_communication(_namespace)

        info = {
            "type": "MICROPHONE",
            "brand": "usb_mic",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": name,
            "place": conf["place"],
            "id": "id_" + str(id_),
            "enabled": True,
            "orientation": float(conf["orientation"]),
            "queue_size": 0,
            "mode": package["mode"],
            "namespace": package["namespace"],
            "device_name": package["device_name"],
            "actors": package["actors"],
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
        self.base_topic = info["base_topic"]
        self.name = info["name"]

        self.set_tf_communication(package)

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

        self.blocked = False

        # merge actors
        self.actors = []
        for i in info["actors"]:
            for h in info["actors"][i]:
                k = h
                h["type"] = i
                self.actors.append(k)

        self.record_action_server = self.commlib_factory.get_action_server(
            callback = self.on_goal,
            action_name = self.base_topic + ".record"
        )
        self.listen_action_server = self.commlib_factory.get_action_server(
            callback = self.on_goal_listen,
            action_name = self.base_topic  + ".listen"
        )

        self.record_pub = self.commlib_factory.get_publisher(
            topic = self.base_topic  + ".record.notify"
        )

        self.detect_speech_sub = self.commlib_factory.get_subscriber(
            topic = self.base_topic  + ".speech_detected",
            callback = self.speech_detected
        )

        self.detection_subscriber = self.commlib_factory.get_subscriber(
            topic = self.base_topic + ".detect",
            callback = self.detection_callback,
        )
        self.state_publisher = self.commlib_factory.get_publisher(
            topic=self.base_topic + ".detection"
        )

        self.tf_detection_rpc_client = self.commlib_factory.get_rpc_client(
            rpc_name=package["tf_detect_rpc_topic"]
        )

        self.commlib_factory.run()

        self.tf_declare_rpc.call(tf_package)

    def detection_callback(self, message):
        """
        Callback function for handling detection messages.

        Args:
            message (dict): A dictionary containing the detection message. 
                            It must have a 'detection' key indicating the type of detection.

        Returns:
            None

        The function sends a request to the tf_detection_rpc_client with the detection type 
        and the name of the current instance. The response from the client is printed.
        """
        detection_type = message['detection'] # to be detected
        print("Detection message received: ", detection_type)
        detection_result = self.tf_detection_rpc_client.call({
            'name': self.name,
            # face, gender, age, emotion, motion, qr, barcode, text, color, robot
            'type': detection_type,
        })
        self.state_publisher.publish(detection_result)

    def speech_detected(self, message):
        """
        Handles the event when speech is detected.

        Args:
            message (dict): A dictionary containing information about the detected speech.
                - speaker (str): The source of the speech.
                - text (str): The detected speech text.
                - language (str): The language of the detected speech.

        Logs:
            Logs the detected speech information including the source, language, and text.
        """
        source = message["speaker"]
        text = message["text"]
        language = message["language"]
        self.logger.info("Speech detected from %s [%s]: %s", source, language, text)

    def load_wav(self, path):
        """
        Loads a WAV file from the specified path, reads its contents, and encodes it in base64.

        Args:
            path (str): The relative path to the WAV file within the resources directory.

        Returns:
            str: The base64 encoded string of the WAV file's binary data.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            wave.Error: If there is an error reading the WAV file.
        """
        # Read from file
        dirname = Path(__file__).resolve().parent
        fil = str(dirname) + '/../../resources/' + path
        self.logger.info("Reading sound from %s", fil)
        # NOTE: Wave is broken
        # f = wave.open(fil, 'rb')
        # data = bytearray()
        # sample = f.readframes(256)
        # while sample:
        #     for s in sample:
        #         data.append(s)
        #     sample = f.readframes(256)
        # f.close()
        # source = base64.b64encode(data).decode("ascii")
        source = ""
        return source

    def on_goal(self, goalh):
        """
        Handles the goal event for the microphone controller.
        This method starts the recording process based on the provided goal, handles concurrent 
        speaker calls, and simulates or mocks the recording process depending on the mode specified 
        in the `info` attribute.
        Args:
            goalh: The goal handle containing the recording parameters.
        Returns:
            dict: A dictionary containing the recording result with the following keys:
                - header: A dictionary with timestamp information.
                - record: The base64 encoded recording data.
                - volume: The volume level of the recording.
        Raises:
            Exception: If the goal does not contain a duration parameter.
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

        timestamp = time.time()
        secs = int(timestamp)
        nanosecs = int((timestamp-secs) * 10**(9))
        ret = {
            "header":{
                "stamp":{
                    "sec": secs,
                    "nanosec": nanosecs
                }
            },
            "record": "",
            "volume": 0
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
            affections = res['affections']
            # Get the closest:
            clos = None
            clos_type = None
            clos_info = None
            clos_d = 100000.0
            for x in affections:
                if affections[x]['distance'] < clos_d:
                    clos = x
                    clos_d = affections[x]['distance']

            wav = "Silent.wav"
            if clos is None:
                pass
            elif affections[clos]['type'] == 'sound_source':
                clos_type = 'sound_source'
                clos_info = affections[clos]['info']
                if affections[clos]['info']['language'] == 'EL':
                    wav = "greek_sentence.wav"
                else:
                    wav = "english_sentence.wav"
            elif affections[clos]['type'] == "human":
                clos_type = 'human'
                clos_info = affections[clos]['info']
                if affections[clos]['info']["sound"] == 1:
                    if affections[clos]['info']["language"] == "EL":
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

    def on_goal_listen(self, goalh):
        """
        Handles the goal to listen for a specified duration and language.
        This function starts the listening process, checks if the microphone is enabled,
        and handles concurrent speaker calls. It then attempts to retrieve the duration
        and language from the goal data and logs the listening process.
        Args:
            goalh (object): An object containing the goal data with 'duration' and 'language' 
            parameters.
        Returns:
            dict: A dictionary containing the transcribed text. Currently, this is a dummy 
            implementation and returns a placeholder text.
        """
        self.logger.info("%s listening started", self.name)
        if self.info["enabled"] is False:
            return {}

        # Concurrent speaker calls handling
        while self.blocked:
            time.sleep(0.1)
        self.logger.info("Microphone unlocked")
        self.blocked = True

        # NOTE!!! This is a dummy implementation
        text = "IMPLEMENT THIS FUNCTIONALITY!"

        if "duration" not in goalh.data or "language" not in goalh.data:
            self.logger.error("%s goal had no duration and language as parameter", self.name)
            return {'text': "ERROR"}

        self.logger.info("Listening finished: %s", )
        self.blocked = False
        return {'text': text}

    def start(self):
        """
        Starts the microphone sensor.

        This method logs a message indicating that the sensor is waiting to start.
        It then enters a loop, sleeping for 1 second at a time, until the simulator
        has started. Once the simulator has started, it logs a message indicating
        that the sensor has started.
        """
        self.logger.info("Sensor %s waiting to start", self.name)
        while not self.simulator_started:
            time.sleep(1)
        self.logger.info("Sensor %s started", self.name)

    def stop(self):
        """
        Stops the microphone controller by invoking the stop method of the commlib_factory.
        """
        self.commlib_factory.stop()
