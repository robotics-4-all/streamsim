"""
Test to check the env gas sensor
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
    Test class for testing the gas sensor environment.
    This class contains methods to set up the test environment, 
        run the test, and clean up after the test.
    It uses the unittest framework to perform the tests.
    Methods
    -------
    setUp():
        Sets up the test environment by initializing the CommlibFactory 
            and subscribing to the gas sensor topic.
    test_get():
        Tests if the gas sensor measurement value is greater than 1000.0. 
            If an exception occurs, it prints the traceback and fails the test.
    gas_callback(measure):
        Callback function to handle the gas sensor measurement data.
    tearDown():
        Cleans up after each test case by stopping the CommlibFactory.
    """
    def setUp(self):
        self.cfact = CommlibFactory(node_name = "Test")
        sim_name = "streamsim.testinguid"
        self.measurement = None

        self.cfact.get_subscriber(
            topic = f"{sim_name}.world.office.sensor.env.gas.gas_X.data",
            callback = self.gas_callback,
            auto_run = False
        )

        self.cfact.run()

    def test_get(self):
        """
        Test the 'get' method.
        This test checks if the 'value' in the measurement dictionary is greater 
            than 1000.0.
        It waits for 1.5 seconds before performing the check.
        If an exception occurs during the test, it prints the traceback to 
            stdout and fails the test with a message.
        """
        try:
            time.sleep(1.5)

            self.assertGreater(self.measurement['value'], 1000.0)

        except: # pylint: disable=bare-except
            traceback.print_exc(file=sys.stdout)
            self.fail("Test failed due to exception")

    def gas_callback(self, measure):
        """
        Callback function to handle gas measurement updates.

        Args:
            measure (float): The gas measurement value to be updated.
        """
        self.measurement = measure

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
