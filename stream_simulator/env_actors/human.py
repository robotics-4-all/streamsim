#!/usr/bin/python
# -*- coding: utf-8 -*-

from commlib.logger import Logger
from derp_me.client import DerpMeClient

from stream_simulator.connectivity import ConnParams
from stream_simulator.base_classes import BaseController

class Human(BaseController):
    def __init__(self, name = None, logger = None, derp = None):
        super(Human, self).__init__(name = name, logger = logger, derp = derp)
