#!/usr/bin/python
# -*- coding: utf-8 -*-

import redis

class Subscriber:
    def __init__(self, topic = None, func = None):
        self.r = redis.Redis(host='localhost', port=6379, db=0)
        self.p = self.r.pubsub(ignore_subscribe_messages=True)
        if func is not None:
            self.p.subscribe(**{topic: func})
        else:
            self.p.subscribe(**{topic: self.sub_handler})

    def start(self, timeout = 0.1):
        self.thread = self.p.run_in_thread(sleep_time = timeout)

    def sub_handler(self, message):
        print("Got ", message['data'])
