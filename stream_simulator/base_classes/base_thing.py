#!/usr/bin/python
# -*- coding: utf-8 -*-

from commlib.logger import Logger
from derp_me.client import DerpMeClient

from stream_simulator.connectivity import ConnParams

class BaseController:
    def __init__(self, name = None, logger = None, derp = None):
        if logger is None:
            if name is None:
                raise Exception("Both name and logger is none")
            self.logger = Logger(info["name"])
        else:
            self.logger = logger

        self.name = name

        if derp is None:
            self.derp_client = DerpMeClient(conn_params=ConnParams.get("redis"))
            self.logger.warning(f"New derp-me client from {info['name']}")
        else:
            self.derp_client = derp

        self.local_params = ConnParams.get("redis")
        self.remote_params = ConnParams.get("amqp")
