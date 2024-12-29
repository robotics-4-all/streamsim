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
    Test class for verifying the robot's movement by a specified distance.
    This class contains methods to set up the test environment, perform the test,
    handle robot pose updates, and clean up after each test case.
    Methods:
        setUp(): Initializes the test environment, including creating RPC clients
            and subscribers, and running the communication factory.
        test_get(): Tests the robot's movement by a specified distance. Teleports
            the robot to a starting position, moves it by a specified distance, and
            asserts the new position.
        robot_pose_callback(pose): Callback function to handle robot pose updates.
            Updates the robot's pose when called.
        tearDown(): Cleans up after each test case by stopping the communication
            factory.
    """
    def setUp(self):
        self.cfact = CommlibFactory(node_name = "Test")
        sim_name = "streamsim.testinguid"
        self.pose = None

        self.teleport_rpc = self.cfact.getRPCClient(
            rpc_name = f"{sim_name}.robot_1.teleport",
            auto_run = False
        )

        self.cfact.getSubscriber(
            topic = f"{sim_name}.robot_1.pose.internal",
            callback = self.robot_pose_callback,
            auto_run = False
        )

        # RPC for moving by distance
        self.move_distance_rpc = self.cfact.getRPCClient(
            rpc_name = f"{sim_name}.robot_1.actuator.motion.twist.skid_steer_robot_1.move.distance",
            auto_run = False
        )

        self.cfact.run()

    def test_get(self):
        """
        Test the robot's movement by a specified distance.
        This test performs the following steps:
        1. Teleports the robot to a specific starting position (x=500, y=500, theta=0).
        2. Moves the robot by a specified distance (1 unit) with a linear speed of 0.25.
        3. Asserts that the robot's new x position is approximately 501, within 
            a delta of 0.25.
        If any exception occurs during the test, it prints the traceback and 
            fails the test with an appropriate message.
        """
        try:
            print("Moving robot by distance")
            self.teleport_rpc.call({
                'x': 50.0,
                'y': 50.0,
                'theta': 0
            })

            self.move_distance_rpc.call({
                'distance': 1,
                'linear': 0.25,
            })
            time.sleep(1)

            self.assertAlmostEqual(self.pose['x'], 51.0, delta=0.1)

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
