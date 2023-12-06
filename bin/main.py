#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import sys
import logging

from stream_simulator import Simulator

logging.basicConfig(format='%(levelname)s : %(name)s : %(message)s', level=logging.DEBUG)

if len(sys.argv) < 2:
    print("You must provide a valid yaml name as argument and if you want the device name. For example:")
    print(">> python3 main.py elsa [device_0]")
    exit(0)

c = sys.argv[1]

# Check if we have device name.
# If yes, it will be assigned to the first device
_device_name = None
if len(sys.argv) == 3:
    _device_name = sys.argv[2]

s = Simulator(conf_file = c, device = _device_name)
s.start()
