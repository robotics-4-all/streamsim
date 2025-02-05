"""
File that contains the TfController class.
"""

#!/usr/bin/python
# -*- coding: utf-8 -*-

import math
import logging
import random
import string

from stream_simulator.connectivity import CommlibFactory
from stream_simulator.transformations.check_lines_intersection import check_lines_intersection
from stream_simulator.transformations.calc_distance import calc_distance

class TfController:
    """
    A class to handle transformations for the simulator.
    """
    def __init__(self, logger = None, mqtt_notifier = None):
        self.logger = logging.getLogger(__name__) if logger is None else logger
        self.base_topic = None
        self.base = None
        self.resolution = None
        self.mqtt_notifier = mqtt_notifier
        self.commlib_factory = None
        self.lin_alarms_robots = {}
        self.env_properties = None
        self.declare_rpc_server = None
        self.get_declarations_rpc_server = None
        self.get_tf_rpc_server = None
        self.get_affectability_rpc_server = None
        self.get_sim_detection_rpc_server = None
        self.get_luminosity_rpc_server = None
        self.distance_calculator_rpc_server = None
        self.detections_publisher = None
        self.get_devices_rpc = None
        self.pan_tilts_rpc = None
        self.declare_rpc_input = [
            'type', 'subtype', 'name', 'pose', 'base_topic', 'range', 'fov', \
            'host', 'host_type', 'properties', 'id', 'namespace'
        ]

        self.declarations = []
        self.declarations_info = {}
        self.names = []

        self.effectors_get_rpcs = {}
        self.robots_get_devices_rpcs = {}

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

    def set_env_properties(self, env_properties):
        """
        Set the environmental properties for the transformation module.
        """
        self.env_properties = env_properties
        # self.logger.info("TF set environmental variables: %s", self.env_properties)

    def initialize(self, base = None, resolution = None, env_properties = None, ):
        """
        Initialize the transformation module with the given parameters.
        """

        self.base_topic = base + ".tf" if base is not None else "streamsim.tf"
        self.base = base
        self.resolution = resolution

        self.commlib_factory = CommlibFactory(node_name = "Tf")

        self.lin_alarms_robots = {}
        self.env_properties = env_properties
        self.logger.info("TF set environmental variables: %s", self.env_properties)

        self.declare_rpc_server = self.commlib_factory.get_rpc_service(
            callback = self.declare_callback,
            rpc_name = self.base_topic + ".declare",
            auto_run = False,
        )

        self.get_declarations_rpc_server = self.commlib_factory.get_rpc_service(
            callback = self.get_declarations_callback,
            rpc_name = self.base_topic + ".get_declarations",
            auto_run = False,
        )

        self.get_tf_rpc_server = self.commlib_factory.get_rpc_service(
            callback = self.get_tf_callback,
            rpc_name = self.base_topic + ".get_tf",
            auto_run = False,
        )

        self.get_affectability_rpc_server = self.commlib_factory.get_rpc_service(
            callback = self.get_affections_callback,
            rpc_name = self.base_topic + ".get_affections",
            auto_run = False,
        )

        self.get_sim_detection_rpc_server = self.commlib_factory.get_rpc_service(
            callback = self.get_sim_detection_callback,
            rpc_name = self.base_topic + ".simulated_detection",
            auto_run = False,
        )

        self.get_luminosity_rpc_server = self.commlib_factory.get_rpc_service(
            callback = self.get_luminosity_callback,
            rpc_name = self.base_topic + ".get_luminosity",
            auto_run = False,
        )

        self.detections_publisher = self.commlib_factory.get_publisher(
            topic = self.base_topic + ".detections.notify",
            auto_run = False,
        )

        self.distance_calculator_rpc_server = self.commlib_factory.get_rpc_service(
            callback = self.distance_calculator_callback,
            rpc_name = self.base_topic + ".distance_calculator",
            auto_run = False,
        )

        self.get_devices_rpc = self.commlib_factory.get_rpc_client(
            rpc_name = self.base + ".get_device_groups",
            auto_run = False,
        )

        self.pan_tilts_rpc = self.commlib_factory.get_rpc_client(
            rpc_name = f"{self.base}.nodes_detector.get_connected_devices",
            auto_run = False,
        )

        # Start the CommlibFactory
        self.commlib_factory.run()

        self.declarations = []
        self.declarations_info = {}
        self.names = []

        self.effectors_get_rpcs = {}
        self.robots_get_devices_rpcs = {}

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

    def distance_calculator_callback(self, message):
        """
        Callback function to calculate the distance between two points.

        Args:
            message (dict): A dictionary containing 'initiator' and 'target' keys, 
                            which represent the identifiers of the two points.

        Returns:
            dict: A dictionary containing the calculated distance with the key 'distance'.
                  If either the initiator or target is not found in `self.places_absolute`, 
                  returns {"distance": None}.
        """
        initiator = message['initiator']
        target = message['target']
        # find absolute positions
        if initiator not in self.places_absolute or target not in self.places_absolute:
            return {"distance": None}
        distance = calc_distance(
            [self.places_absolute[initiator]['x'], self.places_absolute[initiator]['y']],
            [self.places_absolute[target]['x'], self.places_absolute[target]['y']]
        )
        return {"distance": distance}

    def print_tf_tree(self):
        """
        Prints the transformation tree.

        This method iterates through the transformation tree and prints each node
        along with its corresponding places in an absolute format.

        The output format is:
        <node>:
            <child_node> @ <absolute_place>

        Example:
        root:
            child1 @ place1
            child2 @ place2
        """
        self.logger.info("Transformation tree:")
        visited = []
        tmp_tree = {"world": []}
        self.places_absolute["world"] = {'x': 0, 'y': 0, 'theta': 0}
        for h, item in self.tree.items():
            if h is None:
                tmp_tree["world"] += item
            elif h in self.robots:
                tmp_tree["world"] += [h]
                tmp_tree[h] = item
            else:
                tmp_tree[h] = item
        self.print_tf_tree_recursive(tmp_tree, "world", 0, visited)

    def print_tf_tree_recursive(self, tree, node, level, visited):
        """
        Prints the transformation tree recursively.

        This method iterates through the transformation tree and prints each node
        along with its corresponding places in an absolute format.

        The output format is:
        <node>:
            <child_node> @ <absolute_place>

        Example:
        root:
            child1 @ place1
            child2 @ place2

        Args:
            node (str): The current node in the tree.
            level (int): The level of the current node in the tree.
        """
        # We want only env devices and robots here
        # print(f"Checking {node}", node, node not in self.robots, self.robots, visited)
        if node in visited:
            return visited

        visited.append(node)
        if node not in tree:
            return visited
        tabs = "\t" * level
        self.logger.info("%s%s @ %s:", tabs, node, self.places_absolute[node])
        for c in tree[node]:
            tabs = "\t" * (level + 1)
            if c not in self.existing_hosts:
                self.logger.info("%s%s @ %s", tabs, c, self.places_absolute[c])
            visited = self.print_tf_tree_recursive(tree, c, level + 1, visited)
        return visited

    def get_declarations_callback(self, _):
        """
        Callback function to get the declarations.

        Args:
            message (Any): The message triggering the callback.

        Returns:
            dict: A dictionary containing the declarations.
        """
        return {"declarations": self.declarations}

    def get_tf_callback(self, message):
        """
        Retrieves the transformation callback for a given device based on the message.
        Args:
            message (dict): A dictionary containing the 'name' key which specifies the device name.
        Returns:
            dict: A dictionary representing the transformation of the device. If the device is 
            not found, an empty dictionary is returned. If the device is a robot, the absolute 
            position is returned.
            If the device is a pantilt, the pose is calculated based on the relative position and 
            pan angle. Otherwise, the absolute position is returned.
        Raises:
            None
        """
        name = message['name']
        if name not in self.items_hosts_dict:
            self.logger.error("TF: Requested transformation of missing device: %s", name)
            return {}

        if name in self.robots:
            return self.places_absolute[name]
        if name in self.pantilts:
            pose = self.places_absolute[name]
            base_th = 0
            if self.items_hosts_dict[name] is not None:
                base_th = self.places_absolute[self.items_hosts_dict[name]]['theta']
            pose['theta'] = self.places_relative[name]['theta'] + \
                self.pantilts[name]['pan'] + base_th
            return pose

        return self.places_absolute[name]

    def get_luminosity_callback(self, message):
        """
        Callback function to compute the luminosity for a given message.

        Args:
            message (dict): A dictionary containing the message data. 
                            It should have a key "name" which is used to compute the luminosity.

        Returns:
            dict: A dictionary containing the computed luminosity with the key "luminosity".
        """
        lum = self.compute_luminosity(message["name"], print_debug = False)
        return {"luminosity": lum}

    def setup(self):
        """
        Sets up the transformation framework by initializing and updating various
        dictionaries and lists that track the state and relationships of different
        devices and their poses.
        The setup process includes:
        - Logging the start of the setup process.
        - Filling the tree structure with device declarations.
        - Updating the items_hosts_dict with device names and their corresponding hosts.
        - Copying pose information to places_relative and places_absolute dictionaries.
        - Logging detected pan-tilts and adding them to the existing_hosts list.
        - Checking for None values in pan-tilt poses and logging errors if found.
        - Logging errors for missing hosts and their affected devices.
        - Updating poses based on the tree structure for pan-tilts and their devices.
        - Logging the updated poses for each device.
        Finally, logs the end of the setup process.
        """
        self.logger.info("*************** TF setup ***************")

        # Fill tree
        for d in self.declarations:
            # Update tree
            if d['host'] not in self.tree:
                self.tree[d['host']] = []
            self.tree[d['host']].append(d['name'])

            # Update items_hosts_dict
            self.items_hosts_dict[d['name']] = d['host']

            self.places_relative[d['name']] = d['pose'].copy()
            self.places_absolute[d['name']] = d['pose'].copy()

        self.logger.info("Pan tilts detected:")
        for p, pan_tilt in self.pantilts.items():
            self.logger.info("\t%s on %s", p, pan_tilt['place'])
            self.existing_hosts.append(p)

        # Check pan tilt poses for None
        for pt, _ in self.pantilts.items():
            for k in ['x', 'y', 'theta']:
                if self.places_relative[pt][k] is None:
                    self.logger.error("Pan-tilt %s has %s = None. Please fix it in yaml.", pt, k)

        for h, item in self.tree.items():
            if h not in self.existing_hosts and h is not None:
                self.logger.error("We have a missing host: %s", h)
                self.logger.error("\tAffected devices: %s", item)

        # update poses based on tree for pan-tilts
        for d in self.pantilts:
            if d in self.tree:  # We can have a pan-tilt with no devices on it
                for i in self.tree[d]:
                    # initial pan is considered 0
                    # print(f"Updating {i} on {d}")
                    # print(f"Initial: {self.places_absolute[i]}")
                    # print(f"Initial pt: {self.places_absolute[d]}")
                    pt_abs_pose = self.places_absolute[d]
                    self.places_absolute[i]['x'] += pt_abs_pose['x']
                    self.places_absolute[i]['y'] += pt_abs_pose['y']
                    if self.places_absolute[i]['theta'] is not None:
                        self.places_absolute[i]['theta'] += pt_abs_pose['theta']

                    self.logger.info("%s@%s:", i, d)
                    self.logger.info("\tPan-tilt: %s", self.places_absolute[d])
                    self.logger.info("\tRelative: %s", self.places_relative[i])
                    self.logger.info("\tAbsolute: %s", self.places_absolute[i])

        self.logger.info("*************** TF setup end ***************")

    def speak_callback(self, message):
        """
        Handles the callback for when a speaker speaks. It processes the message and publishes 
        it to the appropriate microphones
        if they are within a certain distance.
        Args:
            message (dict): A dictionary containing the following keys:
            - 'text' (str): The text message to be spoken.
            - 'volume' (int): The volume level of the speech.
            - 'language' (str): The language of the speech.
            - 'speaker' (str): The identifier of the speaker.
        The function performs the following steps:
            1. Retrieves the speaker's name and position.
            2. Iterates through all declared entities to find microphones.
            3. Checks the distance between the speaker and each microphone.
            4. If the distance is less than 4 meters, publishes the message to the microphone's 
            topic.
        """
        # {'text': 'This is an example', 'volume': 100, 'language': 'el', 'speaker': 'speaker_X'}
        name = message['speaker']
        pose = self.places_absolute[name]

        # search all microphones:
        for n, node in self.declarations_info.items():
            if node['type'] == "actor":
                continue
            if "microphone" in node['subtype']['subclass']:
                # check distance
                m_name = n
                m_pose = self.places_absolute[m_name]

                xy = [pose['x'], pose['y']]
                m_xy = [m_pose['x'], m_pose['y']]
                d = calc_distance(xy, m_xy)
                # print(d)

                # lets say 4 meters
                if d < 4.0:
                    self.microphone_pubs[m_name].publish({
                        'speaker': name,
                        'text': message['text'],
                        'language': message['language']
                    })

    def robot_pose_callback(self, message):
        """
        Callback function to handle updates to the robot's pose.
        This function updates the absolute positions and orientations of the robot
        and its associated devices based on the incoming message. It also notifies
        the UI about the updated robot pose and adjusts the positions and orientations
        of devices mounted on pan-tilt units.
        Args:
            message (dict): A dictionary containing the robot's pose information with keys:
                - 'name' (str): The name of the robot or device.
                - 'x' (float): The x-coordinate of the robot's position.
                - 'y' (float): The y-coordinate of the robot's position.
                - 'theta' (float): The orientation (theta) of the robot.
        Updates:
            self.places_absolute (dict): Updates the absolute positions and orientations
                of the robot and its associated devices.
            self.update_pan_tilt: Updates the angles of devices mounted on pan-tilt units.
        """
        nm = message['raw_name']
        if nm not in self.places_absolute:
            self.places_absolute[nm] = {'x': 0, 'y': 0, 'theta': 0}
        self.places_absolute[nm]['x'] = message['x']
        self.places_absolute[nm]['y'] = message['y']
        self.places_absolute[nm]['theta'] = message['theta']

        # Update all thetas of devices
        # NOTE: Check that this works!
        if nm not in self.tree:
            return

        for d in self.tree[nm]:
            if self.places_absolute[d]['theta'] is not None and d not in self.pantilts:
                self.places_absolute[d]['theta'] = \
                    self.places_absolute[nm]['theta'] + \
                    self.places_relative[d]['theta']
                # self.logger.info(f"Updated {d}: {self.places_absolute[d]['theta']}")

            self.places_absolute[d]['x'] = self.places_absolute[nm]['x']
            self.places_absolute[d]['y'] = self.places_absolute[nm]['y']

            # Just setting devs on pan tilts the robot's pose
            if d in self.pantilts:
                if d not in self.tree:
                    continue # no devices on this pan-tilt
                pt_devs = self.tree[d]
                for dev in pt_devs:
                    self.places_absolute[dev]['x'] = self.places_absolute[nm]['x']
                    self.places_absolute[dev]['y'] = self.places_absolute[nm]['y']
                # Updating the angle of objects on pan-tilt
                # self.logger.info(f"Updating pt {d} on {nm}")
                pan_now = self.pantilts[d]['pan']
                # self.logger.info(f"giving {pan_now}")
                self.update_pan_tilt(d, pan_now)

        # self.print_tf_tree()

    def update_pan_tilt(self, pt_name, pan):
        """
        Update the pan-tilt mechanism's absolute theta value and notify the UI.
        This method updates the absolute theta value of a pan-tilt mechanism based on its 
        relative theta, the provided pan value, and the base theta of its host (if any). 
        It also updates the absolute theta values of any items mounted on the pan-tilt mechanism 
        and notifies the UI of these changes.
        Args:
            pt_name (str): The name of the pan-tilt mechanism to update.
            pan (float): The pan value to add to the pan-tilt mechanism's relative theta.
        Returns:
            None
        """
        base_th = 0
        # If we are on a robot take its theta
        if self.items_hosts_dict[pt_name] is not None:
            base_th = self.places_absolute[self.items_hosts_dict[pt_name]]['theta']

        # self.logger.info(f"Updated {pt_name}: {self.places_absolute[pt_name]} / {pan}")

        abs_pt_theta = self.places_relative[pt_name]['theta'] + pan + base_th
        if pt_name in self.tree: # if pan-tilt has anything on it
            for i in self.tree[pt_name]:
                if self.places_absolute[i]['theta'] is not None:
                    self.places_absolute[i]['theta'] = \
                        self.places_relative[i]['theta'] + \
                        abs_pt_theta

                    self.mqtt_notifier.dispatch_sensor_pose({
                        "name": i,
                        "x": self.places_absolute[i]['x'],
                        "y": self.places_absolute[i]['y'],
                        "theta": self.places_absolute[i]['theta'],
                        "resolution": self.resolution
                    })

    def pan_tilt_callback(self, message):
        """
        Callback function to handle pan and tilt updates.

        Args:
            message (dict): A dictionary containing the following keys:
                - 'name' (str): The name identifier for the pan-tilt unit.
                - 'pan' (float): The new pan value to be set.

        Updates the internal pan value for the specified pan-tilt unit and calls
        the update_pan_tilt method to apply the change.
        """
        self.pantilts[message['name']]['pan'] = message['pan']
        self.update_pan_tilt(message['name'], message['pan'])
        # self.print_tf_tree()

    # {
    #     'type', 'subtype', 'name', 'pose', 'base_topic', 'range', 'fov', \
    #      'host', 'host_type'
    # }
    def declare_callback(self, message):
        """
        Handles the declaration callback by performing sanity checks, logging information,
        and storing the declaration details.
        Args:
            message (dict): The message containing declaration details.
        Returns:
            dict: An empty dictionary if the declaration is invalid, otherwise the processed
            declaration.
        """
        m = message

        # sanity checks
        temp = {}
        for t in self.declare_rpc_input:
            temp[t] = None
        for m in message:
            if m not in temp:
                self.logger.error("tf: Invalid declaration field for %s: %s", message['name'], m)
                return {}
            temp[m] = message[m]

        host_msg = ""
        if 'host' in message:
            host_msg = f"on {message['host']}"

        if 'host_type' in message:
            if message['host_type'] not in ['robot', 'pan_tilt']:
                self.logger.error("tf: Invalid host type for %s: %s", \
                    message['name'], message['host_type'])
        elif 'host' in message:
            if message['host'] in self.pantilts:
                message['host_type'] = 'pan_tilt'

        self.logger.info("TF declaration: %s::%s::%s\n\t @ %s %s", \
            temp['name'], temp['type'], temp['subtype'], temp['pose'], host_msg)

        # Fix thetas if exist:
        if temp['pose']['theta'] is not None:
            temp['pose']['theta'] = float(temp['pose']['theta'])
            temp['pose']['theta'] *= math.pi/180.0

        # Fix by resolution
        if 'start' not in temp['pose']:
            temp['pose']['x'] = float(temp['pose']['x'] * self.resolution)
            temp['pose']['y'] = float(temp['pose']['y'] * self.resolution)
        else:
            temp['pose']['start']['x'] = float(temp['pose']['start']['x'] * self.resolution)
            temp['pose']['start']['y'] = float(temp['pose']['start']['y'] * self.resolution)
            temp['pose']['end']['x'] = float(temp['pose']['end']['x'] * self.resolution)
            temp['pose']['end']['y'] = float(temp['pose']['end']['y'] * self.resolution)

        self.declarations.append(temp)
        self.declarations_info[temp['name']] = temp

        # Per type storage
        try:
            self.per_type_storage(temp)
        except Exception as e: # pylint: disable=broad-except
            self.logger.error("Error in per type storage for %s: %s", temp['name'], str(e))

        self.logger.info("Declaration done for %s", temp['name'])
        return {}

    def per_type_storage(self, d):
        """
        Organizes and stores data based on its type and subtype.
        Parameters:
        d (dict): A dictionary containing the following keys:
            - 'type' (str): The type of the data (e.g., 'actor', 'env', 'robot').
            - 'subtype' (dict): A dictionary containing subtype information.
            - 'name' (str): The name of the data.
            - 'base_topic' (str): The base topic for communication.
        Raises:
        ValueError: If the name already exists in self.names.
        Side Effects:
        - Updates self.names with the new name.
        - Updates self.per_type with the new data based on its type and subtype.
        - Initializes RPC clients for certain subclasses and stores them in self.effectors_get_rpcs.
        """
        type_ = d['type']
        sub = d['subtype']

        if d['name'] in self.names:
            self.logger.error("Name %s already exists. %s", d['name'], d['base_topic'])
        else:
            self.names.append(d['name'])
            self.logger.info("Adding %s to names", d['name'])

        if type_ == 'actor':
            self.per_type[type_][sub].append(d['name'])
            return

        if type_ == "env":
            subclass = sub['subclass'][0]
            category = sub['category']
            self.per_type[type_][category][subclass].append(d['name'])

            if subclass in ["thermostat", "humidifier", "leds"]:
                self.effectors_get_rpcs[d['name']] = self.commlib_factory.get_rpc_client(
                    rpc_name = d['base_topic'] + ".get"
                )
        elif type_ == "robot":
            subclass = sub['subclass'][0]
            category = sub['category']
            cls = sub['class']
            if cls in ["imu", "button", "env", "encoder", "twist", "line_follow"]:
                self.per_type[type_][category][cls].append(d['name'])
            else:
                self.per_type[type_][category][subclass].append(d['name'])

            if subclass in ["leds"]:
                self.effectors_get_rpcs[d['name']] = self.commlib_factory.get_rpc_client(
                    rpc_name = d['base_topic'] + ".get"
                )

            # Handle robots
            if d['host'] not in self.robots_get_devices_rpcs and d['host_type'] != 'pan_tilt':
                self.robots.append(d['host'])
                self.existing_hosts.append(d['host'])

                self.robots_get_devices_rpcs[d['host']] = self.commlib_factory.get_rpc_client(
                    rpc_name = f"{d['namespace']}.{d['host']}.nodes_detector.get_connected_devices"
                )

                self.subs[d['host']] = self.commlib_factory.get_subscriber(
                    topic = d['namespace'] + "." + d["host"] + ".pose.internal",
                    callback = self.robot_pose_callback,
                    old_way = True,
                )
                self.subs[d['host']].run()

        # Handle pan tilts
        if "pan_tilt" in  d['subtype']['subclass']:
            self.subs[d['name']] = self.commlib_factory.get_subscriber(
                topic = d["base_topic"] + ".data",
                callback = self.pan_tilt_callback,
                old_way = True,
            )

            self.pantilts[d['name']] = {
                'base_topic': d['base_topic'],
                'place': d['pose'], # this was d['categorization']['place'],
                'pan': 0.0
            }

        # Handle speakers
        if "speaker" in d['subtype']['subclass']:
            self.speaker_subs[d['name']] = self.commlib_factory.get_subscriber(
                topic = d["base_topic"] + ".speak.notify",
                callback = self.speak_callback
            )

        # Handle microphones
        if "microphone" in d['subtype']['subclass']:
            self.microphone_pubs[d['name']] = self.commlib_factory.get_publisher(
                topic = d["base_topic"] + ".speech_detected"
            )

    def get_affections_callback(self, message):
        """
        Callback function to get affections based on the provided message.

        Args:
            message (dict): A dictionary containing the message data. 
                            It should have a key 'name' with the name to check for affectability.

        Returns:
            dict: A dictionary with the affections if the name is affectable, 
                  otherwise an empty dictionary in case of an error.

        Raises:
            Exception: Logs an error message if an exception occurs during the process.
        """
        try:
            return self.check_affectability(message['name'])
        except Exception as e: # pylint: disable=broad-except
            self.logger.error("Error in get affections callback: %s", str(e))
            return {}

    def check_distance(self, xy, aff):
        """
        Calculate the distance between a given point and a reference point, and return the distance 
        along with associated properties.

        Args:
            xy (list or tuple): The coordinates (x, y) of the point to check.
            aff (str): The identifier for the reference point.

        Returns:
            dict: A dictionary containing:
                - 'distance' (float): The calculated distance between the given point and the 
                    reference point.
                - 'properties' (dict): The properties associated with the reference point.
        """
        pl_aff = self.places_absolute[aff]
        xyt = [pl_aff['x'], pl_aff['y']]
        d = calc_distance(xy, xyt)
        return {
            'distance': d,
            'properties': self.declarations_info[aff]["properties"]
        }

    def handle_affection_ranged(self, xy, f, type_):
        """
        Handles the affection of a point within a specified range.

        This method checks if the distance between a given point `xy` and a reference point `f` 
        is within the range specified in `self.declarations_info[f]`. If the distance is within 
        range, it returns a dictionary containing the type of affection, properties, distance, 
        range, name, and id of the reference point. If the distance is not within range, 
        it returns None.

        Args:
            xy (tuple): The coordinates of the point to check.
            f (str): The reference point identifier.
            type (str): The type of affection.

        Returns:
            dict or None: A dictionary with affection details if the point is within range, 
            otherwise None.
        """
        dd = self.check_distance(xy, f)
        d = dd['distance']
        # print(self.declarations_info[f])
        if d < self.declarations_info[f]['range']: # range is fire's
            if self.declarations_info[f]["properties"] is None:
                self.declarations_info[f]["properties"] = {}
            return {
                'type': type_,
                'info': self.declarations_info[f]["properties"],
                'distance': d,
                'range': self.declarations_info[f]['range'],
                'name': self.declarations_info[f]['name'],
                'id': self.declarations_info[f]['id']
            }
        return None

    def handle_affection_arced(self, name, f, type_):
        """
        Handles the affection of an arced sensor.
        This method calculates the distance between two points and checks if the 
        second point (f) is within the range and field of view (FOV) of the first 
        point (name). If the second point is within the range and FOV, it returns 
        a dictionary with information about the affection.
        Args:
            name (str): The name of the first point (sensor).
            f (str): The name of the second point (target).
            type (str): The type of the second point (e.g., "robot" or other).
        Returns:
            dict or None: A dictionary containing information about the affection 
            if the second point is within range and FOV, otherwise None. The 
            dictionary contains the following keys:
                - 'type': The type of the second point.
                - 'info': Properties of the second point.
                - 'distance': The distance between the two points.
                - 'min_sensor_ang': The minimum angle of the sensor's FOV.
                - 'max_sensor_ang': The maximum angle of the sensor's FOV.
                - 'actor_ang': The angle of the second point relative to the first.
                - 'name': The name of the second point.
                - 'id': The ID of the second point (if applicable).
        """

        p_d = self.places_absolute[name]
        p_f = self.places_absolute[f]

        d = math.sqrt((p_d['x'] - p_f['x'])**2 + (p_d['y'] - p_f['y'])**2)

        if type_ == "human":
            print(p_d)
            print(p_f)
            print(d)

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
            if min_a < f_ang < max_a:
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
                if type_ == "robot":
                    props = f
                    name = f
                    id_ = None
                else:
                    props = self.declarations_info[f]["properties"]
                    name = self.declarations_info[f]['name']
                    id_ = self.declarations_info[f]['id']
                return {
                    'type': type_,
                    'info': props,
                    'distance': d,
                    'min_sensor_ang': min_a,
                    'max_sensor_ang': max_a,
                    'actor_ang': ang,
                    'name': name,
                    'id': id_
                }

        return None

    # Affected by thermostats and fires
    def handle_env_sensor_temperature(self, name):
        """
        Handles the temperature data for an environmental sensor.
        This method processes the temperature data for a given environmental sensor by 
        checking the influence of thermostats and fires on the sensor's location.
        Args:
            name (str): The name of the environmental sensor.
        Returns:
            dict: A dictionary containing the temperature data influenced by thermostats 
                  and fires, keyed by the influencing factor.
        Raises:
            Exception: If an error occurs during the processing, it logs the error and 
                       raises an exception with the error message.
        """
        try:
            ret = {}
            pl = self.places_absolute[name]
            x_y = [pl['x'], pl['y']]

            for f in self.per_type['env']['actuator']['thermostat']:
                r = self.handle_affection_ranged(x_y, f, 'thermostat')
                if r is not None:
                    th_t = self.effectors_get_rpcs[f].call({})
                    r['info']['temperature'] = th_t['temperature']
                    ret[f] = r
            for f in self.per_type['actor']['fire']:
                r = self.handle_affection_ranged(x_y, f, 'fire')
                if r is not None:
                    ret[f] = r
        except Exception as e:
            self.logger.error(str(e))
            # pylint: disable=broad-exception-raised
            raise Exception(str(e)) from e

        return ret

    # Affected by humidifiers and water sources
    def handle_env_sensor_humidity(self, name):
        """
        Handles the humidity sensor for a given environment sensor.
        This method processes the humidity data for a specified environment sensor by 
        calculating the  effect of humidifiers and water sources on the sensor's location. 
        It returns a dictionary  containing the humidity information for each affecting actuator.
        Args:
            name (str): The name of the environment sensor.
        Returns:
            dict: A dictionary where keys are actuator names and values are dictionaries containing 
              humidity information and random noise.
        Raises:
            Exception: If an error occurs during processing, it logs the error and raises an 
            exception.
        """
        try:
            ret = {}
            pl = self.places_absolute[name]
            x_y = [pl['x'], pl['y']]

            for f in self.per_type['env']['actuator']['humidifier']:
                r = self.handle_affection_ranged(x_y, f, 'humidifier')
                if r is not None:
                    th_t = self.effectors_get_rpcs[f].call({})
                    r['info']['humidity'] = th_t['humidity']
                    ret[f] = r
            for f in self.per_type['actor']['water']:
                r = self.handle_affection_ranged(x_y, f, 'water')
                if r is not None:
                    ret[f] = r
        except Exception as e:
            self.logger.error(str(e))
            # pylint: disable=broad-exception-raised
            raise Exception(str(e)) from e

        return ret

    # Affected by humans, fire
    def handle_env_sensor_gas(self, name):
        """
        Handles the environmental sensor for gas detection.
        This method processes the environmental sensor data for gas detection by 
        determining the effect of various actors (humans and fire) on the sensor 
        based on their proximity.
        Args:
            name (str): The name of the place where the sensor is located.
        Returns:
            dict: A dictionary containing the actors and their respective effects 
                  on the sensor.
        Raises:
            Exception: If an error occurs during processing, it logs the error and 
                       raises an Exception.
        """
        try:
            ret = {}
            pl = self.places_absolute[name]
            x_y = [pl['x'], pl['y']]

            # - env actuator thermostat
            for f in self.per_type['actor']['human']:
                r = self.handle_affection_ranged(x_y, f, 'human')
                if r is not None:
                    ret[f] = r
            # - env actor fire
            for f in self.per_type['actor']['fire']:
                r = self.handle_affection_ranged(x_y, f, 'fire')
                if r is not None:
                    ret[f] = r
        except Exception as e:
            self.logger.error(str(e))
            # pylint: disable=broad-exception-raised
            raise Exception(str(e)) from e

        return ret

    # Affected by humans with sound, sound sources, speakers (when playing smth),
    # robots (when moving)
    def handle_sensor_microphone(self, name):
        """
        Handles the microphone sensor for a given place name.
        This method processes the microphone sensor data for a specified place,
        identifying and handling sound-related information for human actors and
        sound sources within the range of the microphone.
        Args:
            name (str): The name of the place where the microphone sensor is located.
        Returns:
            dict: A dictionary containing the affected human actors and sound sources
                  within the range of the microphone. The keys are the identifiers of
                  the actors or sound sources, and the values are the results of the
                  affection handling.
        Raises:
            Exception: If an error occurs during the processing, an exception is raised
                       and logged.
        """
        try:
            ret = {}
            pl = self.places_absolute[name]
            x_y = [pl['x'], pl['y']]

            # - actor human
            for f in self.per_type['actor']['human']:
                if self.declarations_info[f]['properties']['sound'] == 1:
                    r = self.handle_affection_ranged(x_y, f, 'human')
                    if r is not None:
                        ret[f] = r
            # - actor sound sources
            for f in self.per_type['actor']['sound_source']:
                r = self.handle_affection_ranged(x_y, f, 'sound_source')
                if r is not None:
                    ret[f] = r
        except Exception as e:
            self.logger.error(str(e))
            # pylint: disable=broad-exception-raised
            raise Exception(str(e)) from e

        return ret

    def compute_luminosity(self, name, print_debug = False):
        """
        Compute the luminosity at a given place identified by `name`.
        This method calculates the luminosity at a specific location by considering
        the contributions from environmental light sources, robot LEDs, and actor fires.
        It also factors in the environmental luminosity and ensures the final luminosity
        value is within the range [0, 100]. Optionally, it can print debug information
        during the computation process.
        Args:
            name (str): The name of the place for which to compute the luminosity.
            print_debug (bool, optional): If True, prints debug information. Defaults to False.
        Returns:
            float: The computed luminosity value, with a small random variation added.
        """

        place = self.places_absolute[name]
        x_y = [place['x'], place['y']]
        lum = 0

        if print_debug:
            print(f"Computing luminosity for {name}")

        # - env light
        for f in self.per_type['env']['actuator']['leds']:
            r = self.handle_affection_ranged(x_y, f, 'light')
            if r is not None:
                th_t = self.effectors_get_rpcs[f].call({})
                new_r = r
                new_r['info'] = th_t
                rel_range = 1 - new_r['distance'] / new_r['range']
                lum += rel_range * new_r['info']['luminosity']
                if print_debug:
                    print(f"\t{f} - {new_r['info']['luminosity']}")
        # - robot leds
        for f in self.per_type['robot']['actuator']['leds']:
            r = self.handle_affection_ranged(x_y, f, 'light')
            if r is not None:
                th_t = self.effectors_get_rpcs[f].call({})
                new_r = r
                new_r['info'] = th_t
                rel_range = 1 - new_r['distance'] / new_r['range']
                lum += rel_range * new_r['info']['luminosity']
                if print_debug:
                    print(f"\t{f} - {new_r['info']['luminosity']}")
        # - actor fire
        for f in self.per_type['actor']['fire']:
            r = self.handle_affection_ranged(x_y, f, 'fire')
            if r is not None:
                rel_range = 1 - r['distance'] / r['range']
                lum += 100 * rel_range
                if print_debug:
                    print(f"\t{f} - 100")

        env_luminosity = self.env_properties['luminosity']
        if print_debug:
            print(f"Env luminosity: {env_luminosity}")

        if lum < env_luminosity:
            lum = lum * 0.1 + env_luminosity
        else:
            lum = env_luminosity * 0.1 + lum

        if lum > 100:
            lum = 100
        if lum < 0:
            lum = 0

        if print_debug:
            print(f"Computed luminosity: {lum}")

        return lum + random.uniform(-0.25, 0.25)

    # Affected by light, fire
    def handle_env_light_sensor(self, name):
        """
        Handles the environmental light sensor for a given place.
        This method processes the environmental light sensor data for a specified place
        by calculating the affection range of light and fire actuators and retrieving
        relevant information from the effectors.
        Args:
            name (str): The name of the place to handle the environmental light sensor for.
        Returns:
            dict: A dictionary containing the processed data for light and fire actuators
                  that affect the specified place.
        Raises:
            Exception: If an error occurs during processing, an exception is raised and logged.
        """
        try:
            ret = {}
            pl = self.places_absolute[name]
            x_y = [pl['x'], pl['y']]

            # - env light
            for f in self.per_type['env']['actuator']['leds']:
                r = self.handle_affection_ranged(x_y, f, 'light')
                if r is not None:
                    th_t = self.effectors_get_rpcs[f].call({})
                    new_r = r
                    new_r['info'] = th_t
                    ret[f] = new_r
            # - actor fire
            for f in self.per_type['actor']['fire']:
                r = self.handle_affection_ranged(x_y, f, 'fire')
                if r is not None:
                    ret[f] = r
        except Exception as e:
            self.logger.error(str(e))
            # pylint: disable=broad-exception-raised
            raise Exception(str(e)) from e

        return ret

    # Affected by barcode, color, human, qr, text
    def handle_sensor_camera(self, name, with_robots = False):
        """
        Processes sensor data from a camera and handles different types of actors 
        (human, qr, barcode, color, text) and optionally robots.
        Args:
            name (str): The name of the place or sensor.
            with_robots (bool, optional): If True, includes robots in the processing. 
            Defaults to False.
        Returns:
            dict: A dictionary containing the detected actors and their respective processed data.
        Raises:
            Exception: If an error occurs during processing.
        The function performs the following steps:
        1. Retrieves the absolute place data for the given name.
        2. Computes the luminosity of the place.
        3. Processes different types of actors (human, qr, barcode, color, text) and stores the 
            results.
        4. Optionally processes robots if `with_robots` is True.
        5. Filters the results based on the luminosity, simulating detection failure in low light 
            conditions.
        6. Logs and raises an exception if any error occurs during processing.
        """
        ret = {}
        pl = self.places_absolute[name]
        x_y = [pl['x'], pl['y']]
        try:
            # - actor human
            for f in self.per_type['actor']['human']:
                print(f"Checking {f}")
                r = self.handle_affection_arced(name, f, 'human')
                print(r)
                if r is not None:
                    ret[f] = r
            # - actor qr
            for f in self.per_type['actor']['qr']:
                r = self.handle_affection_arced(name, f, 'qr')
                if r is not None:
                    ret[f] = r
            # - actor barcode
            for f in self.per_type['actor']['barcode']:
                r = self.handle_affection_arced(name, f, 'barcode')
                if r is not None:
                    ret[f] = r
            # - actor color
            for f in self.per_type['actor']['color']:
                r = self.handle_affection_arced(name, f, 'color')
                if r is not None:
                    ret[f] = r
            # - env lights
            for f in self.per_type['env']['actuator']['leds']:
                r = self.handle_affection_ranged(x_y, f, 'light')
                if r is not None:
                    th_t = self.effectors_get_rpcs[f].call({})
                    print(th_t)
                    new_r = r
                    new_r['info'] = th_t
                    ret[f] = new_r
            # - actor text
            for f in self.per_type['actor']['text']:
                r = self.handle_affection_arced(name, f, 'text')
                if r is not None:
                    ret[f] = r

            # check all robots
            if with_robots:
                for rob in self.robots:
                    r = self.handle_affection_arced(name, rob, 'robot')
                    if r is not None:
                        ret[rob] = r

        except Exception as e: # pylint: disable=broad-except
            self.logger.error("handle_sensor_camera: %s", str(e))
            # pylint: disable=broad-exception-raised
            raise Exception(str(e)) from e

        return ret

    # Affected by rfid_tags
    def handle_sensor_rfid_reader(self, name):
        """
        Handles the RFID reader sensor data for a given place name.
        This method processes the RFID reader sensor data associated with a specific place
        identified by the given name. It retrieves the absolute position (x, y) and orientation 
        (theta) of the place, and then processes the RFID tags associated with actors in that place.
        Args:
            name (str): The name of the place to handle the RFID reader sensor data for.
        Returns:
            dict: A dictionary containing the processed RFID tag data for actors in the specified 
            place.
        Raises:
            Exception: If an error occurs during the processing of the RFID reader sensor data.
        """
        try:
            ret = {}

            for f in self.per_type['actor']['rfid_tag']:
                r = self.handle_affection_arced(name, f, 'rfid_tag')
                if r is not None:
                    ret[f] = r

        except Exception as e:
            self.logger.error(str(e))
            # pylint: disable=broad-exception-raised
            raise Exception(str(e)) from e

        return ret

    # Affected by robots
    def handle_area_alarm(self, name):
        """
        Handle area alarm for a given place name.
        This method checks if any robots are within the specified range of the given place.
        If a robot is within range, it adds the robot's name and its distance from the place
        to the return dictionary.
        Args:
            name (str): The name of the place to check for area alarms.
        Returns:
            dict: A dictionary where the keys are the names of the robots within range,
                  and the values are dictionaries containing the distance of the robot
                  from the place and the range.
        Raises:
            Exception: If an error occurs during the process, it logs the error and raises 
            an exception.
        """
        try:
            ret = {}
            pl = self.places_absolute[name]
            xy = [pl['x'], pl['y']]
            range_ = self.declarations_info[name]['range']
            # Check all robots if in there
            for r in self.robots:
                pl_aff = self.places_absolute[r]
                xyt = [pl_aff['x'], pl_aff['y']]
                d = math.sqrt((xy[0] - xyt[0])**2 + (xy[1] - xyt[1])**2)
                if d < range_:
                    ret[r] = {
                        "distance": d,
                        "range": range_
                    }

        except Exception as e:
            self.logger.error(str(e))
            # pylint: disable=broad-exception-raised
            raise Exception(str(e)) from e

        return ret

    # Affected by robots
    def handle_env_distance(self, name):
        """
        Calculate the distance of all robots from a specified place and determine if they are 
        within range.
        Args:
            name (str): The name of the place to check distances from.
        Returns:
            dict: A dictionary where the keys are robot names and the values are dictionaries 
            containing:
                - "distance" (float): The distance of the robot from the specified place.
                - "range" (float): The range within which the robot is considered to be.
        Raises:
            Exception: If an error occurs during the calculation, it logs the error and raises an 
            Exception.
        """
        try:
            ret = {}

            pl = self.places_absolute[name]
            xy = [pl['x'], pl['y']]
            range_ = self.declarations_info[name]['range']

            # Check all robots if in there
            for r in self.robots:
                pl_aff = self.places_absolute[r]
                xyt = [pl_aff['x'], pl_aff['y']]
                d = math.sqrt((xy[0] - xyt[0])**2 + (xy[1] - xyt[1])**2)
                if d < range_:
                    ret[r] = {
                        "distance": d,
                        "range": range_
                    }

        except Exception as e:
            self.logger.error(str(e))
            # pylint: disable=broad-exception-raised
            raise Exception(str(e)) from e

        return ret

    # Affected by robots
    def handle_linear_alarm(self, name):
        """
        Handles linear alarms for robots based on their positions and declared linear paths.
        Args:
            name (str): The name of the linear declaration to check against.
        Returns:
            dict: A dictionary where keys are robot identifiers and values are True if an 
            intersection with the linear path is detected.
        Raises:
            Exception: If any error occurs during the processing, it logs the error and raises 
            an Exception.
        This method performs the following steps:
        1. Retrieves the start and end positions of the linear declaration.
        2. Calculates the distance between the start and end positions.
        3. Iterates through all robots to check if their current path intersects with the linear 
            declaration.
        4. Updates the robot's previous and current positions.
        5. Checks for intersections between the robot's path and the linear declaration.
        6. Logs and raises any exceptions encountered during processing.
        """
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

                intersection = check_lines_intersection(sta, end, \
                    self.lin_alarms_robots[r]["curr"],
                    self.lin_alarms_robots[r]["prev"]
                )

                if intersection is True:
                    ret[r] = intersection

        except Exception as e:
            self.logger.error(str(e))
            # pylint: disable=broad-exception-raised
            raise Exception(str(e)) from e

        return ret

    def check_affectability(self, name):
        """
        Check the affectability of a device based on its type and subtype.
        Parameters:
        name (str): The name of the device to check.
        Returns:
        dict: A dictionary containing the results of the affectability check.
        Raises:
        Exception: If the device name is not found in declarations_info or if there is an 
        error in device handling.
        """
        try:
            type_ = self.declarations_info[name]['type']
            subt = self.declarations_info[name]['subtype']
        except Exception as e: # pylint: disable=broad-except
            # pylint: disable=broad-exception-raised
            raise Exception(f"{name} not in devices") from e

        try:
            ret = {}
            if type_ == "env":
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
                if 'distance' in subt['subclass']:
                    ret = self.handle_env_distance(name)
            elif type_ == "robot":
                if 'microphone' in subt['subclass']:
                    ret = self.handle_sensor_microphone(name)
                if 'camera' in subt['subclass']:
                    ret = self.handle_sensor_camera(name)
                if 'rfid_reader' in subt['subclass']:
                    ret = self.handle_sensor_rfid_reader(name)
                if 'distance' in subt['subclass']:
                    ret = self.handle_env_distance(name)
                if 'temp_hum_pressure_gas' in subt['subclass']:
                    ret = {
                        'temperature': self.handle_env_sensor_temperature(name),
                        'humidity': self.handle_env_sensor_humidity(name),
                        'gas': self.handle_env_sensor_gas(name)
                    }
        except Exception as e:
            self.logger.error("Error in device handling: %s", str(e))
            # pylint: disable=broad-exception-raised
            raise Exception(f"Error in device handling: {str(e)}") from e

        return {
            "affections": ret,
            "env_properties": self.env_properties,
        }

    def get_sim_detection_callback(self, message):
        """
        Handles the simulation detection callback based on the provided message.
        Args:
            message (dict): A dictionary containing the detection message with keys 'name' and 
            'type'.
        Returns:
            dict: A dictionary containing the detection result with keys:
                - "result" (bool): The detection decision.
                - "info" (str or dict): Additional information about the detection.
                - "frm" (dict or None): The frame information related to the detection.
        """
        try:
            name = message['name']
            type_ = message['type']
            decl = self.declarations_info[name]
        except Exception: # pylint: disable=broad-except
            self.logger.error("'%s' not in devices", message['name'])
            return

        if decl['subtype']['subclass'][0] not in ['camera', 'microphone']:
            return {
                "result": False,
                "info": "Wrong detection device. Not microphone nor camera."
            }

        id_ = ''.join(random.choices(string.ascii_uppercase + string.digits, k = 6))
        print(f"Detection request for {name} with id {id}")
        self.detections_publisher.publish({
            "name": name,
            "device_type": decl['subtype']['subclass'][0],
            "type": type_,
            "id": id_,
            "state": "start",
            "result": None
        })

        frm = None

        final_detection = {}

        if decl['subtype']['subclass'][0] == "microphone":
            # possible types: sound, language, emotion, speech2text
            final_detection = {
                "sound": {
                    "result": False,
                    "value": None,
                },
                "language": {
                    "result": False,
                    "value": None,
                },
                "emotion": {
                    "result": False,
                    "value": None,
                },
                "speech2text": {
                    "result": False,
                    "value": None,
                }
            }

            ret = self.check_affectability(name)
            frm = ret
            print(message)
            print("===============", ret)

            if type_ == "sound":
                if ret is not None:
                    if len(ret) >= 1:
                        for ff in ret:
                            final_detection['sound']['result'] = True
                            final_detection['sound']['value'] = "sound"
                            frm = ret[ff]
            elif type_ == "language":
                if ret is not None:
                    if len(ret) >= 1:
                        for x in ret:
                            final_detection['language']['result'] = True
                            final_detection['language']['value'] = ret[x]['info']['language'] # gets the last one
                            frm = ret[x]
            elif type_ == "emotion":
                if ret is not None:
                    if len(ret) >= 1:
                        for x in ret:
                            final_detection['emotion']['result'] = True
                            final_detection['emotion']['value'] = ret[x]['info']['emotion']
                            frm = ret[x]
            elif type_ == "speech2text":
                if ret is not None:
                    if len(ret) >= 1:
                        for x in ret:
                            if ret[x]['type'] == 'human':
                                final_detection['speech2text']['result'] = True
                                final_detection['speech2text']['value'] = ret[x]['info']['speech']
                                frm = ret[x]
                if ret[x]['info']['speech'] == "":
                    final_detection['speech2text']['result'] = False
                    final_detection['speech2text']['value'] = ""
            else:
                self.logger.error("Wrong detection type: %s", type_)

        elif decl['subtype']['subclass'][0] == "camera":
            # possible types: face, qr, barcode, gender, age, motion, color, emotion
            ret = self.handle_sensor_camera(name, with_robots = True)

            # gt luminosity
            lum = self.compute_luminosity(name, print_debug = False)

            final_detection = {
                "face": {
                    "result": False,
                    "value": None,
                },
                "gender": {
                    "result": False,
                    "value": None,
                },
                "age": {
                    "result": False,
                    "value": None,
                },
                "emotion": {
                    "result": False,
                    "value": None,
                },
                "motion": {
                    "result": False,
                    "value": None,
                },
                "qr": {
                    "result": False,
                    "value": None,
                },
                "barcode": {
                    "result": False,
                    "value": None,
                },
                "text": {
                    "result": False,
                    "value": None,
                },
                "color": {
                    "result": False,
                    "value": None,
                },
                "robot": {
                    "result": False,
                    "value": None,
                }
            }
            decision = True
            roulette = random.uniform(0, 1)
            if math.pow(roulette, 2) > lum:
                self.logger.warning("Camera detection: too dark")
                decision = False

            print(ret.items())
            if type_ == "face":
                for x, item in ret.items():
                    if item['type'] == 'human': # gets the last one
                        final_detection['face']['result'] = True and decision
                        final_detection['face']['value'] = ""
                        frm = item
            elif type_ == "gender":
                for x, item in ret.items():
                    if item['type'] == 'human' and item['info']['gender'] != "none": # gets the last
                        final_detection['gender']['result'] = True and decision
                        final_detection['gender']['value'] = item['info']['gender']
                        frm = item
            elif type_ == "age":
                for x, item in ret.items():
                    if item['type'] == 'human' and item['info']['age'] != -1: # gets the last one
                        final_detection['age']['result'] = True and decision
                        final_detection['age']['value'] = item['info']['age']
                        frm = item
            elif type_ == "emotion":
                for x, item in ret:
                    if item['type'] == 'human': # gets the last one
                        final_detection['emotion']['result'] = True and decision
                        final_detection['emotion']['value'] = item['info']['emotion']
                        frm = item
            elif type_ == "motion":
                for x, item in ret.items():
                    if item['type'] == 'human' and item['info']['motion'] == 1: # gets the last one
                        final_detection['motion']['result'] = True and decision
                        final_detection['motion']['value'] = ""
                        frm = item
            elif type_ == "qr":
                for x, item in ret.items():
                    if item['type'] == 'qr':
                        final_detection['qr']['result'] = True and decision
                        final_detection['qr']['value'] = item['info']['message']
                        frm = item
            elif type_ == "barcode":
                for x, item in ret.items():
                    if item['type'] == 'barcode':
                        final_detection['barcode']['result'] = True and decision
                        final_detection['barcode']['value'] = item['info']['message']
                        frm = item
            elif type_ == "text":
                for x, item in ret.items():
                    if item['type'] == 'text':
                        final_detection['text']['result'] = True and decision
                        final_detection['text']['value'] = item['info']['text']
                        frm = item
            elif type_ == "color":
                if len(ret) == 0:
                    frm = None
                    final_detection['color']['result'] = False
                    final_detection['color']['value'] = {'r': 0, 'g': 0, 'b': 0}
                for x, item in ret.items():
                    if item['type'] == 'color':
                        final_detection['color']['result'] = True and decision
                        final_detection['color']['value'] = item['info']
                        frm = item
                    if item['type'] == 'light':
                        final_detection['color']['result'] = True and decision
                        final_detection['color']['value'] = item['info']
                        frm = item
            elif type_ == "robot":
                for x, item in ret.items():
                    if item['type'] == 'robot':
                        final_detection['robot']['result'] = True and decision
                        final_detection['robot']['value'] = item['info']
                        frm = item
            else:
                self.logger.error("Wrong detection type: %s", type_)
                return

        else: # possible types: face, qr, barcode, gender, age, color, motion, emotion
            pass

        self.logger.info("Detection result for %s with id %s: %s, %s",\
            name, id_, final_detection, frm)

        # NOTE: Is this needed?
        self.detections_publisher.publish({
            "name": name,
            "device_type": decl['subtype']['subclass'][0],
            "type": type_,
            "id": id_,
            "state": "end",
            "result": final_detection
        })

        self.mqtt_notifier.dispatch_detection({
            "name": name,
            "device_type": decl['subtype']['subclass'][0],
            "type": type_,
            "id": id_,
            "state": "end",
            "result": final_detection,
            "frm": frm
        })

        return {
            "detection": final_detection,
            "frm": frm,
        }

    def stop(self):
        """
        Stops the communication library factory.

        This method calls the stop method on the commlib_factory instance to 
        terminate any ongoing communication processes.
        """
        self.declarations = []
        self.declarations_info = {}
        self.names = []

        self.effectors_get_rpcs = {}
        self.robots_get_devices_rpcs = {}

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

        if self.commlib_factory is not None:
            self.commlib_factory.stop()
