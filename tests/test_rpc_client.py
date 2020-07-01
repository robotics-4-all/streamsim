#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import threading

from stream_simulator import RpcClient

s = RpcClient(topic = "test")
res = s.call({"req": 10})
print(res)
