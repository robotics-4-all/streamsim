#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random

from stream_simulator.base_classes import BaseThing

class EncoderController(BaseThing):
    def __init__(self, conf = None, package = None):
        if package["logger"] is None:
            self.logger = logging.getLogger(conf["name"])
        else:
            self.logger = package["logger"]

        id = "d_encoder_" + str(BaseThing.id + 1)
        name = id
        if 'name' in conf:
            name = conf['name']
        _category = "sensor"
        _class = "encoder"
        _subclass = "absolute"
        _pack = package["name"]
        
        super().__init__(id)

        info = {
            "type": "ENCODER",
            "brand": "simple",
            "base_topic": f"{_pack}.{_category}.{_class}.{_subclass}.{name}",
            "name": name,
            "place": conf["place"],
            "id": id,
            "enabled": True,
            "orientation": conf["orientation"],
            "hz": conf["hz"],
            "mode": package["mode"],
            "speak_mode": package["speak_mode"],
            "namespace": package["namespace"],
            "sensor_configuration": conf["sensor_configuration"],
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
        self.conf = info["sensor_configuration"]
        self.base_topic = info["base_topic"]
        self.derp_data_key = info["base_topic"] + ".raw"
        self.robot = _pack.split(".")[-1]
        self.place = conf["place"]
        self.motion_derpme_topic = None

        self.set_tf_communication(package)

        self.wheel_radius = 0.02
        self.linear_coeff = 1.0 / (2 * math.pi * self.wheel_radius)
        self.angular_coeff = 3.0 # this should change

        # tf handling
        tf_package = {
            "type": "robot",
            "subtype": {
                "category": _category,
                "class": _class,
                "subclass": [_subclass]
            },
            "pose": conf["pose"],
            "base_topic": info['base_topic'],
            "name": self.name
        }
        tf_package['host'] = package['device_name']
        tf_package['host_type'] = 'robot'
        
        self.tf_declare_rpc.call(tf_package)

        self.publisher = self.commlib_factory.getPublisher(
            topic = self.base_topic + ".data"
        )

        self.enable_rpc_server = self.commlib_factory.getRPCService(
            callback = self.enable_callback,
            rpc_name = self.base_topic + ".enable"
        )
        self.disable_rpc_server = self.commlib_factory.getRPCService(
            callback = self.disable_callback,
            rpc_name = self.base_topic + ".disable"
        )

    def sensor_read(self):
        self.logger.info("Encoder {} sensor read thread started".format(self.info["id"]))
        period = 1.0 / self.info["hz"]

        while self.info["enabled"]:
            if self.info["mode"] == "mock":
                self.data = float(random.uniform(1000,2000))
            elif self.info["mode"] == "simulation":
                return
                time.sleep(1)
                # if self.motion_derpme_topic == None:
                #     rpc_cl = self.commlib_factory.getRPCClient(
                #         rpc_name = f"robot.{self.robot}.nodes_detector.get_connected_devices"
                #     )

                # get the two last velocities
                rl = {'val': [0, 0]} # this should change
                self.data = 0
                if len(rl['val']) == 0:
                    pass
                elif len(rl['val']) == 1:
                    t = 0
                    data = rl['val'][0]['data']
                    # check timestamps:
                    if rl['val'][0]['timestamp'] < time.time() - period:
                        # the whole period had the velocity
                        t = period
                        # print("vel was", rl['val'][0]['data'], "for", period, "sec")
                    else:
                        t = time.time() - rl['val'][0]['timestamp']

                    lin_factor = self.linear_coeff * t * data['linear']
                    if "L" in self.place:
                        rot_factor = - self.angular_coeff * t * data['angular']
                    else:
                        rot_factor = self.angular_coeff * t * data['angular']

                    self.data = lin_factor + rot_factor
                    # print("Case 1", t, lin_factor, rot_factor, self.data, self.name)

                else:
                    # check timestamps:
                    if rl['val'][0]['timestamp'] < time.time() - period:
                        # the whole period had the velocity
                        t = period
                        data = rl['val'][0]['data']
                        lin_factor = self.linear_coeff * t * data['linear']
                        if "L" in self.place:
                            rot_factor = - self.angular_coeff * t * data['angular']
                        else:
                            rot_factor = self.angular_coeff * t * data['angular']
                        self.data = lin_factor + rot_factor

                        # print("Case 1", t, lin_factor, rot_factor, self.data, self.name)
                    else:
                        t = time.time() - rl['val'][0]['timestamp']
                        data = rl['val'][0]['data']
                        lin_factor = self.linear_coeff * t * data['linear']
                        if "L" in self.place:
                            rot_factor = - self.angular_coeff * t * data['angular']
                        else:
                            rot_factor = self.angular_coeff * t * data['angular']
                        self.data = lin_factor + rot_factor
                        # print("Case 3", t, lin_factor, rot_factor, self.data, self.name)

                        # we must take the prev as well
                        t_p = time.time() - rl['val'][1]['timestamp']
                        if t_p > period:
                            t_p = period - t
                            data = rl['val'][1]['data']
                            lin_factor = self.linear_coeff * t_p * data['linear']
                            if "L" in self.place:
                                rot_factor = - self.angular_coeff * t_p * data['angular']
                            else:
                                rot_factor = self.angular_coeff * t_p * data['angular']
                            self.data += lin_factor + rot_factor

            time.sleep(period)

            # Publishing value:
            self.publisher.publish({
                "rpm": self.data,
                "timestamp": time.time()
            })

        self.logger.info("Encoder {} sensor read thread stopped".format(self.info["id"]))

    def enable_callback(self, message):
        self.info["enabled"] = True
        self.info["hz"] = message["hz"]
        self.info["queue_size"] = message["queue_size"]

        self.sensor_read_thread = threading.Thread(target = self.sensor_read)
        self.sensor_read_thread.start()
        return {"enabled": True}

    def disable_callback(self, message):
        self.info["enabled"] = False
        self.logger.info("Encoder {} stops reading".format(self.info["id"]))
        return {"enabled": False}

    def start(self):
        if self.info["enabled"]:
            self.sensor_read_thread = threading.Thread(target = self.sensor_read)
            self.sensor_read_thread.start()
            self.logger.info("Encoder {} reads with {} Hz".format(self.info["id"], self.info["hz"]))
    
    def stop(self):
        self.info["enabled"] = False
        self.commlib_factory.stop()
