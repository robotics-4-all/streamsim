"""
File that contains the BaseThing class.
"""
#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging

from stream_simulator.connectivity import CommlibFactory

class BaseThing:
    """
    Base class for things in the stream simulator.

    Attributes:
        id (int): The ID of the thing.
        commlib_factory (CommlibFactory): The communication library factory.
        tf_declare_rpc (RPCClient): The RPC client for the tf_declare_rpc_topic.
        tf_affection_rpc (RPCClient): The RPC client for the tf_affection_rpc_topic.
        publisher (Publisher): The publisher for publishing data.
        publisher_triggers (Publisher): The publisher for publishing triggers.
    """

    id = 0

    def __init__(self, _name, auto_start=True):
        """
        Initializes a new instance of the BaseThing class.

        Args:
            _name (str): The name of the thing.
        """
        BaseThing.id += 1

        self.commlib_factory = None
        self.name = _name
        self.base_topic = None
        self.namespace = None
        self.tf_declare_rpc = None
        self.tf_affection_rpc = None
        self.tf_distance_calculator_rpc = None
        self.publisher = None
        self.publisher_triggers = None
        self.command_subscriber = None
        self.state_publisher_internal = None
        self.state_publisher = None
        self.set_rpc_server = None
        self.get_rpc_server = None
        self.simulation_started_sub = None
        self.simulator_started = False
        self.sensor_state_publisher = None
        self.sensor_state_subscriber = None

        self.conf = None
        self.state = 'on' # by default on
        self.proximity_mode = False
        self.proximity_distance = 0

        # Define self attributes
        self.mock_parameters = {
            "constant_value": None,
            "random_min": None,
            "random_max": None,
            "triangle_min": None,
            "triangle_max": None,
            "triangle_step": None,
            "normal_std": None,
            "normal_mean": None,
            "sinus_dc": None,
            "sinus_amp": None,
            "sinus_step": None
        }

        self.tf_declare_pub = None

        self.commlib_factory = CommlibFactory(node_name=self.name)
        if auto_start:
            self.commlib_factory.run()

        self.logger = logging.getLogger(self.name + "_base_thing")

    def set_conf(self, conf):
        """
        Sets the configuration for the thing.

        Args:
            conf (dict): The configuration dictionary.
        """
        self.conf = conf
        if 'state' in conf:
            self.state = conf['state']
            self.logger.info("[%s] Setting state to %s", self.name, self.state)

        self.proximity_mode = conf["proximity_mode"] \
            if "proximity_mode" in conf else False
        self.proximity_distance = conf["proximity_distance"] \
            if "proximity_distance" in conf and self.proximity_mode else 0

    def set_sensor_state_interfaces(self, base_topic):
        """
        Sets up the sensor state interfaces by initializing the publisher and subscriber
        for the sensor state.

        Args:
            base_topic (str): The base topic for the sensor state interfaces. The publisher
                              will publish to '<base_topic>.state' and the subscriber will
                              subscribe to '<base_topic>.set'.

        Returns:
            None
        """
        self.sensor_state_publisher = self.commlib_factory.get_publisher(
            topic=base_topic + ".state"
        )
        self.sensor_state_subscriber = self.commlib_factory.get_subscriber(
            topic=base_topic + ".state.set",
            callback=self.sensor_state_cb
        )

    def sensor_state_cb(self, msg):
        """
        Callback function to update the sensor state.

        Args:
            msg (dict): A dictionary containing the sensor state information. 
                        It must have a key 'state' whose value will be assigned 
                        to the instance's state attribute.
        """
        self.state = msg['state']
        initiator = msg['initiator']
        self.logger.critical("[%s] Setting state to %s by %s", self.name, self.state, initiator)
        print(self.proximity_mode)
        if self.proximity_mode:
            # Check if we have an initiator in the message
            allowed_distance = self.proximity_distance
            if self.proximity_distance == 0:
                allowed_distance = 0.5
            if initiator is not None:
                dist = self.tf_distance_calculator_rpc.call(
                    {"initiator": initiator, "target": self.name}
                )
                if dist['distance'] is None or dist['distance'] > allowed_distance:
                    self.logger.info("[%s] %s is too far from %s", self.name, self.name, initiator)
                    return
                self.logger.info("[%s] %s is close enough to %s", self.name, self.name, initiator)
            else: # no initiator
                self.logger.warning("[%s] %s has no initiator", self.name, self.name)
                return

        self.sensor_state_publisher.publish({"state": self.state})

    def generate_info(self, conf, package, _type, _category, _class, _subclass):
        """
        Generates a dictionary containing information based on the provided configuration 
        and package details.
        Args:
            conf (dict): Configuration dictionary containing details such as 'name', 'place', 
            and 'mode'.
            package (dict): Package dictionary containing 'base' and 'namespace'.
            _type (str): The type of the item.
            _category (str): The category of the item.
            _class (str): The class of the item.
            _subclass (str): The subclass of the item.
        Returns:
            dict: A dictionary containing the generated information, including the base topic, 
            name, place, 
                  enabled status, mode, configuration, and categorization details.
        """
        _name = conf["name"]
        _pack = package["base"]
        _namespace = package["namespace"]
        _place = conf["place"]

        info = {
            "type": _type,
            "base_topic": f"{_namespace}.{_pack}.{_place}.{_category}.{_class}.{_subclass}.{_name}",
            "name": _name,
            "place": conf["place"],
            "enabled": True,
            "mode": conf["mode"],
            "conf": conf,
            "categorization": {
                "host_type": _pack,
                "place": _place,
                "category": _category,
                "class": _class,
                "subclass": [_subclass],
                "name": _name
            }
        }
        return info

    def set_simulation_communication(self, namespace):
        """
        Sets up the communication for the simulation by subscribing to the 
        'simulation_started' topic within the given namespace.

        Args:
            namespace (str): The namespace to be used for the simulation communication.

        Attributes:
            namespace (str): The namespace used for the simulation communication.
            simulation_started_sub (Subscriber): The subscriber object for the 
                                                 'simulation_started' topic.
        """
        self.namespace = namespace
        self.simulation_started_sub = self.commlib_factory.get_subscriber(
            topic=f"{namespace}.simulation_started",
            callback=self.simulation_started_cb
        )

    def simulation_started_cb(self, _):
        """
        Callback function for the simulation_started topic.

        Args:
            msg (str): The message received on the topic.
        """
        self.simulator_started = True

    def set_tf_communication(self, package):
        """
        Sets up the TF communication for the thing.

        Args:
            package (dict): The package containing the TF communication details.
        """
        self.tf_declare_rpc = self.commlib_factory.get_rpc_client(
            rpc_name=package["tf_declare_rpc_topic"]
        )

        self.tf_affection_rpc = self.commlib_factory.get_rpc_client(
            rpc_name=package["tf_affection_rpc_topic"]
        )

    def set_tf_distance_calculator_rpc(self, package):
        """
        Sets the TensorFlow distance calculator RPC client.

        This method initializes the RPC client for the TensorFlow distance calculator
        using the provided package information. The RPC client is created using the
        communication library factory.

        Args:
            package (dict): A dictionary containing the configuration for the RPC client.
                            It must include the key "tf_distance_calculator_rpc_topic" which
                            specifies the topic name for the RPC client.
        """
        self.tf_distance_calculator_rpc = self.commlib_factory.get_rpc_client(
            rpc_name=package["tf_distance_calculator_rpc_topic"]
        )

    def set_data_publisher(self, base_topic):
        """
        Sets up the data publisher for the thing.

        Args:
            base_topic (str): The base topic for the data publisher.
        """
        self.publisher = self.commlib_factory.get_publisher(
            topic=base_topic + ".data"
        )

    def set_state_publisher(self, base_topic):
        """
        Sets up the data publisher for the thing.

        Args:
            base_topic (str): The base topic for the data publisher.
        """
        self.state_publisher = self.commlib_factory.get_publisher(
            topic=base_topic + ".state"
        )

    def set_command_subscriber(self, base_topic, callback):
        """
        Sets up the data publisher for the thing.

        Args:
            base_topic (str): The base topic for the data publisher.
        """
        self.command_subscriber = self.commlib_factory.get_subscriber(
            topic=base_topic + ".set",
            callback=callback
        )

    def set_state_publisher_internal(self, namespace):
        """
        Sets up the internal state publisher for the thing.

        Args:
            namespace (str): The namespace for the internal state publisher.
        """
        self.state_publisher_internal = self.commlib_factory.get_publisher(
            topic=namespace + ".state.internal"
        )

    def set_triggers_publisher(self, base_topic):
        """
        Sets up the triggers publisher for the thing.

        Args:
            base_topic (str): The base topic for the triggers publisher.
        """
        self.publisher_triggers = self.commlib_factory.get_publisher(
            topic=base_topic + ".triggers"
        )

    def set_effector_set_get_rpcs(self, base_topic, set_cb, get_cb):
        """
        Sets up the set_effector and get_effector RPC services for the thing.

        Args:
            base_topic (str): The base topic for the RPC services.
            set_cb (callable): The callback function for setting the effector attributes.
            get_cb (callable): The callback function for getting the effector attributes.
        """
        if set_cb is not None:
            self.set_rpc_server = self.commlib_factory.get_rpc_service(
                callback=set_cb,
                rpc_name=base_topic + ".set"
            )
        if get_cb is not None:
            self.get_rpc_server = self.commlib_factory.get_rpc_service(
                callback=get_cb,
                rpc_name=base_topic + ".get"
            )

    def stop(self):
        """
        Stops the communication for the thing.
        """
        self.commlib_factory.stop(wait=True)
