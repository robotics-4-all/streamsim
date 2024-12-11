#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import sys
import traceback

from stream_simulator.connectivity import CommlibFactory

class Test(unittest.TestCase):
    """
    Unit test for thermostat environment in the streamsim simulation.
    This test case includes the following methods:
    - setUp: Prepares the test environment.
    - test_get: Tests the retrieval and setting of thermostat devices in the simulation.
    - tearDown: Cleans up the test environment after each test.
    Methods:
        setUp():
            Prepares the test environment. Currently, it does nothing.
        test_get():
            Retrieves simulation actors and connected devices. For each thermostat device found, it sets the temperature to 22 and retrieves the current temperature. If any exception occurs, the test fails and the exception is printed.
        tearDown():
            Cleans up the test environment. Currently, it does nothing.
    """
    def setUp(self):
        """
        Set up the test environment for each test case.

        This method is called before each test case is executed to prepare the necessary
        environment and resources. Override this method to add any specific setup steps
        required for the tests.
        """

    def test_get(self):
        """
        Test the retrieval and setting of thermostat devices in a simulated environment.
        This test performs the following steps:
        1. Initializes a communication factory and retrieves a list of device groups.
        2. Retrieves a list of connected devices from the world node.
        3. Iterates through the devices to find thermostats.
        4. For each thermostat, sets the temperature to a constant value (22) and retrieves the current temperature.
        If any exception occurs during the process, the test will fail and print the traceback.
        Raises:
            AssertionError: If an exception occurs during the test execution.
        """
        try:
            # Get simulation actors
            sim_name = "streamsim.123"
            cfact = CommlibFactory(node_name = "Test")
            cl = cfact.getRPCClient(
                rpc_name = f"{sim_name}.get_device_groups"
            )
            res = cl.call({})

            world = res["world"]
            cl = cfact.getRPCClient(
                rpc_name = f"streamsim.{world}.nodes_detector.get_connected_devices"
            )
            res = cl.call({})

            # Get ph sensors
            for s in res["devices"]:
                if s["type"] == "THERMOSTAT":
                    set_rpc = cfact.getRPCClient(
                        rpc_name = s["base_topic"] + ".set"
                    )
                    get_rpc = cfact.getRPCClient(
                        rpc_name = s["base_topic"] + ".get"
                    )

                    # Set constant
                    print("Setting 50")
                    set_rpc.call({
                        'temperature': 50
                    })
                    print("Getting temperature")
                    print(get_rpc.call({}))
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            self.fail(f"Test failed due to exception: {e}")

    def tearDown(self):
        """
        Tears down the test environment after each test method has been run.
        This method is called after each test method to clean up any resources
        or reset any state that was modified during the test.
        """

if __name__ == '__main__':
    unittest.main()
