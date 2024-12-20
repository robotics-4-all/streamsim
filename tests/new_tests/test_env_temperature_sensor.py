#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import sys
import traceback
import time

from stream_simulator.connectivity import CommlibFactory

class Test(unittest.TestCase):
    """
    Unit test for environment temperature sensor.
    This test case is designed to test the functionality of the environment temperature sensor
    in a simulated environment. It uses the CommlibFactory to create RPC clients and subscribers
    to interact with the simulation and sensor devices.
    Methods:
        setUp():
            Set up the test environment. Currently, it does nothing.
        test_get():
            Test the retrieval and mode setting of temperature sensors in the simulation.
            It performs the following steps:
            - Retrieves the simulation actors.
            - Retrieves the connected devices in the simulation.
            - For each temperature sensor device, subscribes to its data topic and sets various modes.
            - Modes tested: constant, triangle, random, normal, sinus.
            - Stops the subscriber after testing all modes.
            If any exception occurs during the test, it prints the traceback and fails the test.
        callback(message):
            Callback function to handle messages received from the sensor's data topic.
            It simply prints the received message.
        tearDown():
            Clean up the test environment. Currently, it does nothing.
    """

    def setUp(self):
        """
        Set up the test environment for the temperature sensor tests.
        This method is called before each test case is executed.
        """

    def test_get(self):
        """
        Test the retrieval and mode setting of temperature sensors in a simulated environment.
        This test performs the following steps:
        1. Retrieves the simulation actors.
        2. Gets the list of connected devices from the world node detector.
        3. Iterates through the devices to find temperature sensors.
        4. Subscribes to the temperature sensor data topic.
        5. Sets different modes (constant, triangle, random, normal, sinus) on the temperature sensor with delays in between.
        6. Stops the subscription to the temperature sensor data topic.
        If any exception occurs during the process, the test will fail and the exception traceback will be printed.
        Raises:
            AssertionError: If any exception occurs during the test execution.
        """
        try:
            # Get simulation actors
            sim_name = "streamsim.123"
            cfact = CommlibFactory(node_name = "Test")
            cfact.run()
            cl = cfact.getRPCClient(
                rpc_name = f"{sim_name}.get_device_groups"
            )
            res = cl.call({})

            world = res["world"]
            cl = cfact.getRPCClient(
                rpc_name = f"streamsim.{world}.nodes_detector.get_connected_devices"
            )
            res = cl.call({})

            # Get ph sensors
            for s in res["devices"]:
                if s["type"] == "TEMPERATURE":
                    sub = cfact.getSubscriber(
                        topic = s["base_topic"] + ".data",
                        callback = self.callback
                    )
                    sub.run()
                    time.sleep(5)
                    try:
                        sub.stop()
                    except Exception:
                        pass

        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            self.fail(f"Test failed due to exception: {e}")

    def callback(self, message):
        """
        Callback function to handle incoming messages.

        Args:
            message (str): The message received that needs to be processed.
        """
        print(message)

    def tearDown(self):
        """
        Tears down the test environment after each test method.

        This method is called after each test method to clean up any resources
        or perform any necessary cleanup operations. Override this method to
        add custom teardown logic.
        """

if __name__ == '__main__':
    unittest.main()
