#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys

from commlib_py.transports.redis import RPCClient
from commlib_py.transports.redis import ConnectionParameters
conn_params = ConnectionParameters()
conn_params.host = "localhost"
conn_params.port = 6379

cl = RPCClient(conn_params=conn_params, rpc_name="/simulator/stop")

res = cl.call(data = {"device": sys.argv[1]})
print(res)
