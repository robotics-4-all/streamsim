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

            robots = res["robots"]
            for r in robots:
                cl = CommlibFactory.getRPCClient(
                    broker = "redis",
                    rpc_name = f"robot.{r}.nodes_detector.get_connected_devices"
                )
                res = cl.call({})

                # Get ph sensors
                for s in res["devices"]:
                    if s["type"] == "LED":
                        set_rpc = CommlibFactory.getPublisher(
                            broker = "redis",
                            topic = s["base_topic"] + ".set"
                        )
                        wipe_rpc = CommlibFactory.getRPCClient(
                            broker = "redis",
                            rpc_name = s["base_topic"] + ".wipe"
                        )

                        # Set constant
                        print("Showing color")
                        set_rpc.publish({
                            "id": 0,
                            "r": 0,
                            "g": 30,
                            "b": 10,
                            "luminosity": 100
                        })

                        print("Wiping")
                        ret = wipe_rpc.call({
                            "r": 0,
                            "g": 30,
                            "b": 10,
                            "luminosity": 100,
                            "wait_ms": 4
                        })
                        print(ret)

        except:
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
