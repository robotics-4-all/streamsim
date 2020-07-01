#!/usr/bin/python
# -*- coding: utf-8 -*-

import time

from stream_simulator import Publisher
from stream_simulator import Subscriber


p = Publisher("topic")
s = Subscriber("topic")

for i in range(0, 10):
    p.publish(i)
    time.sleep(1)

s.thread.stop()
