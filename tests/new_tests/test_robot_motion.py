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
            print(res)

            robots = res["robots"]
            for r in robots:
                cl = cfact.getRPCClient(
                    rpc_name = f"{sim_name}.{r}.nodes_detector.get_connected_devices"
                )
                res = cl.call({})

                # Get ph sensors
                for s in res["devices"]:
                    if s["type"] == "SKID_STEER":
                        set_rpc = cfact.getPublisher(
                            topic = s["base_topic"] + ".set"
                        )
                        cmd_duration_rpc = cfact.getRPCClient(
                            rpc_name = s["base_topic"] + ".move.duration"
                        )
                        cmd_distance_rpc = cfact.getRPCClient(
                            rpc_name = s["base_topic"] + ".move.distance"
                        )
                        cmd_turn_rpc = cfact.getRPCClient(
                            rpc_name = s["base_topic"] + ".move.turn"
                        )

                        # Set constant
                        print("Setting 0.1, 0")
                        set_rpc.publish({
                            'linear': 0.1,
                            'angular': 0,
                            'raw': 0
                        })

                        time.sleep(2)
                        print("Stopping")
                        set_rpc.publish({
                            'linear': 0,
                            'angular': 0,
                            'raw': 0
                        })
                        time.sleep(2)
                        print("Go with duration")
                        
                        cmd_duration_rpc.call({
                            'linear': 0.5,
                            'angular': 0,
                            'duration': 2
                        })
                        time.sleep(1)
                        print("Go with distance")
                        cmd_distance_rpc.call({
                            'linear': 0.1,
                            'distance': 1
                        })
                        time.sleep(1)
                        print("Turn")
                        cmd_turn_rpc.call({
                            'angular': 0.1,
                            'angle': 1.57
                        })
                        time.sleep(1)

        except: # pylint: disable=bare-except
            traceback.print_exc(file=sys.stdout)
            self.fail("Test failed due to exception")

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
