#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import sys
import traceback
import time

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

            world = res["world"]
            cl = cfact.getRPCClient(
                rpc_name = f"streamsim.{world}.nodes_detector.get_connected_devices"
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
                        time.sleep(0.1)
                    final_res = action.get_result()
                    print("Speak result: ", final_res)

                    # Play
                    action = cfact.getActionClient(
                        action_name = s["base_topic"] + ".play"
                    )
                    resp = action.send_goal({
                        'string': '...',
                        'volume': 100
                    })
                    while action.get_result() is None:
                        time.sleep(0.1)
                    final_res = action.get_result()
                    print("Play result: ", final_res)

        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            self.fail(f"Test failed due to exception: {e}")

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
