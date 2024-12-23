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
            sim_name = "streamsim.123"
            cfact = CommlibFactory(node_name = "Test")
            cfact.run()
            cl = cfact.getRPCClient(
                rpc_name = f"{sim_name}.get_device_groups"
            )
            res = cl.call({})

            robots = res["robots"]
            for r in robots:
                cl = cfact.getRPCClient(
                    rpc_name = f"{sim_name}.{r}.nodes_detector.get_connected_devices"
                )
                res = cl.call({})

                # Get ph sensors
                for s in res["devices"]:
                    if s["type"] == "SPEAKERS":
                        # Speak
                        action = cfact.getActionClient(
                            action_name = s["base_topic"] + ".speak"
                        )
                        resp = action.send_goal({
                            'text': 'This is an example',
                            'volume': 100,
                            'language': 'el'
                        })
                        while action.get_result() is None:
                            print(action.get_result())
                            time.sleep(0.1)
                        final_res = action.get_result()
                        print(final_res)

                        # Play
                        action = cfact.getActionClient(
                            action_name = s["base_topic"] + ".play"
                        )
                        resp = action.send_goal({
                            'string': '...',
                            'volume': 100
                        })
                        while action.get_result() == None:
                            time.sleep(0.1)
                        final_res = action.get_result()
                        print(final_res)

        except:
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
