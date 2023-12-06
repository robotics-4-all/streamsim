#!/usr/bin/python
# -*- coding: utf-8 -*-

import importlib
from colorama import Fore, Back, Style
import logging

from stream_simulator.connectivity import ConnParams

class CommlibFactory:
    logger = logging.getLogger(__name__)
    colors = {
        "redis": Fore.GREEN,
        "mqtt": Fore.RED,
        "RPCService": Fore.YELLOW,
        "RPCClient": Fore.BLUE,
        "Subscriber": Fore.MAGENTA,
        "Publisher": Fore.CYAN,
        "ActionServer": Fore.WHITE,
        "ActionClient": Back.RED + Fore.WHITE
    }
    reset = Style.RESET_ALL
    notify = None
    get_tf_affection = None
    get_tf = None

    @staticmethod
    def notify_ui(type = None, data = None):
        if CommlibFactory.notify is not None:
            CommlibFactory.notify.publish({
                'type': type,
                'data': data
            })
            CommlibFactory.logger.info(f"{Fore.MAGENTA}UI inform {type}: {data}{Style.RESET_ALL}")

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

    @staticmethod
    def inform(broker, topic, type):
        col = CommlibFactory.colors[broker]
        met = CommlibFactory.colors[type]
        res = CommlibFactory.reset
        CommlibFactory.logger.info(
            f"{met}{Style.BRIGHT}{broker}::{type} {col}<{topic}>{res}"
        )

    @staticmethod
    def getPublisher(broker = "redis", topic = None):
        ret = None
        module = importlib.import_module(
            f"commlib.transports.{broker}"
        )
        ret = module.Publisher(
            conn_params = ConnParams.get(broker),
            topic = topic
        )
        CommlibFactory.inform(broker, topic, "Publisher")
        CommlibFactory.stats[broker]['publishers'] += 1
        return ret

    @staticmethod
    def getSubscriber(broker = "redis", topic = None, callback = None):
        ret = None
        module = importlib.import_module(
            f"commlib.transports.{broker}"
        )
        ret = module.Subscriber(
            conn_params = ConnParams.get(broker),
            topic = topic,
            on_message = callback
        )
        CommlibFactory.inform(broker, topic, "Subscriber")
        CommlibFactory.stats[broker]['subscribers'] += 1
        return ret

    @staticmethod
    def getRPCService(broker = "redis", rpc_name = None, callback = None):
        ret = None
        module = importlib.import_module(
            f"commlib.transports.{broker}"
        )
        ret = module.RPCService(
            conn_params = ConnParams.get(broker),
            on_request = callback,
            rpc_name = rpc_name
        )
        CommlibFactory.inform(broker, rpc_name, "RPCService")
        CommlibFactory.stats[broker]['rpc servers'] += 1
        return ret

    @staticmethod
    def getRPCClient(broker = "redis", rpc_name = None):
        ret = None
        module = importlib.import_module(
            f"commlib.transports.{broker}"
        )
        ret = module.RPCClient(
            conn_params = ConnParams.get("redis"),
            rpc_name = rpc_name
        )
        CommlibFactory.inform(broker, rpc_name, "RPCClient")
        CommlibFactory.stats[broker]['rpc clients'] += 1
        return ret

    @staticmethod
    def getActionServer(broker = "redis", action_name = None, callback = None):
        ret = None
        module = importlib.import_module(
            f"commlib.transports.{broker}"
        )
        ret = module.ActionService(
            conn_params = ConnParams.get(broker),
            on_goal = callback,
            action_name = action_name
        )
        CommlibFactory.inform(broker, action_name, "ActionServer")
        CommlibFactory.stats[broker]['action servers'] += 1
        return ret

    @staticmethod
    def getActionClient(broker = "redis", action_name = None):
        ret = None
        module = importlib.import_module(
            f"commlib.transports.{broker}"
        )
        ret = module.ActionClient(
            conn_params = ConnParams.get(broker),
            action_name = action_name
        )
        CommlibFactory.inform(broker, action_name, "ActionClient")
        CommlibFactory.stats[broker]['action clients'] += 1
        return ret
