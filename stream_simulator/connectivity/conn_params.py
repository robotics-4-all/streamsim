#!/usr/bin/python
# -*- coding: utf-8 -*-

class ConnParams:
    type = "redis"

    @staticmethod
    def get(type):
        if type == "mqtt":
            from commlib.transports.mqtt import ConnectionParameters
            conn_params = ConnectionParameters(
                host='locsys.issel.ee.auth.gr',
                port=1883,
                username='sensors',
                password='issel.sensors',
            )
            return conn_params

        elif type == "redis":
            from commlib.transports.redis import ConnectionParameters
            conn_params = ConnectionParameters()
            return conn_params
