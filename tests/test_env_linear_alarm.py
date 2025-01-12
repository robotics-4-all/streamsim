"""
Test to check the robot motion.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import sys
import traceback
import time

from stream_simulator.connectivity import CommlibFactory

class Test(unittest.TestCase):
    """
    Test class for verifying the functionality of the linear alarm system 
    in the simulated environment.
    This class contains setup, teardown, and test methods to ensure that the 
    linear alarm system behaves as expected when the robot is teleported and 
    moved within the simulation.
    Methods:
        setUp(): Initializes the test environment, including creating RPC clients and subscribers.
        linear_alarm_callback(message): Callback function for handling linear alarm data messages.
        linear_alarm_triggers_callback(message): Callback function for handling 
            linear alarm trigger messages.
        test_get(): Tests the behavior of the linear alarm system by teleporting 
            and moving the robot.
        tearDown(): Cleans up the test environment after each test case.
    """

    def setUp(self):
        """
        Set up the test environment for linear alarm tests.
        This method initializes the necessary components for testing, including:
        - Creating a CommlibFactory instance with a specified node name.
        - Setting up RPC clients for teleportation and moving by distance.
        - Subscribing to topics for linear alarm data and triggers.
        - Initializing alarm and triggers values.
        - Running the communication factory.
        Attributes:
            cfact (CommlibFactory): The communication library factory instance.
            pose (None): Placeholder for pose information (currently not used).
            teleport_rpc (RpcClient): RPC client for teleportation.
            move_distance_rpc (RpcClient): RPC client for moving by distance.
            alarm_value (None): Placeholder for alarm value (initially None).
            triggers_value (None): Placeholder for triggers value (initially None).
        """
        self.cfact = CommlibFactory(node_name = "Test")
        sim_name = "streamsim.testinguid"
        self.pose = None

        self.teleport_rpc = self.cfact.get_rpc_client(
            rpc_name = f"{sim_name}.robot_1.teleport",
            auto_run = False
        )

        # RPC for moving by distance
        self.move_distance_rpc = self.cfact.get_rpc_client(
            rpc_name = f"{sim_name}.robot_1.actuator.motion.twist.skid_steer_robot_1.move.distance",
            auto_run = False
        )

        self.cfact.get_subscriber(
            topic = f"{sim_name}.world.office.sensor.alarm.linear_alarm.alarm_linear.data",
            callback = self.linear_alarm_callback,
            auto_run = False
        )

        self.cfact.get_subscriber(
            topic = f"{sim_name}.world.office.sensor.alarm.linear_alarm.alarm_linear.triggers",
            callback = self.linear_alarm_triggers_callback,
            auto_run = False
        )

        self.alarm_value = None
        self.triggers_value = None

        self.cfact.run()

    def linear_alarm_callback(self, message):
        """
        Callback function to handle linear alarm messages.

        This function is triggered when a linear alarm message is received.
        It updates the alarm_value attribute with the received message and prints
        the linear alarm value.

        Args:
            message (str): The linear alarm message received.
        """
        self.alarm_value = message
        print(f"Linear alarm value: {message}")

    def linear_alarm_triggers_callback(self, message):
        """
        Callback function that handles linear alarm triggers.

        This function is called when a linear alarm trigger message is received.
        It updates the `triggers_value` attribute with the received message and
        prints the message.

        Args:
            message (str): The message received from the linear alarm trigger.
        """
        self.triggers_value = message
        print(f"Linear alarm triggers: {message}")

    def test_get(self):
        """
        Test the functionality of teleporting the robot and checking alarm and trigger values.
        This test performs the following steps:
        1. Teleports the robot to coordinates (50.0, 50.0) with theta 0.
        2. Verifies that the alarm value is not None and its value is an empty list.
        3. Teleports the robot to coordinates (9.8, 50.0) with theta 0.
        4. Moves the robot a distance of 0.3 with a linear speed of 0.25.
        5. Verifies that the alarm value is not None and its value is an empty list.
        6. Verifies that the triggers value is not None, contains "robot_1" in 
            the trigger, and its value is greater than or equal to 1.
        If any exception occurs during the test, it prints the traceback and fails the test.
        """
        try:
            print("Teleporting robot")
            self.teleport_rpc.call({
                'x': 50.0,
                'y': 50.0,
                'theta': 0
            })

            time.sleep(1)
            self.assertIsNotNone(self.alarm_value)
            self.assertEqual(self.alarm_value['value'], [])

            print("Teleporting robot")
            self.teleport_rpc.call({
                'x': 9.8,
                'y': 50.0,
                'theta': 0
            })
            time.sleep(1)
            self.move_distance_rpc.call({
                'distance': 0.3,
                'linear': 0.25,
            })
            time.sleep(1)

            self.assertIsNotNone(self.alarm_value)
            self.assertEqual([], self.alarm_value['value'])

            self.assertIsNotNone(self.triggers_value)
            self.assertTrue("robot_1" in self.triggers_value['trigger'])
            self.assertGreaterEqual(self.triggers_value['value'], 1)

            print("Teleporting robot back to start")
            self.teleport_rpc.call({
                'x': 50.0,
                'y': 50.0,
                'theta': 0
            })

        except: # pylint: disable=bare-except
            traceback.print_exc(file=sys.stdout)
            self.fail("Test failed due to exception")

    def tearDown(self):
        """
        Tear down method for cleaning up after each test case.

        This method is called after each test case has been executed.
        It can be used to release resources, reset states, or perform
        any necessary cleanup operations. Currently, it does not perform
        any actions.
        """
        self.cfact.stop()

if __name__ == '__main__':
    unittest.main()
