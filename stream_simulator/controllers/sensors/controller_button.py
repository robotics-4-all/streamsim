#!/usr/bin/python
# -*- coding: utf-8 -*-

from stream_simulator.base_classes import BaseThing

class ButtonController(BaseThing):
    def __init__(self, conf = None, package = None):

        id = "d_button_" + str(BaseThing.id + 1)
        name = id
        if 'name' in conf:
            name = conf['name']
        _category = "sensor"
        _class = "button"
        _subclass = "tactile"
        _pack = package["name"]
        _namespace = package["namespace"]

        super().__init__(id)

        info = {
            "type": "BUTTON",
            "brand": "simple",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": name,
            "place": conf["place"],
            "id": id,
            "enabled": True,
            "orientation": float(conf["orientation"]),
            "hz": 1,
            "mode": package["mode"],
            "speak_mode": package["speak_mode"],
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
        print(info["base_topic"])