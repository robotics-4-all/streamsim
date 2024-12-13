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

                for s in res["devices"]:
                    if s["type"] == "MICROPHONE":
                        # Speak
                        action = cfact.getActionClient(
                            action_name = s["base_topic"] + ".record"
                        )
                        action.send_goal({
                            'duration': 2
                        })
                        while action.get_result() is None:
                            time.sleep(0.1)
                        final_res = action.get_result()
                        print(f"Bytes of recording: {len(final_res['record'])}")
        except: # pylint: disable=bare-except
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
