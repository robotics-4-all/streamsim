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

                print("found devices in robot")

                # Get ph sensors
                for s in res["devices"]:
                    if s["type"] == "SKID_STEER":
                        set_action = CommlibFactory.getActionClient(
                            broker = "redis",
                            action_name = s["base_topic"] + ".set"
                        )
                        
                        # Set constant
                        resp = set_action.send_goal({
                            'linearVelocity': 0.1,
                            'rotationalVelocity': 0.0,
                            'duration': 3
                        })

                        goal_id_play = resp["goal_id"]
                        # logger.info("GOAL ID:", self.goal_id_play)

                        while set_action.get_result(goal_id_play)["status"] == 1:
                            time.sleep(0.1)
                        
                        final_res = set_action.get_result(goal_id_play)

                        time.sleep(3)

        except:
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
