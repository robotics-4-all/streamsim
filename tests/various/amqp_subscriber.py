#!/usr/bin/python
# -*- coding: utf-8 -*-

from colorama import Fore, Style

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
