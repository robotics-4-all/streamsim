#!/usr/bin/python
# -*- coding: utf-8 -*-

from colorama import Fore, Style

from stream_simulator.connectivity import CommlibFactory

import yaml
import pathlib

import sys
import time

def subscriber_callback(message, meta):
    print(f">> {message}")

sub = CommlibFactory.getSubscriber(
    topic=sys.argv[1],
    broker='amqp'
)

sub.run()
print(f"Subscribed to {sys.argv[1]}")



while True:
    time.sleep(1)
