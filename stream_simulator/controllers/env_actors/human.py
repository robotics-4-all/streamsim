#!/usr/bin/python
# -*- coding: utf-8 -*-

from stream_simulator.base_classes import BaseController

class HumanActor(BaseController):
    def __init__(self, name = None, logger = None, derp = None):
        super(Human, self).__init__(name = name, logger = logger, derp = derp)
