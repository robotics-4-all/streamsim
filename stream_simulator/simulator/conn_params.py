#!/usr/bin/python
# -*- coding: utf-8 -*-

class ConnParams:
    type = "redis"

    @staticmethod
    def get():
        if ConnParams.type == "amqp":
            from commlib.transports.amqp import ConnectionParameters
            conn_params = ConnectionParameters()
            conn_params.credentials.username = 'etsardou'
            conn_params.credentials.password = 'etsardou'
            conn_params.host = 'r4a-platform.ddns.net'
            conn_params.port = 8076
            conn_params.vhost = "etsardou"
            return conn_params
        elif ConnParams.type == "redis":
            from commlib.transports.redis import ConnectionParameters
            conn_params = ConnectionParameters()
            conn_params.host = "localhost"
            conn_params.port = 6379
            return conn_params
