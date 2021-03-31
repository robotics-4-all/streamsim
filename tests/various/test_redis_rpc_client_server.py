#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import sys, traceback
import time
import os

from stream_simulator.connectivity import CommlibFactory

import threading
import logging


class TestRedisRPCClientServer(unittest.TestCase):
    RPC_TOPIC = "this.is.a.test.rpc.topic"
    MESSAGE = "This is a test rpc message"

    def setUp(self):
        logging.basicConfig(format='%(asctime)s %(message)s') 
        self.logger=logging.getLogger() 
        self.logger.setLevel(logging.DEBUG) 

        self._rpc_cb_was_called = False

    def test_rpc_client_server(self):
        try:
            # initialize rpc service
            self._rpc_service = CommlibFactory.getRPCService(
                broker = "redis",
                rpc_name = TestRedisRPCClientServer.RPC_TOPIC,
                callback = self._rpc_callback
            )
            self._rpc_service.run()

            time.sleep(0.1)

            # initialize rpc client
            rpc_client = CommlibFactory.getRPCClient(
                broker = "redis",
                rpc_name = TestRedisRPCClientServer.RPC_TOPIC
            )
            
            # send message
            msg = {
                'data': TestRedisRPCClientServer.MESSAGE
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
    
    def _rpc_callback(self, message, meta):
        self.logger.debug(f"Rpc service received: {message['data']}")

        self._rpc_cb_was_called = True

        ret = {
            "timestamp": time.time(),
            "data": message['data']
        }
        
        return ret

    def tearDown(self):
        pass

if __name__ == '__main__':  
    unittest.main()
    