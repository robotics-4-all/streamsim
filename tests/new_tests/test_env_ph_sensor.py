#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import sys
import traceback
import time

from stream_simulator.connectivity import CommlibFactory

class Test(unittest.TestCase):
    """
    Test class for PH sensor environment in a simulation.
    This class contains methods to set up the test environment, execute the test, and tear down the environment after the test.
    Methods
    -------
    setUp():
        Prepares the test environment. Currently, it does nothing.
    test_get():
        Tests the retrieval of PH sensor data from the simulation. It performs the following steps:
        - Retrieves simulation actors.
        - Retrieves connected devices in the simulation world.
        - Subscribes to PH sensor data topics.
        - Sets different modes (constant, triangle, random, normal, sinus) for the PH sensor and waits for 2 seconds between each mode change.
        - Stops the subscription to the PH sensor data topics.
        If any exception occurs during the test, it prints the traceback and fails the test.
    callback(message):
        Callback function to handle messages received from the PH sensor data topic. It prints the received message.
    tearDown():
        Cleans up the test environment. Currently, it does nothing.
    """

    def setUp(self):
        """
        Set up the test environment for the pH sensor tests.
        This method is called before each test case is executed.
        """
        self.cfact = CommlibFactory(node_name = "Test")

    def test_get(self):
        """
        Test the retrieval and interaction with PH_SENSOR devices in a simulated environment.
        This test performs the following steps:
        1. Retrieves the simulation actors.
        2. Gets the list of connected devices in the simulation.
        3. Identifies PH_SENSOR devices and subscribes to their data topics.
        4. Sets different modes (constant, triangle, random, normal, sinus) on the PH_SENSOR devices.
        5. Stops the subscription after setting the modes.
        If any exception occurs during the process, the test will fail and print the traceback.
        Raises:
            AssertionError: If the test fails due to an exception.
        """
        try:
            # Get simulation actors
            sim_name = "streamsim.123"
            cl = self.cfact.getRPCClient(
                rpc_name = f"{sim_name}.get_device_groups"
            )
            res = cl.call({})

            world = res["world"]
            cl = self.cfact.getRPCClient(
                rpc_name = f"streamsim.{world}.nodes_detector.get_connected_devices"
            )
            res = cl.call({})

            # Get ph sensors
            for s in res["devices"]:
                if s["type"] == "PH_SENSOR":
                    sub = self.cfact.getSubscriber(
                        topic = s["base_topic"] + ".data",
                        callback = self.callback
                    )
                    sub.run()
                    time.sleep(5)
                    sub.stop()

        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            self.fail(f"Test failed due to exception: {e}")

    def callback(self, message):
        """
        Callback function to handle incoming messages.

        Args:
            message (str): The message to be processed and printed.
        """
        print(message)

    def tearDown(self):
        """
        Tears down the test environment after each test method.

        This method is called after each test method to clean up any resources
        or perform any necessary cleanup operations. Override this method to
        add custom teardown logic.
        """
        self.cfact.stop()

if __name__ == '__main__':
    unittest.main()
