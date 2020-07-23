#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import sys

from stream_simulator import Simulator

if len(sys.argv) != 2:
    print("You must provide a valid yaml name as argument. For example:")
    print(">> python3 main.py elsa")
    exit(0)

c = sys.argv[1]

s = Simulator(configuration = c)
s.start()
