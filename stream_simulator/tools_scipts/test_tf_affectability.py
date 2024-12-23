"""
File that contains the test for the tf affectability.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import pprint

from stream_simulator.connectivity import CommlibFactory

# Get simulation actors
sim_name = f"streamsim.{sys.argv[2]}"
cmlib = CommlibFactory(node_name="Test")
cl = cmlib.getRPCClient(
    rpc_name = f"{sim_name}.tf.get_affections",
    broker = sys.argv[3]
)
pprint.pprint(cl.call({
    'name': sys.argv[1]
}))
