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
            dev = None

            for r in robots:
                cl = CommlibFactory.getRPCClient(
                    broker = "redis",
                    rpc_name = f"robot.{r}.nodes_detector.get_connected_devices"
                )
                res = cl.call({})

                # Get ph sensors
                for s in res["devices"]:
                    if s["type"] == "PAN_TILT" and s['name'] == "pt2":
                        dev = s
                        break

                if dev != None:
                    break

            set_rpc = CommlibFactory.getPublisher(
                topic = dev["base_topic"] + ".set"
            )
            set_motion = CommlibFactory.getPublisher(
                topic = "robot.robot_2.actuator.motion.twist.d_101.d_101.set"
            )

            # yaw = 0
            # for i in range(0, 100):
            #     time.sleep(1)
            #     set_rpc.publish({
            #         'yaw': yaw + i * 0.01,
            #         'pitch': 0
            #     })

            # yaw = 0.78
            # set_rpc.publish({
            #     'yaw': yaw,
            #     'pitch': 0
            # })

            set_motion.publish({
                'linear': 1.0,
                'angular': 0.0,
                'raw': 0
            })
            time.sleep(1)
            set_motion.publish({
                'linear': 0.0,
                'angular': 0.0,
                'raw': 0
            })

        except:
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
