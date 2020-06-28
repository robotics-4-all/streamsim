#!/usr/bin/python
# -*- coding: utf-8 -*-

import redis
import json

class Publisher:
    def __init__(self, topic = None):
        self.r = redis.Redis(host='localhost', port=6379, db=0)
        self.topic = topic

    def publish(self, msg):
        self.r.publish(self.topic, json.dumps(msg))
