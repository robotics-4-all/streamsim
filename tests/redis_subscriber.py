#!/usr/bin/python
# -*- coding: utf-8 -*-

from colorama import Fore, Style

from commlib.transports.redis import Subscriber
from commlib.transports.redis import ConnectionParameters
conn_params = ConnectionParameters()
conn_params.host = "localhost"
conn_params.port = 6379

import yaml
import pathlib

import sys
import time

def subscriber_callback(message, meta):
    print(f">> {message}")

sub = Subscriber(
    conn_params=conn_params,
    topic=sys.argv[1],
    on_message=subscriber_callback)

sub.run()
print(f"Subscribed to {sys.argv[1]}")
while True:
    time.sleep(1)
