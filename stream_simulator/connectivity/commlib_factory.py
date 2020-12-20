#!/usr/bin/python
# -*- coding: utf-8 -*-

import importlib
from colorama import Fore, Style

from stream_simulator.connectivity import ConnParams

from commlib.logger import Logger
from derp_me.client import DerpMeClient

class CommlibFactory:
    logger = Logger("commlib_factory")
    colors = {
        "redis": Fore.GREEN,
        "amqp": Fore.RED,
        "RPCService": Fore.YELLOW,
        "RPCClient": Fore.BLUE,
        "Subscriber": Fore.MAGENTA,
        "Publisher": Fore.CYAN,
        "ActionServer": Fore.WHITE
    }
    reset = Style.RESET_ALL
    derp_client = DerpMeClient(conn_params=ConnParams.get("redis"))

    @staticmethod
    def inform(broker, topic, type):
        col = CommlibFactory.colors[broker]
        met = CommlibFactory.colors[type]
        res = CommlibFactory.reset
        CommlibFactory.logger.info(
            f"{met}{Style.BRIGHT}{broker}::{type} {col}<{topic}>{res}"
        )

    @staticmethod
    def getPublisher(broker = None, topic = None):
        ret = None
        module = importlib.import_module(
            f"commlib.transports.{broker}"
        )
        ret = module.Publisher(
            conn_params = ConnParams.get(broker),
            topic = topic
        )
        CommlibFactory.inform(broker, topic, "Publisher")
        return ret

    @staticmethod
    def getSubscriber(broker = None, topic = None, callback = None):
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
        return ret

    @staticmethod
    def getRPCService(broker = None, rpc_name = None, callback = None):
        ret = None
        module = importlib.import_module(
            f"commlib.transports.{broker}"
        )
        ret = module.RPCService(
            conn_params = ConnParams.get("redis"),
            on_request = callback,
            rpc_name = rpc_name
        )
        CommlibFactory.inform(broker, rpc_name, "RPCService")
        return ret
