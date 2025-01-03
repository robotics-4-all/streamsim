"""
File that tests the thermostat environment temperature.
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
    Test class for the thermostat environment temperature.
    This class contains unit tests for the thermostat environment temperature
    using the CommlibFactory for RPC communication and subscription to temperature
    sensor data.
    Methods:
        setUp():
            Initializes the test environment, sets up RPC clients for setting and
            getting thermostat temperature, and subscribes to temperature sensor data.
        temperature_sensor_callback(message):
            Callback function for handling temperature sensor data messages.
            Updates the temperature attribute with the received message.
        test_get():
            Tests the functionality of setting and getting thermostat temperature.
            Verifies that the temperature sensor data is received and matches expected values.
        tearDown():
            Cleans up the test environment after each test case.
            Stops the CommlibFactory instance.
    """
    def setUp(self):
        self.cfact = CommlibFactory(node_name = "Test")
        sim_name = "streamsim.testinguid"
        self.temperature = None

        self.set_rpc = self.cfact.get_rpc_client(
            rpc_name = f"{sim_name}.world.office.actuator.env.thermostat.thermostat_env.set",
            auto_run = False
        )

        self.get_rpc = self.cfact.get_rpc_client(
            rpc_name = f"{sim_name}.world.office.actuator.env.thermostat.thermostat_env.get",
            auto_run = False
        )

        self.cfact.get_subscriber(
            topic = f"{sim_name}.world.office.sensor.env.temperature.temperature_env.data",
            callback = self.temperature_sensor_callback,
            auto_run = False
        )

        self.cfact.run()

    def temperature_sensor_callback(self, message):
        """
        Callback function to handle temperature sensor messages.

        Args:
            message (float): The temperature value received from the sensor.
        """
        self.temperature = message
        print(f"Temperature value: {message}")

    def test_get(self):
        """
        Test the `get` method of the thermostat environment.
        This test performs the following steps:
        1. Sets the temperature to 0.0 and verifies that the temperature is not None 
            and is approximately 96.6.
        2. Sets the temperature to 130.0, retrieves the stored value, and verifies 
            it is approximately 130.0.
        3. Verifies that the temperature value is greater than or equal to 117.0 
            after a short delay.
        If any exception occurs during the test, it prints the traceback and fails the test.
        Raises:
            AssertionError: If any of the assertions fail.
        """
        try:
            self.set_rpc.call({'temperature': 0.0})

            time.sleep(0.5)
            self.assertIsNotNone(self.temperature)
            self.assertAlmostEqual(float(self.temperature['value']), 96.6, delta=1.0)

            self.set_rpc.call({'temperature': 130.0})
            stored_val = self.get_rpc.call({})
            self.assertAlmostEqual(float(stored_val['temperature']), 130.0, delta=0.01)

            time.sleep(0.5)
            self.assertGreaterEqual(float(self.temperature['value']), 117.0)

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
