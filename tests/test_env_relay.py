"""
Test to check the environmental relay
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
    Test class for testing the relay RPC functionality.
    This class contains setup, test, and teardown methods for testing
    the relay RPC functionality using the CommlibFactory. It includes
    methods to set up the test environment, perform the test, and clean
    up after the test.
    Methods:
        setUp(): Initializes the test environment by creating RPC clients
                 for setting and getting relay states and running the factory.
        test_get(): Tests the relay get RPC call to ensure the relay state
                    can be retrieved and set correctly.
        tearDown(): Cleans up the test environment by stopping the factory.
    """
    def setUp(self):
        self.cfact = CommlibFactory(node_name = "Test")
        sim_name = "streamsim.testinguid"

        self.relay_set_rpc = self.cfact.get_rpc_client(
            rpc_name = f"{sim_name}.world.office.actuator.switch.relay.relay_X.set",
            auto_run = False
        )

        self.relay_get_rpc = self.cfact.get_rpc_client(
            rpc_name = f"{sim_name}.world.office.actuator.switch.relay.relay_X.get",
            auto_run = False
        )

        self.cfact.run()

    def test_get(self):
        """
        Test the `get` method of the relay RPC.
        This test performs the following steps:
        1. Calls the `relay_get_rpc` method with an empty dictionary and 
            asserts that the returned state is 0.
        2. Calls the `relay_set_rpc` method to set the state to 1.
        3. Waits for 0.5 seconds to allow the state change to take effect.
        If any exception occurs during the test, it prints the traceback and
            fails the test with an appropriate message.
        """

        try:
            self.relay_set_rpc.call({'state': 0})
            time.sleep(0.5)
            res = self.relay_get_rpc.call({})
            self.assertEqual(res['state'], 0)

            self.relay_set_rpc.call({'state': 1})
            time.sleep(0.5)
            res = self.relay_get_rpc.call({})
            self.assertEqual(res['state'], 1)

            self.relay_set_rpc.call({'state': 0})

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
