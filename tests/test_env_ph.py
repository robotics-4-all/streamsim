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
    Test class for verifying the functionality of the pH sensor data retrieval.
    This class contains setup, teardown, and test methods to ensure that the pH sensor
    data is correctly received and validated.
    Methods
    -------
    setUp():
        Initializes the test environment, sets up the CommlibFactory, and 
            subscribes to the pH sensor data topic.
    ph_sensor_callback(message):
        Callback method that is triggered when a pH sensor data message is received. 
        It stores the pH value.
    test_get():
        Tests if the pH value is received and checks if it is approximately equal to 7.4.
    tearDown():
        Cleans up the test environment after each test case by stopping the CommlibFactory.
    """
    def setUp(self):
        self.cfact = CommlibFactory(node_name = "Test")
        sim_name = "streamsim.testinguid"
        self.ph_value = None

        self.cfact.get_subscriber(
            topic = f"{sim_name}.world.field.sensor.env.ph.ph_sensor.data",
            callback = self.ph_sensor_callback,
            auto_run = False
        )

        self.cfact.run()

    def ph_sensor_callback(self, message):
        """
        Callback function to handle pH sensor messages.

        Args:
            message (float): The pH value received from the sensor.
        """
        self.ph_value = message
        print(f"pH value: {message}")

    def test_get(self):
        """
        Test the `get` method for retrieving pH value.
        This test method performs the following steps:
        1. Waits for 1 second to simulate delay.
        2. Asserts that the `ph_value` attribute is not None.
        3. Asserts that the `value` key in the `ph_value` dictionary is approximately 7.4 with a delta of 0.1.
        If any exception occurs during the test, it prints the traceback and fails the test with an appropriate message.
        Raises:
            AssertionError: If any of the assertions fail.
            Exception: If any other exception occurs during the test execution.
        """
        try:
            time.sleep(1)
            self.assertIsNotNone(self.ph_value)
            self.assertAlmostEqual(float(self.ph_value['value']), 7.4, delta=0.1)

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
