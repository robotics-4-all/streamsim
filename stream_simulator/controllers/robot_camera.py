"""
File that contains the camera controller.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging

from .base_camera import BaseCameraController

class CameraController(BaseCameraController):
    """
    A controller class for managing camera operations, inheriting from BaseCameraController.
    Attributes:
        logger (logging.Logger): The logger instance used for logging messages.
    Methods:
        __init__(conf=None, package=None):
            Initializes the CameraController with the given configuration and package.
    """
    def __init__(self, conf = None, package = None, host = "robot"):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        super().__init__(conf = conf, package = package)
