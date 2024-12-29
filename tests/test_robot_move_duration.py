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
    This test case verifies the robot's ability to move for a specified duration
    and checks if the final position is within the expected range. The test
    performs the following steps:
    Attributes:
        cfact (CommlibFactory): The communication library factory instance.
        pose (dict): The current pose of the robot.
        teleport_rpc (RPCClient): The RPC client for teleporting the robot.
        move_duration_rpc (RPCClient): The RPC client for moving the robot by duration.
    Methods:
        setUp(): Sets up the test environment and initializes necessary components.
        test_get(): Tests the robot's movement by duration.
        robot_pose_callback(pose): Callback function to handle robot pose updates.
        tearDown(): Cleans up after each test case.
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

        # RPC for moving by duration
        self.move_duration_rpc = self.cfact.getRPCClient(
            rpc_name = f"{sim_name}.robot_1.actuator.motion.twist.skid_steer_robot_1.move.duration",
            auto_run = False
        )

        self.cfact.run()

    def test_get(self):
        """
        Test the robot's movement by duration.
        This test performs the following steps:
        1. Teleports the robot to a specific position (x=500, y=500, theta=0).
        2. Waits for 1 second to ensure the teleportation is complete.
        3. Moves the robot for a specified duration (2 seconds) with a 
            linear speed of 0.5 and no angular speed.
        4. Waits for 1 second to ensure the movement is complete.
        5. Asserts that the robot's x position is approximately 501 with a tolerance of 0.25.
        If any exception occurs during the test, it prints the traceback
            and fails the test with an appropriate message.
        """
        try:
            print("Teleporting robot")
            self.teleport_rpc.call({
                'x': 50.0,
                'y': 50.0,
                'theta': 0
            })
            time.sleep(1)

            print("Moving robot by duration")
            self.move_duration_rpc.call({
                'duration': 2,
                'linear': 0.5,
                'angular': 0
            })
            time.sleep(1)
            self.assertAlmostEqual(self.pose['x'], 51, delta=0.1)

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
