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
                    if s["type"] == "TOUCH_SCREEN":
                        set_rpc = CommlibFactory.getRPCClient(
                            broker = "redis",
                            rpc_name = s["base_topic"] + ".show_image"
                        )

                        # Set constant
                        print("Showing color")
                        ret = set_rpc.call({
                            "image_width": 300,
                            "image_height": 490,
                            "file_flag": False,
                            "source": None,
                            "time_enabled": 5,
                            "touch_enabled": True,
                            "color_rgb": [3, 3, 3],
                            "options": [],
                            "multiple_options": False,
                            "time_window": 3,
                            "text": "",
                            "show_image": False,
                            "show_color": True,
                            "show_video": False,
                            "show_options": False
                        })
                        print(ret)

        except:
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
