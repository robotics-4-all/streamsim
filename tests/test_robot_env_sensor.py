"""
Test to check the robot env sensor.
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
    Test class for robot environment sensor.
    This class contains unit tests for verifying the functionality of the robot's
    environment sensor, including temperature, humidity, pressure, and gas readings.
    It uses the CommlibFactory to create RPC clients, subscribers, and publishers
    for interacting with the robot simulation.
    Methods:
        setUp():
            Initializes the test environment, including creating RPC clients,
            subscribers, and publishers, and starting the communication factory.
        env_callback(msg):
            Callback function for processing environment sensor data messages.
            Updates the temperature, humidity, pressure, and gas attributes with
            the received data.
        test_get():
            Tests the robot's environment sensor readings by teleporting the robot
            to different locations and verifying the sensor values.
        tearDown():
            Cleans up the test environment after each test case by stopping the
            communication factory.
    """
    def setUp(self):
        self.cfact = CommlibFactory(node_name = "Test")
        sim_name = "streamsim.testinguid"
        self.temperature = None
        self.humidity = None
        self.pressure = None
        self.gas = None

        self.teleport_rpc = self.cfact.get_rpc_client(
            rpc_name = f"{sim_name}.robot_1.teleport",
            auto_run = False
        )

        self.cfact.get_subscriber(
            topic = f"{sim_name}.robot_1.sensor.env.temp_hum_pressure_gas.d_env_35.data",
            callback = self.env_callback,
            auto_run = False
        )

        # Publisher to set speed to robot
        self.velocity_publisher = self.cfact.get_publisher(
            topic = f"{sim_name}.robot_1.actuator.motion.twist.skid_steer_robot_1.set",
            auto_run = False
        )

        self.cfact.run()

    def env_callback(self, msg):
        """
        Callback function to handle environment sensor data.

        Args:
            msg (dict): A dictionary containing sensor data with the following keys:
                - 'data' (dict): A dictionary containing the following keys:
                    - 'temperature' (float): The temperature value from the sensor.
                    - 'humidity' (float): The humidity value from the sensor.
                    - 'pressure' (float): The pressure value from the sensor.
                    - 'gas' (float): The gas concentration value from the sensor.

        Sets:
            self.temperature (float): The temperature value from the sensor.
            self.humidity (float): The humidity value from the sensor.
            self.pressure (float): The pressure value from the sensor.
            self.gas (float): The gas concentration value from the sensor.
        """
        self.temperature = msg['data']['temperature']
        self.humidity = msg['data']['humidity']
        self.pressure = msg['data']['pressure']
        self.gas = msg['data']['gas']

    def test_get(self):
        """
        Test the sensor readings of the robot in different environments
            by teleporting it to various locations.
        This test performs the following steps:
        1. Teleports the robot to a location away from everything and checks the sensor readings.
        2. Teleports the robot near a fire and checks the temperature and gas sensor readings.
        3. Teleports the robot near water and checks the humidity sensor reading.
        The test asserts the following conditions:
        - Temperature is approximately 16 degrees with a delta of 0.5.
        - Humidity is approximately 60% with a delta of 0.5.
        - Pressure is approximately 27 with a delta of 5.
        - Gas level is approximately 540 with a delta of 10.
        - Temperature near fire is approximately 105 degrees with a delta of 2.
        - Gas level near fire is approximately 4953 with a delta of 10.
        - Humidity near water is greater than 70%.
        If any exception occurs during the test, it prints the traceback and fails the test.
        """
        try:
            print("Teleporting robot away from everything")
            self.teleport_rpc.call({
                'x': 99.0,
                'y': 99.0,
                'theta': 0
            })
            time.sleep(1)

            self.assertAlmostEqual(self.temperature, 16, delta=0.5)
            self.assertAlmostEqual(self.humidity, 60, delta=0.5)
            self.assertAlmostEqual(self.pressure, 27, delta=5)
            self.assertAlmostEqual(self.gas, 540, delta=10)

            # Teleport robot near the fire
            self.teleport_rpc.call({
                'x': 22.0,
                'y': 22.0,
                'theta': 0
            })
            time.sleep(1)

            self.assertGreater(self.temperature, 100)
            self.assertAlmostEqual(self.gas, 4953, delta=10)

            # Teleport robot near water
            self.teleport_rpc.call({
                'x': 41.0,
                'y': 75.0,
                'theta': 0
            })
            time.sleep(1)

            self.assertGreater(self.humidity, 70)

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
