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
                    if s["type"] == "SERVO":
                        set_rpc = CommlibFactory.getPublisher(
                            broker = "redis",
                            topic = s["base_topic"] + ".set"
                        )

                        # Set constant
                        for i in range(0, 180, 1):
                            set_rpc.publish({
                                'angle': i
                            })
                            time.sleep(0.05)

                        for i in range(180, 0, -1):
                            set_rpc.publish({
                                'angle': i
                            })
                            time.sleep(0.05)

                        time.sleep(1)

        except:
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
