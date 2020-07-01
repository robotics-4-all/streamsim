#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import threading

from stream_simulator import RpcServer

done = False

def myfun(msg):
    global done
    done = True
    return {"a": 1}

s = RpcServer(topic = "test", func = myfun)
s.start()
while not done:
    time.sleep(0.1)
s.stop()
