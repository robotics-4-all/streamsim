#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import sys, traceback
import time
import os

from stream_simulator.connectivity import CommlibFactory

class Test_get_env(unittest.TestCase):
    def setUp(self):
        pass

    def test_get(self):
        try:
            # Get simulation actors
            sim_name = "streamsim"
            cl = CommlibFactory.getRPCClient(
                broker = "redis",
                rpc_name = f"{sim_name}.tf.get_declarations"
            )
            res = cl.call({})
            import pprint
            pprint.pprint(res)

            tf = CommlibFactory.getRPCClient(
                broker = "redis",
                rpc_name = f"{sim_name}.tf.get_tf"
            )
            for d in res['declarations']:
                n = d['name']
                rr = tf.call({"name": n})
                print(f"tf of {n}: {rr}")

        except:
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
