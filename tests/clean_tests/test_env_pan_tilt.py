#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import sys
import traceback

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
                if s["type"] == "PAN_TILT":
                    set_rpc = cfact.getRPCClient(
                        rpc_name = s["base_topic"] + ".set"
                    )
                    sub = cfact.getSubscriber(
                        topic = s["base_topic"] + ".data",
                        callback = self.callback
                    )
                    sub.run()
                    get_rpc = cfact.getRPCClient(
                        rpc_name = s["base_topic"] + ".get"
                    )

                    # Set constant
                    print("Setting 0.2, 0.4")
                    set_rpc.call({
                        'pan': 0.2,
                        'tilt': 0
                    })
                    print("Getting state")
                    print("Res: ", get_rpc.call({}))

                    try:
                        sub.stop()
                    except: # pylint disable=bare-except
                        pass

        except: # pylint disable=bare-except
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)

    def tearDown(self):
        pass

    def callback(self, message):
        print(f"Sub: {message}")

if __name__ == '__main__':
    unittest.main()
