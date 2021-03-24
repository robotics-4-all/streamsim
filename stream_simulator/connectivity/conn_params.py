#!/usr/bin/python
# -*- coding: utf-8 -*-

class ConnParams:
    type = "redis"

    @staticmethod
    def get(type):
        if type == "amqp":
            from commlib.transports.amqp import ConnectionParameters
            conn_params = ConnectionParameters()
            conn_params.credentials.username = 'bot'
            conn_params.credentials.password = 'b0t'

            conn_params.host = 'localhost'
            conn_params.port = 5672
            conn_params.vhost = "/"
            #
            # conn_params.host = 'tektrain-cloud.ddns.net'
            # conn_params.port = 5672
            # conn_params.vhost = "sim"

            return conn_params
        elif type == "redis":
            from commlib.transports.redis import ConnectionParameters
            conn_params = ConnectionParameters()
            conn_params.host = "localhost"
            conn_params.port = 6379
            return conn_params
