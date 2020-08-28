#!/usr/bin/python
# -*- coding: utf-8 -*-

# from commlib_py.transports.redis import RPCClient
# from commlib_py.transports.redis import ConnectionParameters
# conn_params = ConnectionParameters()
# conn_params.host = "localhost"
# conn_params.port = 6379

from commlib.transports.amqp import Publisher
from commlib.transports.amqp import ConnectionParameters
conn_params = ConnectionParameters()
conn_params.credentials.username = 'bot'
conn_params.credentials.password = 'b0t'
conn_params.host = 'tektrain-cloud.ddns.net'
conn_params.port = 5672
conn_params.vhost = "sim"

import yaml
import pathlib

cl = Publisher(conn_params=conn_params, topic="robot_1.step_by_step")
cl.publish("")
