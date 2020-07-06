#!/usr/bin/python
# -*- coding: utf-8 -*-

class AmqpParams:
    @staticmethod
    def get():
        from commlib_py.transports.amqp import ConnectionParameters
        conn_params = ConnectionParameters()
        conn_params.credentials.username = 'etsardou'
        conn_params.credentials.password = 'etsardou'
        conn_params.host = 'r4a-platform.ddns.net'
        conn_params.port = 8076
        conn_params.vhost = "etsardou"
        return conn_params
