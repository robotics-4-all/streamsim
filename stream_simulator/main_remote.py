#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import sys
import threading

from stream_simulator import Simulator

from commlib_py.logger import Logger

from commlib_py.transports.amqp import RPCServer
from commlib_py.transports.amqp import ConnectionParameters
conn_params = ConnectionParameters()
conn_params.credentials.username = 'bot'
conn_params.credentials.password = 'b0t'
conn_params.host = 'tektrain-cloud.ddns.net'
conn_params.port = 5672
conn_params.vhost = "sim"

# from commlib_py.transports.redis import RPCServer
# from commlib_py.transports.redis import ConnectionParameters
# conn_params = ConnectionParameters()
# conn_params.host = "localhost"
# conn_params.port = 6379

class SimulatorHandler:
    def __init__(self):
        self.logger = Logger("main_remote")

        self.start = RPCServer(
            conn_params=conn_params,
            on_request=self.start_callback,
            rpc_name='simulator.start'
        )
        self.stop = RPCServer(
            conn_params=conn_params,
            on_request=self.stop_callback,
            rpc_name='simulator.stop'
        )

        self.start.run()
        self.stop.run()

        self.threads = {}
        self.simulations = {}

    def print(self):
        print("Simulators:")
        for s in self.simulations:
            print(s, self.simulations[s])

    def start_callback(self, message, meta):
        print(message)
        name = "device_" + str(len(self.simulations))
        s = Simulator(configuration = message, device = name)
        self.simulations[name] = s
        th = threading.Thread(target = s.start())
        th.start()
        self.threads[name] = th
        self.print()
        return {"status": True, "name": name}

    def stop_callback(self, message, meta):
        name = message["device"]
        self.logger.warning("Trying to stop device {}".format(name))
        self.simulations[name].stop()
        self.simulations.pop(name)
        # Must do a better job here!
        self.threads.pop(name)
        self.print()
        return {"status": 0}

if __name__ == "__main__":
    s = SimulatorHandler()
    while True:
        time.sleep(1)
