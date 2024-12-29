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

    def setUp(self):
        self.cfact = CommlibFactory(node_name = "Test")
        sim_name = "streamsim.testinguid"
        self.measurement = None

        self.teleport_rpc = self.cfact.getRPCClient(
            rpc_name = f"{sim_name}.robot_1.teleport",
            auto_run = False
        )

        self.cfact.getSubscriber(
            topic = f"{sim_name}.robot_1.sensor.distance.sonar.sonar_front_on_pt1.data",
            callback = self.sonar_callback,
            auto_run = False
        )

        self.cfact.run()

    def test_get(self):

        try:
            print("Teleporting robot")
            self.teleport_rpc.call({
                'x': 50.0,
                'y': 50.0,
                'theta': 0
            })
            time.sleep(1)

            # Check for max distance
            self.assertAlmostEqual(self.measurement['distance'], 10.0, delta=0.05)

            print("Teleporting robot near the wall")
            self.teleport_rpc.call({
                'x': 85.0,
                'y': 50.0,
                'theta': 0
            })
            time.sleep(1)

            # Check for max distance
            self.assertAlmostEqual(self.measurement['distance'], 5.0, delta=0.05)

        except: # pylint: disable=bare-except
            traceback.print_exc(file=sys.stdout)
            self.fail("Test failed due to exception")

    def sonar_callback(self, measure):
        """
        Callback function to handle sonar measurements.

        Args:
            measure: The measurement data from the sonar sensor.
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
