#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys

from commlib_py.transports.amqp import RPCClient
from commlib_py.transports.amqp import ConnectionParameters
conn_params = ConnectionParameters()
conn_params.credentials.username = 'bot'
conn_params.credentials.password = 'b0t'
conn_params.host = 'tektrain-cloud.ddns.net'
conn_params.port = 5672
conn_params.vhost = "sim"

cl = RPCClient(conn_params=conn_params, rpc_name="simulator.stop")

res = cl.call({"device": sys.argv[1]})
print(res)
