#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys

from commlib.transports.amqp import RPCClient
from commlib.transports.amqp import ConnectionParameters
conn_params = ConnectionParameters()
conn_params.credentials.username = 'bot'
conn_params.credentials.password = 'b0t'
conn_params.host = 'tektrain-cloud.ddns.net'
conn_params.port = 5672
conn_params.vhost = "sim"

cl = RPCClient(conn_params=conn_params, rpc_name="thing.simbot.deploy_manager.stop_sim")

res = cl.call({"sim_id": sys.argv[1]})
print(res)
