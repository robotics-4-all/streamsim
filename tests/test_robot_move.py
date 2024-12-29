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
    Test class for robot movement and pose updates.
    This class contains unit tests for verifying the robot's movement and pose
    after teleportation and setting velocity. It uses the unittest framework
    and includes setup, test, and teardown methods.
    Methods:
        setUp(): Initializes the test environment, including creating necessary
            communication clients and subscribers.
        test_get(): Tests the robot's movement and pose after teleportation and
            setting velocity. It performs the following steps:
        robot_pose_callback(pose): Callback function to handle robot pose updates.
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

        # Publisher to set speed to robot
        self.velocity_publisher = self.cfact.getPublisher(
            topic = f"{sim_name}.robot_1.actuator.motion.twist.skid_steer_robot_1.set",
            auto_run = False
        )

        self.cfact.run()

    def test_get(self):
        """
        Test the robot's movement and pose after teleportation and setting velocity.
        This test performs the following steps:
        1. Teleports the robot to the coordinates (500, 500) with an 
            orientation (theta) of 0.
        2. Sets the robot's linear velocity to 0.2 and angular velocity to 0.
        3. Asserts that the robot's orientation (theta) remains approximately 0.
        4. Asserts that the robot's x-coordinate is approximately 500.6.
        5. Asserts that the robot's y-coordinate remains approximately 500.
        If any exception occurs during the test, it prints the traceback and 
            fails the test.
        """
        try:
            print("Teleporting robot")
            self.teleport_rpc.call({
                'x': 50.0,
                'y': 50.0,
                'theta': 0
            })
            time.sleep(1)

            print("Setting speed to robot")
            self.velocity_publisher.publish({
                'linear': 0.2,
                'angular': 0
            })
            time.sleep(3)

            self.assertAlmostEqual(self.pose['theta'], 0, delta=0.1)
            self.assertAlmostEqual(self.pose['x'], 50.6, delta=0.1)
            self.assertAlmostEqual(self.pose['y'], 50, delta=0.1)

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
