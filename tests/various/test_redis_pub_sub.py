#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import sys, traceback
import time
import os

from stream_simulator.connectivity import CommlibFactory

import threading
import logging


class TestRedisPublisherSubscriber(unittest.TestCase):
    PUB_SUB_TOPIC = "this.is.a.test.pub_sub.topic"
    MESSAGE = "This is a test pub/sub message"

    def setUp(self):
        logging.basicConfig(format='%(asctime)s %(message)s') 
        self.logger=logging.getLogger() 
        self.logger.setLevel(logging.DEBUG) 

        self._pub_freq = 5
        self._pub_duration = 5
        self._num_of_subs = 5
        self._sub_alive = True
        self._sub_cb_failed = False
        self._counter = [0] * 5

    def test_publisher_subscriber(self):
        try:
            # initialize subscriber
            self._publisher = CommlibFactory.getPublisher(
                broker = "redis",
                topic = TestRedisPublisherSubscriber.PUB_SUB_TOPIC,
            )

            self.sub_threads = list()
            for i in range(self._num_of_subs):
                thread = threading.Thread(target=self._subscriber, args=(i,), daemon=True)
                thread.start()
                self.sub_threads.append(thread)
            
            # give some time so threads can be initialized
            time.sleep(0.1)

            counter = 0
            start = time.time()
            while (time.time() - start) < self._pub_duration:
                msg = {
                    "timestamp": time.time(),
                    "data": TestRedisPublisherSubscriber.MESSAGE + str(counter)
                }

                self._publisher.publish(msg)
                
                self.assertEqual(self._sub_cb_failed, False)

                self.logger.debug(f"Publishing test message {counter}!")

                counter = counter + 1     

                time.sleep(1 / self._pub_freq)
        except:
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)
    
    def _subscriber(self, id):
        self.logger.debug(f"Initializing subscriber {id}")

        def _sub_callback(message, meta):
            try:
                self.logger.debug(f"Subscriber {id} received: {message['data']}")

                now = time.time()
                self.assertEqual('data' in message, True)
                self.assertEqual('timestamp' in message, True)
                
                self.assertLess(message['timestamp'], now)
                self.assertEqual(message['data'], 
                                TestRedisPublisherSubscriber.MESSAGE + str(self._counter[id]))
                

                self._counter[id] = self._counter[id] + 1
            except:
                traceback.print_exc(file=sys.stdout)
                self._sub_cb_failed = True
                self.assertTrue(False)
        
        subscriber = CommlibFactory.getSubscriber(
            broker = "redis",
            topic = TestRedisPublisherSubscriber.PUB_SUB_TOPIC,
            callback = _sub_callback
        )
        subscriber.run()

        while self._sub_alive:
            time.sleep(0.1)

        subscriber.stop()
        self.logger.debug(f"Terminating subscriber {id}")

    def tearDown(self):
        self._sub_alive = False
        for i in range(self._num_of_subs):
            self.sub_threads[i].join()

if __name__ == '__main__':  
    unittest.main()
    