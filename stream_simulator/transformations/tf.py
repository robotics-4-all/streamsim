#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import json
import math
import logging
import threading
import random
from colorama import Fore, Style
import pprint

from commlib.logger import Logger
from stream_simulator.connectivity import CommlibFactory

class TfController:
    def __init__(self, base = None, resolution = None, logger = None):
        self.logger = Logger("tf") if logger is None else logger
        self.base_topic = base + ".tf" if base is not None else "streamsim.tf"
        self.base = base
        self.resolution = resolution

        self.declare_rpc_server = CommlibFactory.getRPCService(
            callback = self.declare_callback,
            rpc_name = self.base_topic + ".declare"
        )
        self.declare_rpc_server.run()

        self.get_declarations_rpc_server = CommlibFactory.getRPCService(
            callback = self.get_declarations_callback,
            rpc_name = self.base_topic + ".get_declarations"
        )
        self.get_declarations_rpc_server.run()

        self.get_tf_rpc_server = CommlibFactory.getRPCService(
            callback = self.get_tf_callback,
            rpc_name = self.base_topic + ".get_tf"
        )
        self.get_tf_rpc_server.run()

        self.get_affectability_rpc_server = CommlibFactory.getRPCService(
            callback = self.get_affections_callback,
            rpc_name = self.base_topic + ".get_affections"
        )
        self.get_affectability_rpc_server.run()

        self.get_sim_detection_rpc_server = CommlibFactory.getRPCService(
            callback = self.get_sim_detection_callback,
            rpc_name = self.base_topic + ".simulated_detection"
        )
        self.get_sim_detection_rpc_server.run()

        self.declare_rpc_input = [
            'type', 'subtype', 'name', 'pose', 'base_topic', 'range', 'fov', \
            'host', 'host_type', 'properties'
        ]

        self.declarations = []
        self.declarations_info = {}
        self.names = []

        self.effectors_get_rpcs = {}

        self.per_type = {
            'robot': {
                'sensor': {
                    'microphone': [],
                    'sonar': [],
                    'ir': [],
                    'tof': [],
                    'imu': [],
                    'camera': [],
                    'button': [],
                    'env': [],
                    'encoder': [],
                    'line_follow': [],
                    'rfid_reader': [],
                },
                'actuator': {
                    'speaker': [],
                    'leds': [],
                    'pan_tilt': [],
                    'screen': [],
                    'twist': [],
                }
            },
            'env': {
                'sensor': {
                    'ph': [],
                    'temperature': [],
                    'humidity': [],
                    'gas': [],
                    'camera': [],
                    'sonar': [],
                    'linear_alarm': [],
                    'area_alarm': [],
                    'light_sensor': [],
                    'microphone': [],
                },
                'actuator': {
                    'thermostat': [],
                    'relay': [],
                    'pan_tilt': [],
                    'speaker': [],
                    'leds': [],
                    'humidifier': [],
                }
            },
            'actor': {
                'human': [],
                'superman': [],
                'sound_source': [],
                'qr': [],
                'barcode': [],
                'color': [],
                'text': [],
                'rfid_tag': [],
                'fire': [],
                'water': [],
            }
        }

    def start(self):
        self.declare_rpc_server.run()

    def stop(self):
        self.declare_rpc_server.stop()

    def get_declarations_callback(self, message, meta):
        return {"declarations": self.declarations}

    def get_tf_callback(self, message, meta):
        name = message['name']
        if name not in self.items_hosts_dict:
            self.logger.error(f"TF: Requested transformation of missing device: {name}")
            return {}

        if name in self.robots:
            return self.places_absolute[name]
        elif name in self.pantilts:
            pose = self.places_absolute[name]
            base_th = 0
            if self.items_hosts_dict[name] != None:
                base_th = self.places_absolute[self.items_hosts_dict[name]]['theta']
            pose['theta'] = self.places_relative[name]['theta'] + \
                self.pantilts[name]['pan'] + base_th
            return pose
        else:
            return self.places_absolute[name]

    def setup(self):
        self.logger.info("*************** TF status ***************")
        self.subs = {} # Filled
        self.places_relative = {}
        self.places_absolute = {}
        self.tree = {} # filled
        self.items_hosts_dict = {}
        self.existing_hosts = []
        self.pantilts = {}
        self.robots = []

        # Fill tree
        for d in self.declarations:
            if d['host'] not in self.tree:
                self.tree[d['host']] = []

            self.tree[d['host']].append(d['name'])
            self.items_hosts_dict[d['name']] = d['host']

            self.places_relative[d['name']] = d['pose'].copy()
            self.places_absolute[d['name']] = d['pose'].copy()
            if 'x' in d['pose']: # The only culprit is linear alarm
                for i in ['x', 'y']:
                    self.places_relative[d['name']][i] *= self.resolution
                    self.places_absolute[d['name']][i] *= self.resolution

            if d['range'] != None:
                d['range'] *= self.resolution

        # Get all devices and check pan-tilts exist
        get_devices_rpc = CommlibFactory.getRPCClient(
            rpc_name = self.base + ".get_device_groups"
        )
        res = get_devices_rpc.call({})

        # Pan tilts on robots
        for r in res['robots']:
            cl = CommlibFactory.getRPCClient(
                broker = "redis",
                rpc_name = f"robot.{r}.nodes_detector.get_connected_devices"
            )
            rr = cl.call({})
            for d in rr['devices']:
                if d['type'] == 'PAN_TILT':
                    self.pantilts[d['name']] = {
                        'base_topic': d['base_topic'],
                        'place': d['categorization']['place'],
                        'pan': 0.0
                    }

        # Pan tilts in environment
        cl = CommlibFactory.getRPCClient(
            rpc_name = f"{res['world']}.nodes_detector.get_connected_devices"
        )
        rr = cl.call({})
        for d in rr['devices']:
            if d['type'] == 'PAN_TILT':
                self.pantilts[d['name']] = {
                    'base_topic': d['base_topic'],
                    'place': d['categorization']['place'],
                    'pan': 0.0
                }

        self.logger.info("Pan tilts detected:")
        for p in self.pantilts:
            self.logger.info(f"\t{p} on {self.pantilts[p]['place']}")

            self.existing_hosts.append(p)

            topic = self.pantilts[p]['base_topic'] + '.data'
            self.subs[p] = CommlibFactory.getSubscriber(
                topic = topic,
                callback = self.pan_tilt_callback
            )

        # Gather robots and create subscribers
        for d in self.declarations:
            if d['host_type'] == "robot":
                if d['host'] not in self.existing_hosts:
                    self.robots.append(d['host'])
                    self.existing_hosts.append(d['host'])

                    topic = d['host_type'] + "." + d["host"] + ".pose"
                    self.subs[d['host']] = CommlibFactory.getSubscriber(
                        topic = topic,
                        callback = self.robot_pose_callback
                    )

        # Check pan tilt poses for None
        for pt in self.pantilts:
            for k in ['x', 'y', 'theta']:
                if self.places_relative[pt][k] == None:
                    self.logger.error(f"Pan-tilt {pt} has {k} = None. Please fix it in yaml.")

        for h in self.tree:
            if h not in self.existing_hosts and h != None:
                self.logger.error(f"We have a missing host: {h}")
                self.logger.error(f"\tAffected devices: {self.tree[h]}")

        # update poses based on tree for pan-tilts
        for d in self.pantilts:
            if d in self.tree:  # We can have a pan-tilt with no devices on it
                for i in self.tree[d]:
                    # initial pan is considered 0
                    pt_abs_pose = self.places_absolute[d]
                    self.places_absolute[i]['x'] += pt_abs_pose['x']
                    self.places_absolute[i]['y'] += pt_abs_pose['y']
                    if self.places_absolute[i]['theta'] != None:
                        self.places_absolute[i]['theta'] += pt_abs_pose['theta']

                    # self.logger.info(f"{i}@{d}:")
                    # self.logger.info(f"\tPan-tilt: {self.places_absolute[d]}")
                    # self.logger.info(f"\tRelative: {self.places_relative[i]}")
                    # self.logger.info(f"\tAbsolute: {self.places_absolute[i]}")

        self.logger.info("*****************************************")

        # pprint.pprint(self.per_type)

        # starting subs
        for s in self.subs:
            self.subs[s].run()

    def robot_pose_callback(self, message, meta):
        nm = message['name'].split(".")[-1]
        # self.logger.info(f"Updating {nm}: {message}")
        if nm not in self.places_absolute:
            self.places_absolute[nm] = {'x': 0, 'y': 0, 'theta': 0}
        self.places_absolute[nm]['x'] = message['x']
        self.places_absolute[nm]['y'] = message['y']
        self.places_absolute[nm]['theta'] = message['theta']

        # Update all thetas of devices
        for d in self.tree[nm]:
            if self.places_absolute[d]['theta'] != None and d not in self.pantilts:
                self.places_absolute[d]['theta'] = \
                    self.places_absolute[nm]['theta'] + \
                    self.places_relative[d]['theta']
                # self.logger.info(f"Updated {d}: {self.places_absolute[d]['theta']}")

            self.places_absolute[d]['x'] = self.places_absolute[nm]['x']
            self.places_absolute[d]['y'] = self.places_absolute[nm]['y']

            # Just setting devs on pan tilts the robot's pose
            if d in self.pantilts:
                pt_devs = self.tree[d]
                for dev in pt_devs:
                    self.places_absolute[dev]['x'] = self.places_absolute[nm]['x']
                    self.places_absolute[dev]['y'] = self.places_absolute[nm]['y']
                # Updating the angle of objects on pan-tilt
                # self.logger.info(f"Updating pt {d} on {nm}")
                pan_now = self.pantilts[d]['pan']
                # self.logger.info(f"giving {pan_now}")
                self.update_pan_tilt(d, pan_now)

    def update_pan_tilt(self, pt_name, pan):
        base_th = 0
        # If we are on a robot take its theta
        if self.items_hosts_dict[pt_name] != None:
            base_th = self.places_absolute[self.items_hosts_dict[pt_name]]['theta']

        # self.logger.info(f"Updated {pt_name}: {self.places_absolute[pt_name]} / {pan}")

        abs_pt_theta = self.places_relative[pt_name]['theta'] + pan + base_th
        if pt_name in self.tree: # if pan-tilt has anything on it
            for i in self.tree[pt_name]:
                if self.places_absolute[i]['theta'] != None:
                    self.places_absolute[i]['theta'] = \
                        self.places_relative[i]['theta'] + \
                        abs_pt_theta
                    # self.logger.info(f"Updated {i}: {self.places_absolute[i]}")

    def pan_tilt_callback(self, message, meta):
        self.pantilts[message['name']]['pan'] = message['pan']
        self.update_pan_tilt(message['name'], message['pan'])

    # {
    #     'type', 'subtype', 'name', 'pose', 'base_topic', 'range', 'fov', \
    #      'host', 'host_type'
    # }
    def declare_callback(self, message, meta):
        m = message

        # sanity checks
        temp = {}
        for t in self.declare_rpc_input:
            temp[t] = None
        for m in message:
            if m not in temp:
                self.logger.error(f"tf: Invalid declaration field for {message['name']}: {m}")
                return {}
            temp[m] = message[m]

        host_msg = ""
        if 'host' in message:
            host_msg = f"on {message['host']}"

        if 'host_type' in message:
            if message['host_type'] not in ['robot', 'pan_tilt']:
                self.logger.error(f"tf: Invalid host type for {message['name']}: {message['host_type']}")

        self.logger.info(f"{Style.DIM}{temp['name']}::{temp['type']}::{temp['subtype']} @ {temp['pose']} {host_msg}{Style.RESET_ALL}")

        # Fix thetas if exist:
        if temp['pose']['theta'] != None:
            temp['pose']['theta'] *= math.pi/180.0

        self.declarations.append(temp)
        self.declarations_info[temp['name']] = temp

        # Per type storage
        self.per_type_storage(temp)
        return {}

    # https://jsonformatter.org/yaml-formatter/a56cff
    def per_type_storage(self, d):
        type = d['type']
        sub = d['subtype']

        if d['name'] in self.names:
            self.logger.error(f"Name {d['name']} already exists. {d['base_topic']}")
        else:
            self.names.append(d['name'])

        if type == 'actor':
            self.per_type[type][sub].append(d['name'])
        elif type == "env":
            subclass = sub['subclass'][0]
            category = sub['category']
            self.per_type[type][category][subclass].append(d['name'])

            if subclass in ["thermostat", "humidifier"]:
                self.effectors_get_rpcs[d['name']] = CommlibFactory.getRPCClient(
                    rpc_name = d['base_topic'] + ".get"
                )

        elif type == "robot":
            subclass = sub['subclass'][0]
            category = sub['category']
            cls = sub['class']
            if cls in ["imu", "button", "env", "encoder", "twist", "line_follow"]:
                self.per_type[type][category][cls].append(d['name'])
            else:
                self.per_type[type][category][subclass].append(d['name'])

    def get_affections_callback(self, message, meta):
        try:
            return self.check_affectability(message['name'])
        except Exception as e:
            self.logger.error(f"Error in get affections callback: {str(e)}")
            return {}

    def check_distance(self, xy, aff):
        pl_aff = self.places_absolute[aff]
        xyt = [pl_aff['x'], pl_aff['y']]
        d = math.sqrt((xy[0] - xyt[0])**2 + (xy[1] - xyt[1])**2)
        return {
            'distance': d,
            'properties': self.declarations_info[aff]["properties"]
        }

    def handle_affection_ranged(self, xy, f, type):
        dd = self.check_distance(xy, f)
        d = dd['distance']
        # print(self.declarations_info[f])
        if d < self.declarations_info[f]['range']: # range is fire's
            if self.declarations_info[f]["properties"] == None:
                self.declarations_info[f]["properties"] = {}
            return {
                'type': type,
                'info': self.declarations_info[f]["properties"],
                'distance': d,
                'range': self.declarations_info[f]['range']
            }
        return None

    def handle_affection_arced(self, name, f, type):
        p_d = self.places_absolute[name]
        p_f = self.places_absolute[f]
        d = math.sqrt((p_d['x'] - p_f['x'])**2 + (p_d['y'] - p_f['y'])**2)
        # print(name, p_d, p_f, d)
        if d < self.declarations_info[name]['range']: # range of arced sensor
            # Check if in specific arc
            fov = self.declarations_info[name]["properties"]["fov"] / 180.0 * math.pi
            min_a = p_d['theta'] - fov / 2
            max_a = p_d['theta'] + fov / 2
            f_ang = math.atan2(p_f['y'] - p_d['y'], p_f['x'] - p_d['x'])
            # print(min_a, max_a, f_ang)
            ok = False
            ang = None
            if min_a < f_ang and f_ang < max_a:
                ok = True
                ang = f_ang
            elif min_a < (f_ang + 2 * math.pi) and (f_ang + 2 * math.pi) < max_a:
                ok = True
                ang = f_ang + 2 * math.pi
            elif min_a < (f_ang - 2 * math.pi) and (f_ang - 2 * math.pi) < max_a:
                ok = True
                ang = f_ang + 2 * math.pi

            if ok:
                return {
                    'type': type,
                    'info': self.declarations_info[f]["properties"],
                    'distance': d,
                    'min_sensor_ang': min_a,
                    'max_sensor_ang': max_a,
                    'actor_ang': ang,
                }

        return None

    # Affected by thermostats and fires
    def handle_env_sensor_temperature(self, name):
        try:
            ret = {}
            pl = self.places_absolute[name]
            x_y = [pl['x'], pl['y']]

            for f in self.per_type['env']['actuator']['thermostat']:
                r = self.handle_affection_ranged(x_y, f, 'thermostat')
                if r != None:
                    th_t = self.effectors_get_rpcs[f].call({})
                    r['info']['temperature'] = th_t['temperature']
                    ret[f] = r
            for f in self.per_type['actor']['fire']:
                r = self.handle_affection_ranged(x_y, f, 'fire')
                if r != None:
                    ret[f] = r
        except Exception as e:
            self.logger.error(str(e))
            raise Exception(str(e))

        return ret

    # Affected by humidifiers and water sources
    def handle_env_sensor_humidity(self, name):
        try:
            ret = {}
            pl = self.places_absolute[name]
            x_y = [pl['x'], pl['y']]

            for f in self.per_type['env']['actuator']['humidifier']:
                r = self.handle_affection_ranged(x_y, f, 'humidifier')
                if r != None:
                    th_t = self.effectors_get_rpcs[f].call({})
                    r['info']['humidity'] = th_t['humidity']
                    ret[f] = r
            for f in self.per_type['actor']['water']:
                r = self.handle_affection_ranged(x_y, f, 'water')
                if r != None:
                    ret[f] = r
        except Exception as e:
            self.logger.error(str(e))
            raise Exception(str(e))

        return ret

    # Affected by humans, fire
    def handle_env_sensor_gas(self, name):
        try:
            ret = {}
            pl = self.places_absolute[name]
            x_y = [pl['x'], pl['y']]

            # - env actuator thermostat
            for f in self.per_type['actor']['human']:
                r = self.handle_affection_ranged(x_y, f, 'human')
                if r != None:
                    ret[f] = r
            # - env actor fire
            for f in self.per_type['actor']['fire']:
                r = self.handle_affection_ranged(x_y, f, 'fire')
                if r != None:
                    ret[f] = r
        except Exception as e:
            self.logger.error(str(e))
            raise Exception(str(e))

        return ret

    # Affected by humans with sound, sound sources, speakers (when playing smth),
    # robots (when moving)
    def handle_sensor_microphone(self, name):
        try:
            ret = {}
            pl = self.places_absolute[name]
            x_y = [pl['x'], pl['y']]

            # - actor human
            for f in self.per_type['actor']['human']:
                if self.declarations_info[f]['properties']['sound'] == 1:
                    r = self.handle_affection_ranged(x_y, f, 'human')
                    if r != None:
                        ret[f] = r
            # - actor sound sources
            for f in self.per_type['actor']['sound_source']:
                r = self.handle_affection_ranged(x_y, f, 'sound_source')
                if r != None:
                    ret[f] = r
        except Exception as e:
            self.logger.error(str(e))
            raise Exception(str(e))

        return ret

    # Affected by barcode, color, human, qr, text
    def handle_sensor_camera(self, name):
        try:
            ret = {}
            pl = self.places_absolute[name]
            x_y = [pl['x'], pl['y']]
            th = pl['theta']

            # - actor human
            for f in self.per_type['actor']['human']:
                r = self.handle_affection_arced(name, f, 'human')
                if r != None:
                    ret[f] = r
            # - actor qr
            for f in self.per_type['actor']['qr']:
                r = self.handle_affection_arced(name, f, 'qr')
                if r != None:
                    ret[f] = r
            # - actor barcode
            for f in self.per_type['actor']['barcode']:
                r = self.handle_affection_arced(name, f, 'barcode')
                if r != None:
                    ret[f] = r
            # - actor color
            for f in self.per_type['actor']['color']:
                r = self.handle_affection_arced(name, f, 'color')
                if r != None:
                    ret[f] = r
            # - actor text
            for f in self.per_type['actor']['text']:
                r = self.handle_affection_arced(name, f, 'text')
                if r != None:
                    ret[f] = r

        except Exception as e:
            self.logger.error(str(e))
            raise Exception(str(e))

        return ret

    def check_affectability(self, name):
        try:
            type = self.declarations_info[name]['type']
            subt = self.declarations_info[name]['subtype']
        except Exception as e:
            raise Exception(f"{name} not in devices")

        try:
            ret = {}
            if type == "env":
                if 'temperature' in subt['subclass']:
                    ret = self.handle_env_sensor_temperature(name)
                if 'humidity' in subt['subclass']:
                    ret = self.handle_env_sensor_humidity(name)
                if 'gas' in subt['subclass']:
                    ret = self.handle_env_sensor_gas(name)
                if 'microphone' in subt['subclass']:
                    ret = self.handle_sensor_microphone(name)
                if 'camera' in subt['subclass']:
                    ret = self.handle_sensor_camera(name)
            elif type == "robot":
                if 'microphone' in subt['subclass']:
                    ret = self.handle_sensor_microphone(name)
                if 'camera' in subt['subclass']:
                    ret = self.handle_sensor_camera(name)
        except Exception as e:
            raise Exception(f"Error in device handling: {str(e)}")

        return ret

    def get_sim_detection_callback(self, message, meta):
        try:
            name = message['name']
            type = message['type']
            decl = self.declarations_info[name]
        except Exception as e:
            raise Exception(f"{name} not in devices")

        if decl['subtype']['subclass'][0] not in ['camera', 'microphone']:
            return {
                "result": False,
                "info": "Wrong detection device. Not microphone nor camera."
            }

        decision = False
        info = None
        frm = None

        if decl['subtype']['subclass'][0] == "microphone":
            # possible types: sound, language, emotion, speech2text
            ret = self.check_affectability(name)
            if type == "sound":
                decision = True
                info = None
                frm = ret
            elif type == "language":
                decision = True
                for x in ret:
                    info = ret[x]['info']['language'] # gets the last one
                    frm = ret[x]
            elif type == "emotion":
                decision = True
                for x in ret:
                    info = ret[x]['info']['emotion'] # gets the last one
                    frm = ret[x]
            elif type == "speech2text":
                decision = True
                for x in ret:
                    info = ret[x]['info']['speech'] # gets the last one
                    frm = ret[x]
                if info == "":
                    decision = False
            else:
                self.logger.error(f"Wrong detection type: {type}")

        else: # possible types: face, qr, barcode, gender, age, color, motion, emotion
            pass

        return {
            "result": decision,
            "info": info,
            "frm": frm
        }
