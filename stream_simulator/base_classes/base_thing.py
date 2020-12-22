#!/usr/bin/python
# -*- coding: utf-8 -*-

from commlib.logger import Logger
from derp_me.client import DerpMeClient

class BaseThing:
    id = 0
    def __init__(self):
        BaseThing.id += 1
