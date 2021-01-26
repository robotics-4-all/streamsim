#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import sys, traceback
import time
import os

from stream_simulator.connectivity import CommlibFactory

try:
    # Get simulation actors
    sim_name = "streamsim"
    cl = CommlibFactory.getRPCClient(
        broker = "redis",
        rpc_name = f"{sim_name}.tf.simulated_detection"
    )
    print(cl.call({
        'name': sys.argv[1],
        'type': sys.argv[2]
    }))

except:
    traceback.print_exc(file=sys.stdout)
    self.assertTrue(False)
