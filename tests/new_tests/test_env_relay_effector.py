#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import sys
import traceback

from stream_simulator.connectivity import CommlibFactory

class Test(unittest.TestCase):
    """
    Unit tests for the relay effector in the streamsim environment.
    This test case includes the following tests:
    - `test_get`: Tests the retrieval and setting of relay states via RPC calls.
    Methods:
    - `setUp`: Prepares the test environment.
    - `test_get`: Retrieves simulation actors, gets connected devices, and tests setting and getting relay states.
    - `tearDown`: Cleans up the test environment.
    Exceptions:
    - Catches and logs any exceptions that occur during the `test_get` method execution and fails the test if an exception is raised.
    """
    def setUp(self):
        """
        Set up the test environment.

        This method is called before each test case is executed. It is used to
        initialize any state or resources required for the tests.
        """

    def test_get(self):
        """
        Test the functionality of getting and setting states for relay devices in a simulated environment.
        This test performs the following steps:
        1. Retrieves the simulation actors.
        2. Gets the connected devices from the world nodes detector.
        3. Iterates through the devices to find relay devices.
        4. For each relay device, sets and gets the state with various values (1, 0, -1, '0', '1').
        5. Prints the state after each set operation to verify the correct behavior.
        If any exception occurs during the process, the test will fail and the exception details will be printed.
        Raises:
            AssertionError: If the test fails due to an exception.
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
                if s["type"] == "RELAY":
                    set_rpc = cfact.getRPCClient(
                        rpc_name = s["base_topic"] + ".set"
                    )
                    get_rpc = cfact.getRPCClient(
                        rpc_name = s["base_topic"] + ".get"
                    )

                    # Set constant
                    print("Setting state 1")
                    set_rpc.call({"state": 1})
                    print("Getting state")
                    print(get_rpc.call({}))

                    print("Setting state 0")
                    set_rpc.call({"state": 0})
                    print("Getting state")
                    print(get_rpc.call({}))

                    print("Setting state -1")
                    set_rpc.call({"state": -1})
                    print("Getting state")
                    print(get_rpc.call({}))

                    print("Setting state '0'")
                    set_rpc.call({"state": '0'})
                    print("Getting state")
                    print(get_rpc.call({}))

                    print("Setting state '1'")
                    set_rpc.call({"state": '1'})
                    print("Getting state")
                    print(get_rpc.call({}))

        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            self.fail(f"Test failed due to exception: {e}")

    def tearDown(self):
        """
        Tears down the test environment after each test method.

        This method is called after each test method to clean up any resources
        or perform any necessary cleanup operations. Currently, it does not
        perform any actions.
        """
        pass

if __name__ == '__main__':
    unittest.main()
