"""
File that contains the human actor.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

from stream_simulator.base_classes import BaseActor

class HumanActor(BaseActor):
    """
    HumanActor is a class that represents a human actor in the simulation environment.
    Attributes:
        logger (logging.Logger): Logger for the human actor.
        info (dict): Information about the human actor including type, configuration, id, and name.
        name (str): Name of the human actor.
        pose (dict): Pose of the human actor with x, y coordinates and theta.
        motion (str): Motion configuration of the human actor.
        sound (str): Sound configuration of the human actor.
        language (str): Language configuration of the human actor.
        range (int): Range of the human actor.
        speech (str): Speech configuration of the human actor.
        emotion (str): Emotion configuration of the human actor.
        gender (str): Gender configuration of the human actor.
        age (str): Age configuration of the human actor.
        id (int): ID of the human actor.
        host (str, optional): Host configuration of the human actor.
    Methods:
        __init__(conf=None, package=None): Initializes the HumanActor with the 
            given configuration and package.
    """
    def __init__(self, conf = None, package = None, precision_mode = False):
        # State dict for automation
        raw_name = conf['name']
        self.properties = {
            'motion': conf['move'],
            'sound': conf['sound'],
            'language': conf['lang'],
            'range': 80 if 'range' not in conf else conf['range'],
            'speech': "" if 'speech' not in conf else conf['speech'],
            'emotion': "neutral" if 'emotion' not in conf else conf['emotion'],
            'gender': "none" if 'gender' not in conf else conf['gender'],
            'age': "-1" if 'age' not in conf else conf['age'],
            'raw_name': conf['name'],
        }

        super().__init__(
            raw_name,
            package,
            conf,
            _type="HUMAN",
            _range=80 if 'range' not in conf else conf['range'],
            _properties=self.properties,
            auto_start=False,
            precision_mode=precision_mode,
        )
        self.logger = super().get_logger()

        # State variables:
        self.motion = None
        self.sound = None
        self.language = None
        self.range = None
        self.speech = None
        self.emotion = None
        self.gender = None
        self.age = None

        self.update_class_state_variables({'state': self.properties})

    def update_class_state_variables(self, step):
        """
        Updates the class state variables from the current state dictionary.

        This method assigns the values from the `state` dictionary to the corresponding
        class attributes: motion, sound, language, range, speech, emotion, gender, and age.
        """
        # Change the state here
        for key in step['state']:
            self.properties[key] = step['state'][key]
        self.motion = self.properties['motion']
        self.sound = self.properties['sound']
        self.language = self.properties['language']
        self.range = self.properties['range']
        self.speech = self.properties['speech']
        self.emotion = self.properties['emotion']
        self.gender = self.properties['gender']
        self.age = self.properties['age']
        self.logger.info("Human %s properties updated: %s", self.name, self.properties)

        self.internal_properties_pub.publish(self.properties)
