#!/usr/bin/python
# -*- coding: utf-8 -*-

from commlib_py.transports.redis import RPCClient
from commlib_py.transports.redis import ConnectionParameters
conn_params = ConnectionParameters()
conn_params.host = "localhost"
conn_params.port = 6379

import yaml
import pathlib

cl = RPCClient(conn_params=conn_params, rpc_name="/simulator/start")

curr_dir = pathlib.Path().absolute()
filename = str(curr_dir) + "/../configurations/tektrain.yaml"
with open(filename, 'r') as stream:
    try:
        world = yaml.safe_load(stream)
        res = cl.call(data = world)
        print(res)
    except yaml.YAMLError as exc:
        self.logger.critical("World filename does not exist")
