"""
Test to check the robot teleportation functionality.
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
    Test class for robot teleportation functionality.
    This class contains a unit test that verifies the ability to teleport robots
    within a simulation environment. The test retrieves simulation actors, identifies
    robots, and sends teleportation commands to them.
    Methods:
        setUp(): Prepares the test environment.
        test_get(): Tests the retrieval of simulation actors and the teleportation of robots.
        tearDown(): Cleans up the test environment.
    """
    def setUp(self):
        self.cfact = CommlibFactory(node_name = "Test")
        sim_name = "streamsim.testinguid"
        self.pose = None

        self.teleport_rpc = self.cfact.get_rpc_client(
            rpc_name = f"{sim_name}.robot_1.teleport",
            auto_run = False
        )

        self.cfact.get_subscriber(
            topic = f"{sim_name}.robot_1.pose.internal",
            callback = self.robot_pose_callback,
            auto_run = False
        )

        self.cfact.run()

    def test_get(self):
        """
        Test the retrieval and teleportation of robots in the simulation.
        This test performs the following steps:
        1. Initializes a communication library factory and runs it.
        2. Retrieves the list of simulation actors (robots) using an RPC client.
        3. Iterates through the list of robots and retrieves their connected devices.
        4. Identifies SKID_STEER type devices and teleports them to a specified location.
        If any exception occurs during the process, the test will fail and print the traceback.
        Raises:
            AssertionError: If any exception occurs during the test execution.
        """
        try:
            print("Teleporting robot")
            self.teleport_rpc.call({
                'x': 50.6,
                'y': 49.5,
                'theta': 0.99
            })
            time.sleep(1)

            self.assertIsNotNone(self.pose)
            self.assertAlmostEqual(self.pose['x'], 50.6, places = 1)
            self.assertAlmostEqual(self.pose['y'], 49.5, places = 1)
            self.assertAlmostEqual(self.pose['theta'], 0.99, places = 2)

        except: # pylint: disable=bare-except
            traceback.print_exc(file=sys.stdout)
            self.fail("Test failed due to exception")

    def robot_pose_callback(self, pose):
        """
        Callback function to handle robot pose updates.
        This function is called when a robot's pose is updated.
        Args:
            pose (dict): The updated pose of the robot.
        """
        self.pose = pose

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
