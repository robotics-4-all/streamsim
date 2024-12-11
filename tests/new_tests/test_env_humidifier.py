#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import sys
import traceback

from stream_simulator.connectivity import CommlibFactory

class Test(unittest.TestCase):
    """
    Unit test for the humidifier environment in the streamsim simulation.
    This test case includes the following methods:
    - setUp: Prepares the test environment.
    - test_get: Tests the retrieval and setting of humidity values for HUMIDIFIER devices.
    - tearDown: Cleans up the test environment.
    Methods:
        setUp():
            Prepares the test environment. Currently does nothing.
        test_get():
            Retrieves simulation actors and connected devices, specifically targeting HUMIDIFIER devices.
            Sets the humidity to a constant value (70) and retrieves the humidity value to verify the operation.
            If any exception occurs, the test fails and the exception traceback is printed.
        tearDown():
            Cleans up the test environment. Currently does nothing.
    """
    def setUp(self):
        """
        Set up the test environment for each test case.

        This method is called before each test case is executed. It can be used to
        initialize variables, create mock objects, or perform any other setup tasks
        required for the tests.
        """
        pass

    def test_get(self):
        """
        Test the retrieval and setting of humidity for HUMIDIFIER devices in the simulation.
        This test performs the following steps:
        1. Retrieves the simulation actors using the simulation name.
        2. Gets the world information from the simulation response.
        3. Retrieves the connected devices in the world.
        4. Iterates through the devices to find HUMIDIFIER devices.
        5. For each HUMIDIFIER device, sets the humidity to 70 and retrieves the current humidity.
        If any exception occurs during the process, the test will fail and print the traceback.
        Raises:
            AssertionError: If any exception occurs during the test execution.
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
                if s["type"] == "HUMIDIFIER":
                    set_rpc = cfact.getRPCClient(
                        rpc_name = s["base_topic"] + ".set"
                    )
                    get_rpc = cfact.getRPCClient(
                        rpc_name = s["base_topic"] + ".get"
                    )

                    # Set constant
                    print("Setting 70")
                    set_rpc.call({
                        'humidity': 30
                    })
                    print("Getting humidity")
                    print(get_rpc.call({}))

        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            self.fail(f"Test failed due to exception: {e}")

    def tearDown(self):
        """
        Tears down the test environment after each test method has been run.
        This method is called after each test method to clean up any resources
        or state that were set up for the test.
        """
        pass

if __name__ == '__main__':
    unittest.main()
