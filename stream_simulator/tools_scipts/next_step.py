"""
File that publishes to a topic.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import time

from stream_simulator.connectivity import CommlibFactory

cmlib = CommlibFactory(node_name="Test")

cl = cmlib.getPublisher(
    topic=f"{sys.argv[1]}.step_by_step",
    broker='mqtt'
)

cl.publish("")
print(f"Published to {sys.argv[1]}.step_by_step")
time.sleep(1)
