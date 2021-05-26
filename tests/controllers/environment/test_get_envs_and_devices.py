#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import sys, traceback
import time
import os

from stream_simulator.connectivity import CommlibFactory

class Test_get_env(unittest.TestCase):
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
            import pprint
            pprint.pprint(res)

            robots = res["robots"]
            world = res["world"]
            for r in robots:
                cl = CommlibFactory.getRPCClient(
                    broker = "redis",
                    rpc_name = f"robot.{r}.nodes_detector.get_connected_devices"
                )
                res = cl.call({})
                import pprint
                pprint.pprint(res)

            cl = CommlibFactory.getRPCClient(
                broker = "redis",
                rpc_name = f"{world}.nodes_detector.get_connected_devices"
            )
            res = cl.call({})
            import pprint
            pprint.pprint(res)

            # Get robots
        except:
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
