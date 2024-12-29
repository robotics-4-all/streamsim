"""
File that contains the button controller.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

from stream_simulator.base_classes import BaseThing

class ButtonController(BaseThing):
    """
    ButtonController is a class that represents a tactile button sensor controller.
    Attributes:
        info (dict): A dictionary containing detailed information about the button sensor.
        name (str): The name of the button sensor.
    Methods:
        __init__(conf=None, package=None):
            Initializes the ButtonController with the given configuration and package details.
    Args:
        conf (dict, optional): Configuration dictionary for the button sensor. Defaults to None.
            Expected keys in conf:
                - name (str): The name of the button sensor.
                - place (str): The place where the button sensor is located.
                - orientation (float): The orientation of the button sensor.
        package (dict, optional): Package dictionary containing package details. Defaults to None.
            Expected keys in package:
                - name (str): The name of the package.
                - namespace (str): The namespace of the package.
                - mode (str): The mode of the package.
                - device_name (str): The device name of the package.
    """
    def __init__(self, conf = None, package = None):

        id_ = "d_button_" + str(BaseThing.id + 1)
        name = id_
        if 'name' in conf:
            name = conf['name']
        _category = "sensor"
        _class = "button"
        _subclass = "tactile"
        _pack = package["name"]
        _namespace = package["namespace"]

        super().__init__(id_, auto_start=False)
        self.set_simulation_communication(_namespace)
        self.commlib_factory.run()

        info = {
            "type": "BUTTON",
            "brand": "simple",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": name,
            "place": conf["place"],
            "id": id_,
            "enabled": True,
            "orientation": float(conf["orientation"]),
            "hz": 1,
            "mode": package["mode"],
            "namespace": package["namespace"],
            "device_name": package["device_name"],
            "categorization": {
                "host_type": "robot",
                "place": _pack.split(".")[-1],
                "category": _category,
                "class": _class,
                "subclass": [_subclass],
                "name": name
            }
        }

        self.info = info
        self.name = info["name"]
