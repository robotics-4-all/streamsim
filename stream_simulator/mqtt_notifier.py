"""
File that contains the MQTTNotifier class.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging

from stream_simulator.connectivity import CommlibFactory

class MQTTNotifier:
    """
    MQTTNotifier class is responsible for handling MQTT notifications for various 
    events such as linear alarms, area alarms, RFID reader data, and robot poses. 
    It uses the CommlibFactory to create publishers and subscribers for different 
    topics and provides callback functions to handle incoming messages.
    Attributes:
        logger (logging.Logger): Logger instance for logging information.
        commlib_factory (CommlibFactory): Remote CommlibFactory instance for MQTT communication.
        notify_pub (Publisher): Publisher instance for sending notifications.
        local_commlib (CommlibFactory): Local CommlibFactory instance for internal communication.
        robot_pose_sub (Subscriber): Subscriber instance for robot pose messages.
        linear_alarms_sub (Subscriber): Subscriber instance for linear alarm triggers.
        area_alarms_sub (Subscriber): Subscriber instance for area alarm triggers.
        rfid_reader_sub (Subscriber): Subscriber instance for RFID reader data.
    Methods:
        __init__(self, uid=None):
            Initializes the MQTTNotifier instance, sets up publishers and 
            subscribers, and starts the CommlibFactory instances.
        linear_alarm_triggers_callback(self, message):
            Callback function to handle linear alarm triggers. Publishes the message to 
            the notify_pub topic and logs the information.
        area_alarm_triggers_callback(self, message):
            Callback function to handle area alarm triggers. Publishes the message 
            to the notify_pub topic and logs the information.
        rfid_reader_callback(self, message):
            Callback function for handling RFID reader messages. Publishes the 
            message to the notify_pub topic if tags are present and logs the information.
        dispatch_log(self, message):
            Dispatches a log message to the notify_pub topic and logs the information.
        dispatch_sensor_pose(self, message):
            Dispatches a sensor pose message to the notify_pub topic and logs the information.
        dispatch_detection(self, message):
            Dispatches a detection message to the notify_pub topic and logs the 
            information.
        robot_pose_callback(self, message):
            Callback function to handle robot pose messages. Publishes the 
            extracted information to the notify_pub topic and logs the information.
    """
    def __init__(self,
                 uid = None
                 ):

        self.logger = logging.getLogger(__name__)
        self.prints = False

        # Remote CommlibFactory
        self.commlib_factory = CommlibFactory(
            node_name = "MQTTNotifierRemote",
            interface = "mqtt",
        )

        self.notify_pub = self.commlib_factory.get_publisher(
            topic = f"streamsim.{uid}.notify",
        )

        # Local CommlibFactory
        self.local_commlib = CommlibFactory(
            node_name = "MQTTNotifierLocal",
        )

        self.robot_pose_sub = self.local_commlib.create_psubscriber(
            topic = "streamsim.*.*.pose.internal",
            on_message = self.robot_pose_callback,
        )

        self.robot_crash_sub = self.local_commlib.create_psubscriber(
            topic = "streamsim.*.*.crash",
            on_message = self.robot_crash_callback,
        )

        self.linear_alarms_sub = self.local_commlib.create_psubscriber(
            topic = "streamsim.*.world.*.sensor.alarm.linear_alarm.*.triggers",
            on_message = self.linear_alarm_triggers_callback,
        )

        self.area_alarms_sub = self.local_commlib.create_psubscriber(
            topic = "streamsim.*.world.*.sensor.alarm.area_alarm.*.triggers",
            on_message = self.area_alarm_triggers_callback,
        )

        self.rfid_reader_sub = self.local_commlib.create_psubscriber(
            topic = "streamsim.*.*.sensor.rf.rfid_reader.*.data",
            on_message = self.rfid_reader_callback,
        )

        self.effector_state_change_sub = self.local_commlib.create_psubscriber(
            topic = f"streamsim.{uid}.state.internal",
            on_message = self.effector_state_change_callback,
        )

        # Start the CommlibFactory
        self.commlib_factory.run()
        self.local_commlib.run()

        self.logger.info("MQTT Notifier started")

    def robot_crash_callback(self, message, origin):
        """
        Callback function to handle robot crash messages.

        This function is triggered when a robot crash message is received.
        It publishes the message to the notify_pub topic and logs the information.

        Args:
            message (dict): The message containing the robot crash data.
        """
        origin = origin.split(".")[2]
        self.notify_pub.publish({
            'type': "robot_crash",
            'data': {
                'message': message,
                'origin': origin,
            }
        })

    def effector_state_change_callback(self, message, _):
        """
        Callback function to handle effector state change messages.

        This function is triggered when an effector state change message is received.
        It publishes the message to the notify_pub topic and logs the information.

        Args:
            message (dict): The message containing the effector state change data.
        """
        self.notify_pub.publish({
            'type': "effector_state_change",
            'data': message,
        })
        if self.prints:
            self.logger.info("UI inform %s: %s", "effector_state_change", message)

    def linear_alarm_triggers_callback(self, message, _):
        """
        Callback function to handle linear alarm triggers.

        This function is called when a linear alarm trigger message is received.
        It publishes the message to the notify_pub topic and logs the information.

        Args:
            message (dict): The message containing the linear alarm trigger data.
        """
        self.notify_pub.publish({
            'type': "linear_alarm_triggers",
            'data': message,
        })
        if self.prints:
            self.logger.info("UI inform %s: %s", "linear_alarm_triggers", message)

    def area_alarm_triggers_callback(self, message, _):
        """
        Callback function to handle area alarm triggers.

        This function is called when an area alarm trigger message is received.
        It publishes the message to the notify_pub topic and logs the information.

        Args:
            message (dict): The message containing the area alarm trigger data.
        """
        self.notify_pub.publish({
            'type': "area_alarm_triggers",
            'data': message,
        })
        if self.prints:
            self.logger.info("UI inform %s: %s", "area_alarm_triggers", message)

    def rfid_reader_callback(self, message, _):
        """
        Callback function for handling RFID reader messages.
        This function is triggered when an RFID reader message is received. 
        It checks if the message contains any tags.
        If tags are present, it publishes the message to the notify_pub topic 
        and logs the information.
        Args:
            message (dict): The message received from the RFID reader. It is 
            expected to have the following structure:
                {
                    'data': {
                        'tags': list
                    }
                }
        """
        if len(message['data']['tags']) == 0:
            return

        self.notify_pub.publish({
            'type': "rfid_reader",
            'data': message,
        })
        if self.prints:
            self.logger.info("UI inform %s: %s", "rfid_reader", message)

    def dispatch_log(self, message):
        """
        Dispatches a log message to the notify_pub topic.

        Args:
            message (str): The log message to dispatch.

        Returns:
            None
        """
        self.notify_pub.publish({
            'type': "log",
            'data': message,
        })
        if self.prints:
            self.logger.info("UI inform %s: %s", "log", message)

    def dispatch_sensor_pose(self, message):
        """
        Dispatches a sensor pose message to the notify_pub topic.

        Args:
            message (dict): A dictionary containing the sensor pose information with keys:
                - 'x' (float): The x-coordinate of the sensor's position.
                - 'y' (float): The y-coordinate of the sensor's position.
                - 'theta' (float): The orientation of the sensor in radians.
                - 'resolution' (float): The resolution of the sensor's position data.
                - 'name' (str): The name associated with the sensor's pose data.

        Returns:
            None
        """
        self.notify_pub.publish({
            'type': "sensor_pose",
            'data': message,
        })
        if self.prints:
            self.logger.info("UI inform %s: %s", "sensor_pose", message)

    def dispatch_detection(self, message):
        """
        Dispatches a detection message to the notifier.

        This method publishes a detection message to the notify_pub publisher.
        If the prints attribute is set to True, it also logs the detection message.

        Args:
            message (str): The detection message to be dispatched.
        """
        self.notify_pub.publish({
            'type': "detection",
            'data': message,
        })
        if self.prints:
            self.logger.info("UI inform %s: %s", "detection", message)

    def robot_pose_callback(self, message, _):
        """
        Callback function to handle robot pose messages.

        This function is triggered when a new robot pose message is received. It extracts
        relevant information from the message, constructs a payload, and publishes it to
        the notify_pub topic. Additionally, it logs the information for debugging purposes.

        Args:
            message (dict): A dictionary containing the robot pose information with keys:
                - 'x' (float): The x-coordinate of the robot's position.
                - 'y' (float): The y-coordinate of the robot's position.
                - 'theta' (float): The orientation of the robot in radians.
                - 'resolution' (float): The resolution of the robot's position data.
                - 'raw_name' (str): The name associated with the robot's pose data.

        Returns:
            None
        """
        payload = {
            'x': message['x'],
            'y': message['y'],
            'theta': message['theta'],
            'resolution': message['resolution'],
            'name': message['raw_name'],
        }
        self.notify_pub.publish({
            'type': "robot_pose",
            'data': payload,
        })
        if self.prints:
            self.logger.info("UI inform %s: %s", "robot_pose", payload)

    def dispatch_env_properties(self, message):
        """
        Dispatches environmental properties message to the notifier.

        This method publishes a message containing environmental properties to the
        notify_pub publisher. If the 'prints' attribute is set to True, it also logs
        the information.

        Args:
            message (dict): The environmental properties data to be dispatched.
        """
        self.notify_pub.publish({
            'type': "env_properties",
            'data': message,
        })
        if self.prints:
            self.logger.info("UI inform %s: %s", "env_properties", message)
