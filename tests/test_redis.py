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
    Test class for testing the Redis publisher and subscriber functionality.
    This class contains setup, teardown, and test methods to verify the
    communication between a publisher and a subscriber using the CommlibFactory.
    Methods:
        setUp():
            Initializes the CommlibFactory, publisher, and subscriber instances.
            Sets up the necessary configurations for the test.
        callback(_):
            Sets the `ok` attribute to True when a message is received.
        test_get():
            Tests the `get` method by publishing a message and verifying that
            the subscriber receives it. Asserts that the `ok` attribute is True.
        tearDown():
            Cleans up resources and stops the CommlibFactory after each test case.
    """
    def setUp(self):
        self.cfact = CommlibFactory(node_name = "Test")
        sim_name = "streamsim.testinguid"
        self.ok = False

        self.pub = self.cfact.get_publisher(
            topic = f"{sim_name}.redis",
            auto_run = False
        )

        self.sub = self.cfact.get_subscriber(
            topic = f"{sim_name}.redis",
            callback=self.callback,
            auto_run = False
        )

        self.cfact.run()

    def callback(self, _):
        """
        Callback function to handle incoming messages.

        Returns:
            None
        """
        self.ok = True

    def test_get(self):
        """
        Test the `get` method.
        This test verifies that the addition of 0 and 1 equals 1. If an exception occurs,
        it will print the traceback and fail the test with a message indicating that the
        test failed due to an exception.
        """
        try:
            time.sleep(0.5) # to ensure that the subscriber is ready
            self.pub.publish({"msg":"test"})
            time.sleep(0.5)
            self.assertTrue(self.ok)

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
