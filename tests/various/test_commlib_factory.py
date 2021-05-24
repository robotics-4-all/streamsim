#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import sys, traceback
import time
import os

from stream_simulator.connectivity import CommlibFactory

import threading
import logging


class TestCommlibFactory(unittest.TestCase):
    RPC_TOPIC = "this.is.a.test.rpc.topic"
    PUB_SUB_TOPIC = "this.is.a.test.pub_sub.topic"
    ACTION_TOPIC = "this.is.a.test.action.topic"

    MESSAGE = "This is a test message"

    def setUp(self):
        logging.basicConfig(format='%(asctime)s %(message)s') 
        self.logger=logging.getLogger() 
        self.logger.setLevel(logging.DEBUG) 

    def test_rpc_client_server(self):
        try:
            self._rpc_cb_was_called = False

            # initialize rpc service
            self._rpc_service = CommlibFactory.getRPCService(
                broker = "redis",
                rpc_name = TestCommlibFactory.RPC_TOPIC,
                callback = self._rpc_callback
            )
            self._rpc_service.run()

            time.sleep(0.1)

            # initialize rpc client
            rpc_client = CommlibFactory.getRPCClient(
                broker = "redis",
                rpc_name = TestCommlibFactory.RPC_TOPIC
            )
            
            # send message
            msg = {
                'data': TestCommlibFactory.MESSAGE
            }
            ret = rpc_client.call(msg)

            # terminate rpc service
            self._rpc_service.stop()

            self.logger.debug(f"Received answer from rpc service: {ret}")

            # check if operation was succesful
            now = time.time()
            self.assertTrue(self._rpc_cb_was_called)

            self.assertEqual('data' in ret, True)
            self.assertEqual('timestamp' in ret, True)

            self.assertEqual(ret['data'], msg['data'])
            self.assertLess(ret['timestamp'], now)
        except:
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)

    def test_publisher_subscriber(self):
        try:
            self._pub_freq = 5
            self._pub_duration = 5
            self._num_of_subs = 5
            self._sub_alive = True
            self._sub_cb_failed = False
            self._counter = [0] * 5

            # initialize subscriber
            self._publisher = CommlibFactory.getPublisher(
                broker = "redis",
                topic = TestCommlibFactory.PUB_SUB_TOPIC,
            )

            sub_threads = list()
            for i in range(self._num_of_subs):
                thread = threading.Thread(target=self._subscriber, args=(i,), daemon=True)
                thread.start()
                sub_threads.append(thread)
            
            # give some time so threads can be initialized
            time.sleep(0.1)

            counter = 0
            start = time.time()
            while (time.time() - start) < self._pub_duration:
                msg = {
                    "timestamp": time.time(),
                    "data": TestCommlibFactory.MESSAGE + str(counter)
                }

                self._publisher.publish(msg)
                
                self.assertEqual(self._sub_cb_failed, False)

                self.logger.debug(f"Publishing test message {counter}!")

                counter = counter + 1     

                time.sleep(1 / self._pub_freq)
            
            self._sub_alive = False

            time.sleep(0.1)

            for i in range(self._num_of_subs):
                sub_threads[i].join()
        except:
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)

    def test_action_call(self):
        try:
            self._action_server_alive = True
            self._action_cb_failed = False

            action_thread = threading.Thread(target=self._action_server, args=(), daemon=True)
            action_thread.start()
            
            time.sleep(0.1)

            self._action_client = CommlibFactory.getActionClient(
                broker = "redis",
                action_name = TestCommlibFactory.ACTION_TOPIC
            )

            # test normal use
            msg = {
                'timestamp': time.time(),
                'data': TestCommlibFactory.MESSAGE,
                'duration': 2
            }

            resp = self._action_client.send_goal(msg)

            self.goal_id_play = resp["goal_id"]

            while self._action_client.get_result(self.goal_id_play)["status"] == 1:
                self.assertEqual(self._action_cb_failed, False)
                time.sleep(0.1)
        
            final_res = self._action_client.get_result(self.goal_id_play)
            
            self.assertEqual(self._action_cb_failed, False)
            self.assertEqual(final_res["status"], 4)
            
            self.assertEqual('timestamp' in final_res['result'], True)
            self.assertEqual('data' in final_res['result'], True)
            
            self.assertEqual(final_res['result']['data'], TestCommlibFactory.MESSAGE)
            self.assertLess(final_res['result']['timestamp'], time.time())

            # test preemption
            msg = {
                'timestamp': time.time(),
                'data': TestCommlibFactory.MESSAGE,
                'duration': 100
            }

            resp = self._action_client.send_goal(msg)

            self.goal_id_play = resp["goal_id"]

            now = time.time()
            while self._action_client.get_result(self.goal_id_play)["status"] == 1:
                self.assertEqual(self._action_cb_failed, False)

                if (time.time() - now) > 5:
                    self._action_client.cancel_goal(self.goal_id_play)

                time.sleep(0.1)
        
            final_res = self._action_client.get_result(self.goal_id_play)
            
            self.assertEqual(self._action_cb_failed, False)
            self.assertEqual(final_res["status"], 6)
            
            self.assertEqual('timestamp' in final_res['result'], True)
            self.assertEqual('data' in final_res['result'], True)
            
            self.assertEqual(final_res['result']['data'], TestCommlibFactory.MESSAGE)
            self.assertLess(final_res['result']['timestamp'], time.time())

            self._action_server_alive = False
            time.sleep(0.1)
            action_thread.join()
            
        except:
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)
            
    def _rpc_callback(self, message, meta):
        self.logger.debug(f"Rpc service received: {message['data']}")

        self._rpc_cb_was_called = True

        ret = {
            "timestamp": time.time(),
            "data": message['data']
        }
        
        return ret

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
                                TestCommlibFactory.MESSAGE + str(self._counter[id]))
                

                self._counter[id] = self._counter[id] + 1
            except:
                traceback.print_exc(file=sys.stdout)
                self._sub_cb_failed = True
                self.assertTrue(False)
        
        subscriber = CommlibFactory.getSubscriber(
            broker = "redis",
            topic = TestCommlibFactory.PUB_SUB_TOPIC,
            callback = _sub_callback
        )
        subscriber.run()

        while self._sub_alive:
            time.sleep(0.1)

        subscriber.stop()
        self.logger.debug(f"Terminating subscriber {id}")
        
    def _action_callback(self, goalh):
        try:
            self.logger.debug(f"Received action with data: {goalh.data}")

            now = time.time()
            
            self.assertEqual('timestamp' in goalh.data, True)
            self.assertEqual('data' in goalh.data, True)
            self.assertEqual('duration' in goalh.data, True)

            self.assertLess(goalh.data['timestamp'], now)
            self.assertEqual(goalh.data['data'], 
                            TestCommlibFactory.MESSAGE)

            ret = {
                'timestamp': time.time(),
                'data': TestCommlibFactory.MESSAGE
            }

            start = time.time()
            duration = goalh.data['duration']
            while (time.time() - start) < duration:
                if goalh.cancel_event.is_set():
                    self.logger.debug("Goal cancelled!")
                    return ret
                time.sleep(0.1)
            
            return ret
        
        except:
            traceback.print_exc(file=sys.stdout)
            self._action_cb_failed = True
            self.assertTrue(False)

    def _action_server(self):
        # initialize action service
        self.logger.debug("Starting action service")
        self._action_service = CommlibFactory.getActionServer(
            broker = "redis",
            action_name = TestCommlibFactory.ACTION_TOPIC,
            callback = self._action_callback
        )
        self._action_service.run()

        while self._action_server_alive:
            time.sleep(0.1)

        self._action_service.stop()
        self.logger.debug("Terminating action service")

    def tearDown(self):
        pass

if __name__ == '__main__':  
    unittest.main()
    