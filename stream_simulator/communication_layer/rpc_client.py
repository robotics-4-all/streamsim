#!/usr/bin/python
# -*- coding: utf-8 -*-

import redis
import json
import time

class RpcClient:
    def __init__(self, topic = None):
        self.topic = topic

        self.r = redis.Redis(host='localhost', port=6379, db=0)
        self.p = self.r.pubsub(ignore_subscribe_messages=True)

    def call(self, msg, timeout = 0.1):
        self.p.subscribe(**{self.topic + ":res": self.internal_handler})
        self.thread = self.p.run_in_thread(sleep_time = timeout)
        self.result = None
        self.r.publish(self.topic + ":req", json.dumps(msg))

        while self.result is None:
            time.sleep(0.1)

        self.thread.stop()
        return self.result

    def internal_handler(self, message):
        self.result = json.loads(message['data'])
