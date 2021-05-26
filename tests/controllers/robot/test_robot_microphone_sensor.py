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

                for s in res["devices"]:
                    if s["type"] == "MICROPHONE":
                        # Speak
                        action = CommlibFactory.getActionClient(
                            broker = "redis",
                            action_name = s["base_topic"] + ".record"
                        )
                        resp = action.send_goal({
                            'duration': 2
                        })
                        goal_id = resp["goal_id"]
                        while action.get_result(goal_id)["status"] == 1:
                            time.sleep(0.1)
                        final_res = action.get_result(goal_id)
                        print(f"Bytes of recording: {len(final_res['result']['record'])}")
        except:
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
