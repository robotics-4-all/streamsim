#!/usr/bin/python
# -*- coding: utf-8 -*-

from colorama import Fore, Style

from commlib.transports.redis import RPCClient
from commlib.transports.redis import ConnectionParameters
conn_params = ConnectionParameters()
conn_params.host = "localhost"
conn_params.port = 6379
import json

import yaml
import pathlib

import sys
import time

cl = RPCClient(conn_params=conn_params, rpc_name=sys.argv[1])

cl.call(json.loads(sys.argv[2]))
