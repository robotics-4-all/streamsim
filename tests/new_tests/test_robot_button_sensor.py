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

                # Get buttons
                for s in res["devices"]:
                    if s["type"] == "BUTTON":
                        sub = cfact.getSubscriber(
                            topic = s["base_topic"] + ".data",
                            callback = self.callback
                        )
                        print(s["base_topic"] + ".data")
                        sub.run()
                        print("Waiting for button press")
                        time.sleep(1)

                        pub = cfact.getPublisher(
                            topic = f"{sim_name}.{r}.buttons_sim.internal"
                        )
                        pub.publish({
                            "button": s["id"],
                            "state": 1
                        })
                        time.sleep(2)
                        try:
                            sub.stop()
                        except: # pylint: disable=bare-except
                            pass

        except:
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)

    def callback(self, message):
        print(message)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
