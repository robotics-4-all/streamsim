#!/usr/bin/python
# -*- coding: utf-8 -*-

import redis
import json

class RpcServer:
    def __init__(self, topic = None, func = None):
        self.topic = topic

        self.r = redis.Redis(host='localhost', port=6379, db=0)
        self.p = self.r.pubsub(ignore_subscribe_messages=True)

        self.custom_fun = func
        self.p.subscribe(**{self.topic + ":req": self.internal_handler})

    def start(self, timeout = 0.1):
        self.thread = self.p.run_in_thread(sleep_time = timeout)

    def stop(self):
        self.thread.stop()

    def internal_handler(self, message):
        res = self.custom_fun(json.loads(message['data']))
        self.r.publish(self.topic + ":res", json.dumps(res))
