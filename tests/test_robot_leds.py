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
        self.ambient_light_value = None

        self.teleport_rpc = self.cfact.get_rpc_client(
            rpc_name = f"{sim_name}.robot_1.teleport",
            auto_run = False
        )

        # RPC for lighting the robot leds
        self.bulb_rpc = self.cfact.get_rpc_client(
            rpc_name = f"{sim_name}.robot_1.actuator.visual.leds.d_leds_37.set",
            auto_run = False
        )

        self.cfact.get_subscriber(
            topic = f"{sim_name}.world.office.sensor.visual.light_sensor.ambient_light_X.data",
            callback = self.ambient_light_callback,
            auto_run = False
        )

        self.cfact.run()

    def ambient_light_callback(self, message):
        """
        Callback function to handle ambient light messages.

        Args:
            message (any): The message containing the ambient light value.
        """
        self.ambient_light_value = message

    def test_get(self):
        """
        Test the ambient light sensor's response to changes in bulb luminosity.
        This test performs the following steps:
        1. Turns off the light by setting the bulb's luminosity to 0.0 and 
            verifies that the ambient light value is approximately 10.0.
        2. Turns on the light by setting the bulb's luminosity to 60.0 and 
            verifies that the ambient light value increases to greater than 20.0.
        The test will fail if any exceptions are raised during execution or if 
            the ambient light values do not meet the expected criteria.
        """
        try:
            print("Turn off light")
            self.bulb_rpc.call({
                'luminosity': 0.0,
                'r': 255,
                'g': 255,
                'b': 255,
            })

            time.sleep(1)
            self.assertIsNotNone(self.ambient_light_value)
            self.assertAlmostEqual(self.ambient_light_value['value'], 10.0, delta = 0.5)

            self.teleport_rpc.call({
                'x': 70.0,
                'y': 70.0,
                'theta': 0
            })
            time.sleep(1)

            print("Turn on light")
            self.bulb_rpc.call({
                'luminosity': 100.0,
                'r': 255,
                'g': 255,
                'b': 255,
            })

            time.sleep(1)
            self.assertGreater(self.ambient_light_value['value'], 20.0)

            print("Turn off light")
            self.bulb_rpc.call({
                'luminosity': 0.0,
                'r': 255,
                'g': 255,
                'b': 255,
            })

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
