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
                if s["type"] == "LIGHTS":
                    set_rpc = CommlibFactory.getRPCClient(
                        rpc_name = s["base_topic"] + ".set"
                    )
                    get_rpc = CommlibFactory.getRPCClient(
                        rpc_name = s["base_topic"] + ".get"
                    )

                    # Set constant
                    print("Setting {1, 1, 1, 1}")
                    set_rpc.call({
                        'r': 1,
                        'g': 1,
                        'b': 1,
                        'a': 1
                    })
                    print("Getting color")
                    print(get_rpc.call({}))

        except:
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
