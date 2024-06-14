#!/usr/bin/python
# -*- coding: utf-8 -*-

import importlib
from colorama import Fore, Back, Style
import logging
import inspect
import pprint

from commlib.msg import PubSubMessage
from commlib.utils import Rate
from commlib.node import Node
from commlib.transports.mqtt import ConnectionParameters

class CommlibFactory(Node):
    stats = {
        'mqtt': {
            'publishers': 0,
            'subscribers': 0,
            'rpc servers': 0,
            'rpc clients': 0,
            'action servers': 0,
            'action clients': 0
        },
        'redis': {
            'publishers': 0,
            'subscribers': 0,
            'rpc servers': 0,
            'rpc clients': 0,
            'action servers': 0,
            'action clients': 0
        }
    }

    def __init__(self, *args, **kwargs):
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        self._logger = logging.getLogger(__name__)
        self._logger.info(f'[*] Commlib factory initiated from {calframe[1][1].split("/")[-1]}:{calframe[1][2]}')

        self.notify = None
        self.get_tf_affection = None
        self.get_tf = None

        self.conn_params = ConnectionParameters(
            host='locsys.issel.ee.auth.gr',
            port=8883,
            ssl=True,
            username='sensors',
            password='issel.sensors',
        )

        super().__init__(
            connection_params=self.conn_params,
            *args, **kwargs
        )

    def notify_ui(self, type = None, data = None):
        if self.notify is not None:
            self.notify.publish({
                'type': type,
                'data': data
            })
            self._logger.info(f"UI inform {type}: {data}")

    def inform(self, broker, topic, type, extras = ""):
        self._logger.info(
            f"{broker}::{type} <{topic}> @ {extras if extras != '' else '-'}"
        )

    def getPublisher(self, broker = "mqtt", topic = None):
        ret = self.create_publisher(
            topic = topic
        )
        ret.run()

        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        self.inform(broker, topic, "Publisher", f"{calframe[1][1].split('/')[-1]}:{calframe[1][2]}")
        CommlibFactory.stats[broker]['publishers'] += 1
        return ret

    def getSubscriber(self, broker = "mqtt", topic = None, callback = None):
        ret = self.create_subscriber(
            topic = topic,
            on_message = callback
        )
        ret.run()
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        self.inform(broker, topic, "Subscriber", f"{calframe[1][1].split('/')[-1]}:{calframe[1][2]}")
        CommlibFactory.stats[broker]['subscribers'] += 1
        return ret

    def getRPCService(self, broker = "mqtt", rpc_name = None, callback = None):
        ret = self.create_rpc(
            on_request = callback,
            rpc_name = rpc_name
        )
        ret.run()
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        self.inform(broker, rpc_name, "RPCService", f"{calframe[1][1].split('/')[-1]}:{calframe[1][2]}")
        CommlibFactory.stats[broker]['rpc servers'] += 1
        return ret

    def getRPCClient(self, broker = "mqtt", rpc_name = None):
        ret = self.create_rpc_client(
            rpc_name = rpc_name
        )
        ret.run()
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        self.inform(broker, rpc_name, "RPCClient", f"{calframe[1][1].split('/')[-1]}:{calframe[1][2]}")
        CommlibFactory.stats[broker]['rpc clients'] += 1
        return ret

    def getActionServer(self, broker = "mqtt", action_name = None, callback = None):
        ret = self.create_action(
            on_goal = callback,
            action_name = action_name
        )
        ret.run()
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        self.inform(broker, action_name, "ActionServer", f"{calframe[1][1].split('/')[-1]}:{calframe[1][2]}")
        CommlibFactory.stats[broker]['action servers'] += 1
        return ret

    def getActionClient(self, broker = "mqtt", action_name = None):
        ret = self.create_action_client(
            action_name = action_name
        )
        ret.run()
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        self.inform(broker, action_name, "ActionClient", f"{calframe[1][1].split('/')[-1]}:{calframe[1][2]}")
        CommlibFactory.stats[broker]['action clients'] += 1
        return ret