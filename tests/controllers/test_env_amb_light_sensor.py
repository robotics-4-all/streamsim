#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import sys, traceback
import time
import os

from stream_simulator.connectivity import CommlibFactory

class Test(unittest.TestCase):
    def setUp(self):
        pass

    def test_get(self):
        try:
            # Get simulation actors
            sim_name = "streamsim"
            cl = CommlibFactory.getRPCClient(
                broker = "redis",
                rpc_name = f"{sim_name}.get_device_groups"
            )
            res = cl.call({})

            world = res["world"]
            cl = CommlibFactory.getRPCClient(
                broker = "redis",
                rpc_name = f"{world}.nodes_detector.get_connected_devices"
            )
            res = cl.call({})

            # Get ph sensors
            for s in res["devices"]:
                if s["type"] == "AMBIENT_LIGHT":
                    sub = CommlibFactory.getSubscriber(
                        broker = "redis",
                        topic = s["base_topic"] + ".data",
                        callback = self.callback
                    )
                    sub.run()

                    mode_rpc = CommlibFactory.getRPCClient(
                        broker = "redis",
                        rpc_name = s["base_topic"] + ".set_mode"
                    )

                    # Set constant
                    print("Setting constant")
                    mode_rpc.call({"mode": "constant"})
                    time.sleep(2)
                    print("Setting triangle")
                    mode_rpc.call({"mode": "triangle"})
                    time.sleep(2)
                    print("Setting random")
                    mode_rpc.call({"mode": "random"})
                    time.sleep(2)
                    print("Setting normal")
                    mode_rpc.call({"mode": "normal"})
                    time.sleep(2)
                    print("Setting sinus")
                    mode_rpc.call({"mode": "sinus"})
                    time.sleep(2)

                    sub.stop()

        except:
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)

    def callback(self, message, meta):
        print(message)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
