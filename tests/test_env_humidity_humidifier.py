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
    Test class for testing the environment humidity humidifier.
    This class contains unit tests for verifying the functionality of the
    humidity humidifier in a simulated environment. It uses the unittest
    framework to define test cases and assertions.
    Methods:
        setUp():
            Initializes the test environment, including creating RPC clients
            and subscribers, and running the communication factory.
        humidity_sensor_callback(message):
            Callback function for handling humidity sensor data. Updates the
            humidity value with the received message.
        test_get():
            Tests the functionality of setting and getting humidity values
            using the humidifier RPC clients. Asserts that the humidity values
            are set and retrieved correctly.
        tearDown():
            Cleans up the test environment after each test case. Stops the
            communication factory.
    """
    def setUp(self):
        self.cfact = CommlibFactory(node_name = "Test")
        sim_name = "streamsim.testinguid"
        self.humidity_value = None

        self.humidifier_set_rpc = self.cfact.get_rpc_client(
            rpc_name = f"{sim_name}.world.office.actuator.env.humidifier.hum_X.set",
            auto_run = False
        )

        self.humidifier_get_rpc = self.cfact.get_rpc_client(
            rpc_name = f"{sim_name}.world.office.actuator.env.humidifier.hum_X.get",
            auto_run = False
        )

        self.cfact.get_subscriber(
            topic = f"{sim_name}.world.office.sensor.env.humidity.humidity_sensor.data",
            callback = self.humidity_sensor_callback,
            auto_run = False
        )

        self.cfact.run()

    def humidity_sensor_callback(self, message):
        """
        Callback function to handle incoming humidity sensor messages.

        Args:
            message (float): The humidity value received from the sensor.
        """
        self.humidity_value = message
        print(f"Humidity value: {message}")

    def test_get(self):
        """
        Test the `get` method of the humidifier.
        This test performs the following steps:
        1. Sets the humidity to 0.0 and verifies that the humidity value is not 
            None and is approximately 60.0.
        2. Sets the humidity to 80.0 and verifies that the stored humidity value 
            is approximately 80.0.
        3. Verifies that the humidity value is greater than or equal to 63.0 after a delay.
        If any exception occurs during the test, it prints the traceback and fails the test.
        Raises:
            AssertionError: If any of the assertions fail.
        """

        try:
            self.humidifier_set_rpc.call({'humidity': 0.0})

            time.sleep(0.5)
            self.assertIsNotNone(self.humidity_value)
            self.assertAlmostEqual(float(self.humidity_value['value']), 60.0, delta=0.5)

            self.humidifier_set_rpc.call({'humidity': 80.0})
            stored_val = self.humidifier_get_rpc.call({})
            self.assertAlmostEqual(float(stored_val['humidity']), 80.0, delta=0.01)

            time.sleep(0.5)
            self.assertGreaterEqual(float(self.humidity_value['value']), 63.0)

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
