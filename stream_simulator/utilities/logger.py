#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging

class Logger:
    def __init__(self, name, debug_level):
        self.logger = logging.getLogger(name)
        formatter = logging.Formatter('%(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(asctime)s - %(message)s')
        self.logger.setLevel(debug_level)
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

    def debug(self, str):
        self.logger.debug("%s", str)
    def info(self, str):
        self.logger.info("%s", str)
    def warning(self, str):
        self.logger.warning("%s", str)
    def error(self, str):
        self.logger.error("%s", str)
    def critical(self, str):
        self.logger.critical("%s", str)
