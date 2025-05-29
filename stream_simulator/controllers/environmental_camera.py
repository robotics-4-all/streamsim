"""
File that contains the camera controller.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging

from .base_camera import BaseCameraController

class EnvCameraController(BaseCameraController):
    """
    A controller class for managing an environmental camera.
    This class extends the `BaseCameraController` and is responsible for 
    initializing and managing the environmental camera with specific configurations.
    Attributes:
        logger (logging.Logger): The logger instance used for logging messages. 
                                 If a logger is provided in the `package`, it will be used; 
                                 otherwise, a new logger is created using the configuration name.
    Args:
        conf (dict, optional): Configuration dictionary containing settings for the controller. 
                               Defaults to None.
        package (dict, optional): A dictionary containing shared resources such as a logger. 
                                  Defaults to None.
    """

    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        super().__init__(conf = conf, package = package, host = "env")
