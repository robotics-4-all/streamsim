"""
File that exposes the controllers.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import

from .robot_button_array import ButtonArrayController
from .robot_camera import CameraController
from .robot_env import EnvController
from .robot_imu import ImuController
from .robot_microphone import MicrophoneController
from .robot_sonar import SonarController
from .robot_button import ButtonController
from .robot_rfid_reader import RfidReaderController
from .robot_leds import LedsController
from .robot_motion import MotionController
from .robot_pan_tilt import PanTiltController
from .robot_speaker import SpeakerController

from .environmental_relay import EnvRelayController
from .environmental_ph_sensor import EnvPhSensorController
from .environmental_temperature_sensor import EnvTemperatureSensorController
from .environmental_humidity_sensor import EnvHumiditySensorController
from .environmental_gas_sensor import EnvGasSensorController
from .environmental_camera import EnvCameraController
from .environmental_distance import EnvDistanceController
from .environmental_linear_alarm import EnvLinearAlarmController
from .environmental_area_alarm import EnvAreaAlarmController
from .environmental_ambient_light import EnvAmbientLightController
from .environmental_pan_tilt import EnvPanTiltController
from .environmental_speaker import EnvSpeakerController
from .environmental_light import EnvLightController
from .environmental_thermostat import EnvThermostatController
from .environmental_microphone import EnvMicrophoneController
from .environmental_humidifier import EnvHumidifierController

from .actor_human import HumanActor
from .actor_superman import SupermanActor
from .actor_sound_source import SoundSourceActor
from .actor_qr import QrActor
from .actor_barcode import BarcodeActor
from .actor_color import ColorActor
from .actor_text import TextActor
from .actor_rfid_tag import RfidTagActor
from .actor_fire import FireActor
from .actor_water import WaterActor
