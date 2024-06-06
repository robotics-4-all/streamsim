#!/usr/bin/python
# -*- coding: utf-8 -*-

from stream_simulator.connectivity import CommlibFactory

class BaseThing:
    id = 0
    def __init__(self, _name):
        BaseThing.id += 1

        self.commlib_factory = CommlibFactory(node_name = _name)
        self.commlib_factory.run()
