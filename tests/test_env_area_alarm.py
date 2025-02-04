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
    Test class for the environment area alarm functionality.
    This class contains unit tests for verifying the behavior of the area alarm
    system in the simulated environment. It uses the unittest framework to define
    test cases and assertions.
    Attributes:
        cfact (CommlibFactory): The communication library factory instance.
        pose (None): Placeholder attribute for the robot's pose.
        teleport_rpc (RPCClient): The RPC client for teleporting the robot.
        alarm_value (str): The value received from the area alarm subscriber.
        triggers_value (str): The value received from the area alarm triggers subscriber.
    Methods:
        setUp():
            Set up method for initializing the test environment.
            This method is called before each test case is executed.
        area_alarm_callback(message):
        area_alarm_triggers_callback(message):
        test_get():
            Test case for verifying the area alarm functionality.
            This test checks if the alarm value is not None and performs a teleport
            operation for the robot.
        tearDown():
            It can be used to release resources, reset states, or perform any
            necessary cleanup operations.
    """
    def setUp(self):
        self.cfact = CommlibFactory(node_name = "Test")
        sim_name = "streamsim.testinguid"
        self.pose = None

        self.teleport_rpc = self.cfact.get_rpc_client(
            rpc_name = f"{sim_name}.robot_1.teleport",
            auto_run = False
        )

        self.cfact.get_subscriber(
            topic = f"{sim_name}.world.office.sensor.alarm.area_alarm.areaalarm.data",
            callback = self.area_alarm_callback,
            auto_run = False
        )

        self.cfact.get_subscriber(
            topic = f"{sim_name}.world.office.sensor.alarm.area_alarm.areaalarm.triggers",
            callback = self.area_alarm_triggers_callback,
            auto_run = False
        )

        self.alarm_value = []
        self.triggers_value = None

        self.cfact.run()

    def area_alarm_callback(self, message):
        """
        Callback function to handle area alarm messages.

        Args:
            message (str): The message received from the area alarm subscriber.

        Returns:
            None
        """
        self.alarm_value = message
        print(f"Area alarm value: {message}")

    def area_alarm_triggers_callback(self, message):
        """
        Callback function to handle area alarm triggers.

        Args:
            message (str): The message received from the area alarm triggers subscriber.

        Returns:
            None
        """
        self.triggers_value = message
        print(f"Area alarm triggers: {message}")

    def test_get(self):
        """
        Test the `get` method for the environment area alarm.
        This test performs the following steps:
        1. Teleports the robot to coordinates (50.0, 50.0) with theta 0.
        2. Waits for 1 second.
        3. Asserts that `alarm_value` is not None and its 'value' is an empty list.
        4. Teleports the robot to coordinates (12.0, 12.0) with theta 0.
        5. Waits for 1 second.
        6. Asserts that `alarm_value` is not None and 'robot_1' is in its 'value'.
        7. Asserts that `triggers_value` is not None and its 'value' is 1.
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
                'x': 12.0,
                'y': 12.0,
                'theta': 0
            })
            time.sleep(1)

            self.assertIsNotNone(self.alarm_value)
            self.assertTrue('robot_1' in self.alarm_value['value'])

            self.assertIsNotNone(self.triggers_value)
            self.assertGreater(self.triggers_value['value'], 0)

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
