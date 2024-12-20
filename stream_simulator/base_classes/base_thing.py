"""
File that contains the BaseThing class.
"""
#!/usr/bin/python
# -*- coding: utf-8 -*-

from stream_simulator.connectivity import CommlibFactory

class BaseThing:
    """
    Base class for things in the stream simulator.

    Attributes:
        id (int): The ID of the thing.
        commlib_factory (CommlibFactory): The communication library factory.
        tf_declare_rpc (RPCClient): The RPC client for the tf_declare_rpc_topic.
        tf_affection_rpc (RPCClient): The RPC client for the tf_affection_rpc_topic.
        enable_rpc_server (RPCService): The RPC service for enabling the thing.
        disable_rpc_server (RPCService): The RPC service for disabling the thing.
        set_mode_rpc_server (RPCService): The RPC service for setting the thing's mode.
        get_mode_rpc_server (RPCService): The RPC service for getting the thing's mode.
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

        self.name = _name
        self.base_topic = None
        self.namespace = None
        self.tf_declare_rpc = None
        self.tf_affection_rpc = None
        self.enable_rpc_server = None
        self.disable_rpc_server = None
        self.set_mode_rpc_server = None
        self.get_mode_rpc_server = None
        self.publisher = None
        self.publisher_triggers = None
        self.set_rpc_server = None
        self.get_rpc_server = None
        self.simulation_started_sub = None
        self.simulator_started = False

        self.tf_declare_pub = None

        self.commlib_factory = CommlibFactory(node_name=self.name)
        if auto_start:
            self.commlib_factory.run()

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
        self.simulation_started_sub = self.commlib_factory.getSubscriber(
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
        self.tf_declare_rpc = self.commlib_factory.getRPCClient(
            rpc_name=package["tf_declare_rpc_topic"]
        )

        self.tf_affection_rpc = self.commlib_factory.getRPCClient(
            rpc_name=package["tf_affection_rpc_topic"]
        )

    def set_enable_disable_rpcs(self, base_topic, enable_cb, disable_cb):
        """
        Sets up the enable and disable RPC services for the thing.

        Args:
            base_topic (str): The base topic for the RPC services.
            enable_cb (callable): The callback function for enabling the thing.
            disable_cb (callable): The callback function for disabling the thing.
        """
        self.enable_rpc_server = self.commlib_factory.getRPCService(
            callback=enable_cb,
            rpc_name=base_topic + ".enable"
        )
        self.disable_rpc_server = self.commlib_factory.getRPCService(
            callback=disable_cb,
            rpc_name=self.base_topic + ".disable"
        )

    def set_mode_get_set_rpcs(self, base_topic, set_cb, get_cb):
        """
        Sets up the set_mode and get_mode RPC services for the thing.

        Args:
            base_topic (str): The base topic for the RPC services.
            set_cb (callable): The callback function for setting the thing's mode.
            get_cb (callable): The callback function for getting the thing's mode.
        """
        self.set_mode_rpc_server = self.commlib_factory.getRPCService(
            callback=set_cb,
            rpc_name=base_topic + ".set_mode"
        )
        self.get_mode_rpc_server = self.commlib_factory.getRPCService(
            callback=get_cb,
            rpc_name=base_topic + ".get_mode"
        )

    def set_data_publisher(self, base_topic):
        """
        Sets up the data publisher for the thing.

        Args:
            base_topic (str): The base topic for the data publisher.
        """
        self.publisher = self.commlib_factory.getPublisher(
            topic=base_topic + ".data"
        )

    def set_triggers_publisher(self, base_topic):
        """
        Sets up the triggers publisher for the thing.

        Args:
            base_topic (str): The base topic for the triggers publisher.
        """
        self.publisher_triggers = self.commlib_factory.getPublisher(
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
        self.set_rpc_server = self.commlib_factory.getRPCService(
            callback=set_cb,
            rpc_name=base_topic + ".set"
        )
        self.get_rpc_server = self.commlib_factory.getRPCService(
            callback=get_cb,
            rpc_name=base_topic + ".get"
        )
