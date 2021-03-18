#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import sys, traceback
import time
import os

from stream_simulator.connectivity import CommlibFactory

import threading
import logging


class TestRedisActionClientServer(unittest.TestCase):
    ACTION_TOPIC = "this.is.a.test.action.topic"
    MESSAGE = "This is a test action message"

    def setUp(self):
        logging.basicConfig(format='%(asctime)s %(message)s') 
        self.logger=logging.getLogger() 
        self.logger.setLevel(logging.DEBUG) 

        self._action_server_alive = True
        self._action_cb_failed = False

        self.action_thread = threading.Thread(target=self._action_server, args=(), daemon=True)

    def test_action_call(self):
        try:
            self.action_thread.start()
            
            time.sleep(0.1)

            self._action_client = CommlibFactory.getActionClient(
                broker = "redis",
                action_name = TestRedisActionClientServer.ACTION_TOPIC
            )

            # test normal use
            msg = {
                'timestamp': time.time(),
                'data': TestRedisActionClientServer.MESSAGE,
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
            
            self.assertEqual(final_res['result']['data'], TestRedisActionClientServer.MESSAGE)
            self.assertLess(final_res['result']['timestamp'], time.time())

            # test preemption
            msg = {
                'timestamp': time.time(),
                'data': TestRedisActionClientServer.MESSAGE,
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
            
            self.assertEqual(final_res['result']['data'], TestRedisActionClientServer.MESSAGE)
            self.assertLess(final_res['result']['timestamp'], time.time())           
        except:
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)
    
    def _action_callback(self, goalh):
        try:
            self.logger.debug(f"Received action with data: {goalh.data}")

            now = time.time()
            
            self.assertEqual('timestamp' in goalh.data, True)
            self.assertEqual('data' in goalh.data, True)
            self.assertEqual('duration' in goalh.data, True)

            self.assertLess(goalh.data['timestamp'], now)
            self.assertEqual(goalh.data['data'], 
                            TestRedisActionClientServer.MESSAGE)

            ret = {
                'timestamp': time.time(),
                'data': TestRedisActionClientServer.MESSAGE
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
            action_name = TestRedisActionClientServer.ACTION_TOPIC,
            callback = self._action_callback
        )
        self._action_service.run()

        while self._action_server_alive:
            time.sleep(0.1)

        self._action_service.stop()
        self.logger.debug("Terminating action service")

    def tearDown(self):
        self._action_server_alive = False
        self.action_thread.join()

if __name__ == '__main__':  
    unittest.main()
    