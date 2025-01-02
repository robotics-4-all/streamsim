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
    Test class for robot sonar functionality.
    This class contains unit tests for verifying the behavior of a robot's sonar sensor.
    It uses the unittest framework to define test cases, set up the necessary environment,
    and clean up after each test.
    Methods:
        setUp(): Initializes the test environment, including creating a communication
                 factory, setting up RPC clients and subscribers, and running the factory.
        test_get(): Tests the robot's teleportation and sonar distance measurement by
                    teleporting the robot to different positions and verifying the
                    measured distances.
        sonar_callback(measure): Callback function to handle sonar measurements and
                                 store the measurement data.
        tearDown(): Cleans up the test environment after each test case by stopping
                    the communication factory.
    """
    def setUp(self):
        self.cfact = CommlibFactory(node_name = "Test")
        sim_name = "streamsim.testinguid"
        self.measurement = None

        self.teleport_rpc = self.cfact.get_rpc_client(
            rpc_name = f"{sim_name}.robot_1.teleport",
            auto_run = False
        )

        self.cfact.get_subscriber(
            topic = f"{sim_name}.robot_1.sensor.distance.sonar.sonar_front_on_pt1.data",
            callback = self.sonar_callback,
            auto_run = False
        )

        self.cfact.run()

    def test_get(self):
        """
        Test the robot's sonar distance measurement by teleporting the robot to different positions.
        This test performs the following steps:
        1. Teleports the robot to coordinates (50.0, 50.0) with a theta of 0.
        2. Waits for 1 second to allow the robot to stabilize.
        3. Asserts that the measured distance is approximately 10.0 units with a 
            tolerance of 0.05 units.
        4. Teleports the robot to coordinates (85.0, 50.0) near a wall with a theta of 0.
        5. Waits for 1 second to allow the robot to stabilize.
        6. Asserts that the measured distance is approximately 5.0 units with a tolerance 
            of 0.05 units.
        If any exception occurs during the test, it prints the traceback and fails the test 
            with an appropriate message.
        """
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
