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
    Test class for robot movement by angle.
    This class contains unit tests for verifying the robot's movement by a specified angle.
    It uses the CommlibFactory to create RPC clients and subscribers for interacting with the robot.
    Methods:
        setUp():
            Initializes the test environment, including creating RPC clients and subscribers.
        test_get():
            Tests the robot's movement by angle. Teleports the robot to a specified position,
            moves it by a specified angle, and asserts that the robot's orientation is as expected.
        robot_pose_callback(pose):
            Callback function to handle robot pose updates. Updates the internal pose state.
        tearDown():
            Cleans up after each test case by stopping the CommlibFactory.
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

        # RPC for moving by angle
        self.move_angle_rpc = self.cfact.get_rpc_client(
            rpc_name = f"{sim_name}.robot_1.actuator.motion.twist.skid_steer_robot_1.move.turn",
            auto_run = False
        )

        self.cfact.run()

    def test_get(self):
        """
        Test the robot's movement by angle.
        This test performs the following steps:
        1. Teleports the robot to a specified position (x=500, y=500) with an orientation (theta=0).
        2. Waits for 1 second to ensure the teleportation is complete.
        3. Moves the robot by a specified angle (angle=0.3) with a given angular velocity 
            (angular=0.1).
        4. Asserts that the robot's orientation (theta) is approximately 0.3 with a 
            tolerance of 0.05.
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

            print("Moving robot by angle")
            self.move_angle_rpc.call({
                'angle': 0.3,
                'angular': 0.1
            })

            time.sleep(1)

            self.assertAlmostEqual(self.pose['theta'], 0.3, delta=0.05)

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
