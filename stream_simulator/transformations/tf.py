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

from stream_simulator.connectivity import CommlibFactory

class TfController:
    def __init__(self, base = None, resolution = None, logger = None):
        self.logger = logging.getLogger(__name__) if logger is None else logger
        self.base_topic = base + ".tf" if base is not None else "streamsim.tf"
        self.base = base
        self.resolution = resolution

        self.commlib_factory = CommlibFactory(node_name = "Tf")
        self.commlib_factory.run()
        
        self.lin_alarms_robots = {}

        self.declare_rpc_server = self.commlib_factory.getRPCService(
            callback = self.declare_callback,
            rpc_name = self.base_topic + ".declare"
        )

        self.get_declarations_rpc_server = self.commlib_factory.getRPCService(
            callback = self.get_declarations_callback,
            rpc_name = self.base_topic + ".get_declarations"
        )

        self.get_tf_rpc_server = self.commlib_factory.getRPCService(
            callback = self.get_tf_callback,
            rpc_name = self.base_topic + ".get_tf"
        )

        self.get_affectability_rpc_server = self.commlib_factory.getRPCService(
            callback = self.get_affections_callback,
            rpc_name = self.base_topic + ".get_affections"
        )

        self.get_sim_detection_rpc_server = self.commlib_factory.getRPCService(
            callback = self.get_sim_detection_callback,
            rpc_name = self.base_topic + ".simulated_detection"
        )

        self.detections_publisher = self.commlib_factory.getPublisher(
            topic = self.base_topic + ".detections.notify"
        )

        self.declare_rpc_input = [
            'type', 'subtype', 'name', 'pose', 'base_topic', 'range', 'fov', \
            'host', 'host_type', 'properties', 'id'
        ]

        self.declarations = []
        self.declarations_info = {}
        self.names = []

        self.effectors_get_rpcs = {}

        self.subs = {} # Filled
        self.places_relative = {}
        self.places_absolute = {}
        self.tree = {} # filled
        self.items_hosts_dict = {}
        self.existing_hosts = []
        self.pantilts = {}
        self.robots = []

        self.speaker_subs = {}
        self.microphone_pubs = {}

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

    # def start(self):
    #     self.declare_rpc_server.run()

    # def stop(self):
    #     self.declare_rpc_server.stop()

    def get_declarations_callback(self, message):
        return {"declarations": self.declarations}

    def get_tf_callback(self, message):
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
        # self.logger.info("*************** TF setup ***************")

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
                    self.places_relative[d['name']][i] #*= self.resolution
                    self.places_absolute[d['name']][i] #*= self.resolution

            # if d['range'] != None:
            #     d['range'] *= self.resolution

        # Get all devices and check pan-tilts exist
        get_devices_rpc = self.commlib_factory.getRPCClient(
            rpc_name = self.base + ".get_device_groups"
        )
        res = get_devices_rpc.call({})

        # Pan tilts on robots
        for r in res['robots']:
            cl = self.commlib_factory.getRPCClient(
                rpc_name = f"{self.base}.{r}.nodes_detector.get_connected_devices"
            )
            rr = cl.call({})
            self.logger.info(f"Devices in {r}: {len(rr['devices'])}")
            for d in rr['devices']:
                if d['type'] == 'PAN_TILT':
                    self.pantilts[d['name']] = {
                        'base_topic': d['base_topic'],
                        'place': d['categorization']['place'],
                        'pan': 0.0
                    }

        # Pan tilts in environment
        cl = self.commlib_factory.getRPCClient(
            rpc_name = f"{self.base}.{res['world']}.nodes_detector.get_connected_devices"
        )
        rr = cl.call({})
        self.logger.info(f"Devices in world: {len(rr['devices'])}")
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
            self.subs[p] = self.commlib_factory.getSubscriber(
                topic = topic,
                callback = self.pan_tilt_callback
            )

        # Gather robots and create subscribers
        for d in self.declarations:
            if d['host_type'] == "robot":
                if d['host'] not in self.existing_hosts:
                    self.robots.append(d['host'])
                    self.existing_hosts.append(d['host'])

                    topic = d['host_type'] + "." + d["host"] + ".pose.internal"
                    self.subs[d['host']] = self.commlib_factory.getSubscriber(
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

        for n in self.declarations_info:
            d_i = self.declarations_info[n]
            if d_i["type"] == "actor":
                continue

            # subscribers for speakers
            if "speaker" in d_i['subtype']['subclass']:
                self.speaker_subs[d_i['name']] = self.commlib_factory.getSubscriber(
                    topic = d_i["base_topic"] + ".speak.notify",
                    callback = self.speak_callback
                )
            # publishers for microphones
            if "microphone" in d_i['subtype']['subclass']:
                self.microphone_pubs[d_i['name']] = self.commlib_factory.getPublisher(
                    topic = d_i["base_topic"] + ".speech_detected"
                )
        # self.logger.info("*************** TF setup end ***************")

    def speak_callback(self, message):
        # {'text': 'This is an example', 'volume': 100, 'language': 'el', 'speaker': 'speaker_X'}
        name = message['speaker']
        pose = self.places_absolute[name]

        # search all microphones:
        for n in self.declarations_info:
            if self.declarations_info[n]['type'] == "actor":
                continue
            if "microphone" in self.declarations_info[n]['subtype']['subclass']:
                # check distance
                m_name = n
                m_pose = self.places_absolute[m_name]

                xy = [pose['x'], pose['y']]
                m_xy = [m_pose['x'], m_pose['y']]
                d = self.calc_distance(xy, m_xy)
                # print(d)

                # lets say 4 meters
                if d < 4.0:
                    self.microphone_pubs[m_name].publish({
                        'speaker': name,
                        'text': message['text'],
                        'language': message['language']
                    })

    def robot_pose_callback(self, message):
        nm = message['name'].split(".")[-1]
        print(f"Updating {nm}: {message}")
        if nm not in self.places_absolute:
            self.places_absolute[nm] = {'x': 0, 'y': 0, 'theta': 0}
        self.places_absolute[nm]['x'] = message['x']
        self.places_absolute[nm]['y'] = message['y']
        self.places_absolute[nm]['theta'] = message['theta']

        self.commlib_factory.notify_ui(
            type = "robot_pose",
            data = {
                "name": nm,
                "x": message['x'],
                "y": message['y'],
                "theta": message['theta']
            }
        )


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

                    self.commlib_factory.notify.publish({
                        'type': 'sensor_pose',
                        'data': {
                            "name": i,
                            "x": self.places_absolute[i]['x'],
                            "y": self.places_absolute[i]['y'],
                            "theta": self.places_absolute[i]['theta']
                        }
                    })

    def pan_tilt_callback(self, message):
        self.pantilts[message['name']]['pan'] = message['pan']
        self.update_pan_tilt(message['name'], message['pan'])

    # {
    #     'type', 'subtype', 'name', 'pose', 'base_topic', 'range', 'fov', \
    #      'host', 'host_type'
    # }
    def declare_callback(self, message):
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

        self.logger.info(f"TF declaration: {temp['name']}::{temp['type']}::{temp['subtype']}\n\t @ {temp['pose']} {host_msg}")

        # Fix thetas if exist:
        if temp['pose']['theta'] != None:
            temp['pose']['theta'] = float(temp['pose']['theta'])
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

            if subclass in ["thermostat", "humidifier", "leds"]:
                self.effectors_get_rpcs[d['name']] = self.commlib_factory.getRPCClient(
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

    def get_affections_callback(self, message):
        try:
            return self.check_affectability(message['name'])
        except Exception as e:
            self.logger.error(f"Error in get affections callback: {str(e)}")
            return {}

    def check_lines_orientation(self, p, q, r):
        val = (float(q[1] - p[1]) * (r[0] - q[0])) - \
            (float(q[0] - p[0]) * (r[1] - q[1]))
        if (val > 0):
            # Clockwise orientation
            return 1
        elif (val < 0):
            # Counterclockwise orientation
            return 2
        else:
            # Colinear orientation
            return 0

    def check_lines_on_segment(self, p, q, r):
        if ( (q[0] <= max(p[0], r[0])) and (q[0] >= min(p[0], r[0])) and
               (q[1] <= max(p[1], r[1])) and (q[1] >= min(p[1], r[1]))):
            return True
        return False

    def check_lines_intersection(self, p1, q1, p2, q2):
        # Find the 4 orientations required for
        # the general and special cases
        o1 = self.check_lines_orientation(p1, q1, p2)
        o2 = self.check_lines_orientation(p1, q1, q2)
        o3 = self.check_lines_orientation(p2, q2, p1)
        o4 = self.check_lines_orientation(p2, q2, q1)
        # General case
        if ((o1 != o2) and (o3 != o4)):
            return True
        # Special Cases
        # p1 , q1 and p2 are colinear and p2 lies on segment p1q1
        if ((o1 == 0) and self.check_lines_on_segment(p1, p2, q1)):
            return True
        # p1 , q1 and q2 are colinear and q2 lies on segment p1q1
        if ((o2 == 0) and self.check_lines_on_segment(p1, q2, q1)):
            return True
        # p2 , q2 and p1 are colinear and p1 lies on segment p2q2
        if ((o3 == 0) and self.check_lines_on_segment(p2, p1, q2)):
            return True
        # p2 , q2 and q1 are colinear and q1 lies on segment p2q2
        if ((o4 == 0) and self.check_lines_on_segment(p2, q1, q2)):
            return True
        # If none of the cases
        return False

    def calc_distance(self, p1, p2):
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    def check_distance(self, xy, aff):
        pl_aff = self.places_absolute[aff]
        xyt = [pl_aff['x'], pl_aff['y']]
        d = self.calc_distance(xy, xyt)
        # d = math.sqrt((xy[0] - xyt[0])**2 + (xy[1] - xyt[1])**2)
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
                'range': self.declarations_info[f]['range'],
                'name': self.declarations_info[f]['name'],
                'id': self.declarations_info[f]['id']
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
                props = None
                if type == "robot":
                    props = f
                    name = f
                    id = None
                else:
                    props = self.declarations_info[f]["properties"]
                    name = self.declarations_info[f]['name']
                    id = self.declarations_info[f]['id']
                return {
                    'type': type,
                    'info': props,
                    'distance': d,
                    'min_sensor_ang': min_a,
                    'max_sensor_ang': max_a,
                    'actor_ang': ang,
                    'name': name,
                    'id': id
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
    def handle_env_sensor_gas(self, name, robot = None):
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

    # Affected by light, fire
    def handle_env_light_sensor(self, name):
        try:
            ret = {}
            pl = self.places_absolute[name]
            x_y = [pl['x'], pl['y']]

            # - env light
            for f in self.per_type['env']['actuator']['leds']:
                r = self.handle_affection_ranged(x_y, f, 'light')
                if r != None:
                    th_t = self.effectors_get_rpcs[f].call({})
                    ret[f] = r
            # - actor fire
            for f in self.per_type['actor']['fire']:
                r = self.handle_affection_ranged(x_y, f, 'fire')
                if r != None:
                    ret[f] = r
        except Exception as e:
            self.logger.error(str(e))
            raise Exception(str(e))

        return ret

    # Affected by barcode, color, human, qr, text
    def handle_sensor_camera(self, name, with_robots = False):
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

            # check all robots
            if with_robots:
                for rob in self.robots:
                    r = self.handle_affection_arced(name, rob, 'robot')
                    if r != None:
                        ret[rob] = r

        except Exception as e:
            self.logger.error("handle_sensor_camera:" + str(e))
            raise Exception(str(e))

        return ret

    # Affected by rfid_tags
    def handle_sensor_rfid_reader(self, name):
        try:
            ret = {}
            pl = self.places_absolute[name]
            x_y = [pl['x'], pl['y']]
            th = pl['theta']

            # - actor human
            for f in self.per_type['actor']['rfid_tag']:
                r = self.handle_affection_arced(name, f, 'rfid_tag')
                if r != None:
                    ret[f] = r

        except Exception as e:
            self.logger.error(str(e))
            raise Exception(str(e))

        return ret

    # Affected by robots
    def handle_area_alarm(self, name):
        try:
            ret = {}
            pl = self.places_absolute[name]
            xy = [pl['x'], pl['y']]
            th = pl['theta']
            range = self.declarations_info[name]['range']

            # Check all robots if in there
            for r in self.robots:
                pl_aff = self.places_absolute[r]
                xyt = [pl_aff['x'], pl_aff['y']]
                d = math.sqrt((xy[0] - xyt[0])**2 + (xy[1] - xyt[1])**2)
                if d < range:
                    ret[r] = {
                        "distance": d,
                        "range": range
                    }

        except Exception as e:
            self.logger.error(str(e))
            raise Exception(str(e))

        return ret

    # Affected by robots
    def handle_env_distance(self, name):
        try:
            ret = {}

            pl = self.places_absolute[name]
            xy = [pl['x'], pl['y']]
            th = pl['theta']
            range = self.declarations_info[name]['range']

            # Check all robots if in there
            for r in self.robots:
                pl_aff = self.places_absolute[r]
                xyt = [pl_aff['x'], pl_aff['y']]
                d = math.sqrt((xy[0] - xyt[0])**2 + (xy[1] - xyt[1])**2)
                if d < range:
                    ret[r] = {
                        "distance": d,
                        "range": range
                    }

        except Exception as e:
            self.logger.error(str(e))
            raise Exception(str(e))

        return ret

    # Affected by robots
    def handle_linear_alarm(self, name):
        try:
            lin_start = self.declarations_info[name]['pose']['start']
            lin_end = self.declarations_info[name]['pose']['end']
            sta = [
                lin_start['x'], #* self.resolution
                lin_start['y'] #* self.resolution
            ]
            end = [
                lin_end['x'], #* self.resolution
                lin_end['y'] #* self.resolution
            ]
            inter = self.calc_distance(sta, end)
            ret = {}

            # Check all robots
            for r in self.robots:
                pl_aff = self.places_absolute[r]
                xyt = [pl_aff['x'], pl_aff['y']]

                if r not in self.lin_alarms_robots:
                    self.lin_alarms_robots[r] = {
                        "prev": xyt,
                        "curr": xyt
                    }

                self.lin_alarms_robots[r]["prev"] = \
                    self.lin_alarms_robots[r]["curr"]

                self.lin_alarms_robots[r]["curr"] = xyt

                intersection = self.check_lines_intersection(sta, end, \
                    self.lin_alarms_robots[r]["curr"],
                    self.lin_alarms_robots[r]["prev"]
                )
                # print(sta, end, "||", self.lin_alarms_robots[r]["curr"], \
                #     self.lin_alarms_robots[r]["prev"], "||", intersection)

                if intersection == True:
                    ret[r] = intersection

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
                if 'area_alarm' in subt['subclass']:
                    ret = self.handle_area_alarm(name)
                if 'linear_alarm' in subt['subclass']:
                    ret = self.handle_linear_alarm(name)
                if 'sonar' in subt['subclass']:
                    ret = self.handle_env_distance(name)
                if 'light_sensor' in subt['subclass']:
                    ret = self.handle_env_light_sensor(name)
            elif type == "robot":
                if 'microphone' in subt['subclass']:
                    ret = self.handle_sensor_microphone(name)
                if 'camera' in subt['subclass']:
                    ret = self.handle_sensor_camera(name)
                if 'rfid_reader' in subt['subclass']:
                    ret = self.handle_sensor_rfid_reader(name)
                if 'temp_hum_pressure_gas' in subt['subclass']:
                    ret = {
                        'temperature': self.handle_env_sensor_temperature(name),
                        'humidity': self.handle_env_sensor_humidity(name),
                        'gas': self.handle_env_sensor_gas(name)
                    }
        except Exception as e:
            raise Exception(f"Error in device handling: {str(e)}")

        return ret

    def get_sim_detection_callback(self, message):
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

        import string
        id = ''.join(random.choices(string.ascii_uppercase + string.digits, k = 6))
        self.detections_publisher.publish({
            "name": name,
            "device_type": decl['subtype']['subclass'][0],
            "type": type,
            "id": id,
            "state": "start",
            "result": None
        })

        decision = False
        info = None
        frm = None

        if decl['subtype']['subclass'][0] == "microphone":
            # possible types: sound, language, emotion, speech2text
            ret = self.check_affectability(name)
            decision = False
            info = ""
            frm = ret
            print(message)
            print("===============", ret)

            if type == "sound":
                if ret != None:
                    if len(ret) >= 1:
                        for ff in ret:
                            decision = True
                            info = ret[ff]['info']['sound']
                            frm = ret[ff]
            elif type == "language":
                if ret != None:
                    if len(ret) >= 1:
                        for x in ret:
                            decision = True
                            info = ret[x]['info']['language'] # gets the last one
                            frm = ret[x]
            elif type == "emotion":
                if ret != None:
                    if len(ret) >= 1:
                        for x in ret:
                            decision = True
                            info = ret[x]['info']['emotion'] # gets the last one
                            frm = ret[x]
            elif type == "speech2text":
                if ret != None:
                    if len(ret) >= 1:
                        for x in ret:
                            if ret[x]['type'] == 'human':
                                decision = True
                                info = ret[x]['info']['speech']
                                frm = ret[x]
                if info == "":
                    decision = False
            else:
                self.logger.error(f"Wrong detection type: {type}")

        elif decl['subtype']['subclass'][0] == "camera":
            # possible types: face, qr, barcode, gender, age, motion, color, emotion
            ret = self.handle_sensor_camera(name, with_robots = True)

            # experimental
            amb_luminosity = self.declarations_info[name]['properties']['ambient_luminosity']
            res = self.handle_env_light_sensor(name) # just to get the sources

            lum = amb_luminosity
            add_lum = 0
            for a in res:
                rel_range = (1 - res[a]['distance'] / res[a]['range'])
                if res[a]['type'] == 'fire':
                    # assumed 100% luminosity there
                    add_lum += 100 * rel_range
                elif res[a]['type'] == "light":
                    add_lum += rel_range * res[a]['info']['luminosity']

            if add_lum < lum:
                lum = add_lum * 0.1 + lum
            else:
                lum = lum * 0.1 + add_lum

            if lum > 100:
                lum = 100

            lum = lum / 100.0

            if type == "face":
                for x in ret:
                    if ret[x]['type'] == 'human': # gets the last one
                        decision = True
                        info = "" # no info, just a face
                        frm = ret[x]
            elif type == "gender":
                for x in ret:
                    if ret[x]['type'] == 'human' and ret[x]['info']['gender'] != "none": # gets the last one
                        decision = True
                        info = ret[x]['info']['gender']
                        frm = ret[x]
            elif type == "age":
                for x in ret:
                    if ret[x]['type'] == 'human' and ret[x]['info']['age'] != -1: # gets the last one
                        decision = True
                        info = ret[x]['info']['age']
                        frm = ret[x]
            elif type == "emotion":
                for x in ret:
                    if ret[x]['type'] == 'human': # gets the last one
                        decision = True
                        info = ret[x]['info']['emotion']
                        frm = ret[x]
            elif type == "motion":
                for x in ret:
                    if ret[x]['type'] == 'human' and ret[x]['info']['motion'] == 1: # gets the last one
                        decision = True
                        info = ""
                        frm = ret[x]
            elif type == "qr":
                for x in ret:
                    if ret[x]['type'] == 'qr':
                        decision = True
                        info = ret[x]['info']['message']
                        frm = ret[x]
            elif type == "barcode":
                for x in ret:
                    if ret[x]['type'] == 'barcode':
                        decision = True
                        info = ret[x]['info']['message']
                        frm = ret[x]
            elif type == "text":
                for x in ret:
                    if ret[x]['type'] == 'text':
                        decision = True
                        info = ret[x]['info']['text']
                        frm = ret[x]
            elif type == "color":
                # {'result': True, 'info': {'r': 0, 'g': 255, 'b': 0}, 'frm': {'type': 'color', 'info': {'r': 0, 'g': 255, 'b': 0}, 'distance': 2.5, 'min_sensor_ang': 1.4613539971898075, 'max_sensor_ang': 2.5085515483864054, 'actor_ang': 2.498091544796509}}

                if len(ret) == 0:
                    info = {'r': 0, 'g': 0, 'b': 0}
                    frm = None
                for x in ret:
                    if ret[x]['type'] == 'color':
                        decision = True
                        info = ret[x]['info']
                        frm = ret[x]
            elif type == "robot":
                for x in ret:
                    if ret[x]['type'] == 'robot':
                        decision = True
                        info = ret[x]['info']
                        frm = ret[x]
            else:
                self.logger.error(f"Wrong detection type: {type}")


            if decision == True:
                roulette = random.uniform(0, 1)
                if math.pow(roulette, 2) > lum:
                    self.logger.warning("Camera detection: too dark")
                    decision = False

        else: # possible types: face, qr, barcode, gender, age, color, motion, emotion
            pass

        self.detections_publisher.publish({
            "name": name,
            "device_type": decl['subtype']['subclass'][0],
            "type": type,
            "id": id,
            "state": "end",
            "result": decision
        })

        self.commlib_factory.notify.publish({
            "type": "detection",
            "data": {
                "name": name,
                "device_type": decl['subtype']['subclass'][0],
                "type": type,
                "id": id,
                "state": "end",
                "result": decision,
                "info": info,
                "frm": frm
            }
        })

        return {
            "result": decision,
            "info": info,
            "frm": frm
        }
    
    def stop(self):
        self.commlib_factory.stop()