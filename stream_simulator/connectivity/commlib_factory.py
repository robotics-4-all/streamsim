#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import inspect
import os
from dotenv import load_dotenv

from commlib.node import Node
from commlib.transports.mqtt import ConnectionParameters as MQTTConnectionParameters
from commlib.transports.redis import ConnectionParameters as RedisConnectionParameters

class CommlibFactory(Node):
    """
    CommlibFactory is a class that extends the Node class and provides methods to create 
    various communication entities such as publishers, subscribers, RPC services, RPC clients,
    action servers, and action clients.
    It also maintains statistics about these entities for different brokers (e.g., MQTT, Redis).
    Attributes:
        stats (dict): A dictionary to keep track of the number of publishers, subscribers, RPC servers, RPC clients,
                      action servers, and action clients for different brokers.
    Methods:
        __init__(*args, **kwargs):
            Initializes the CommlibFactory instance, sets up logging, and initializes connection parameters.
        notify_ui(type=None, data=None):
            Publishes a notification to the UI if the notify attribute is set.
        inform(broker, topic, type, extras=""):
            Logs information about the communication entity being created.
        getPublisher(broker="mqtt", topic=None):
            Creates and runs a publisher for the specified broker and topic. Updates the statistics.
        getSubscriber(broker="mqtt", topic=None, callback=None):
            Creates and runs a subscriber for the specified broker and topic. Updates the statistics.
        getRPCService(broker="mqtt", rpc_name=None, callback=None):
            Creates and runs an RPC service for the specified broker and RPC name. Updates the statistics.
        getRPCClient(broker="mqtt", rpc_name=None):
            Creates and runs an RPC client for the specified broker and RPC name. Updates the statistics.
        getActionServer(broker="mqtt", action_name=None, callback=None):
            Creates and runs an action server for the specified broker and action name. Updates the statistics.
        getActionClient(broker="mqtt", action_name=None):
            Creates and runs an action client for the specified broker and action name. Updates the statistics.
    """
    stats = {
        'mqtt': {
            'publishers': 0,
            'subscribers': 0,
            'rpc servers': 0,
            'rpc clients': 0,
            'action servers': 0,
            'action clients': 0
        },
        'redis': {
            'publishers': 0,
            'subscribers': 0,
            'rpc servers': 0,
            'rpc clients': 0,
            'action servers': 0,
            'action clients': 0
        },
    }

    publisher_topics = {}
    subscriber_topics = {}
    rpc_server_topics = {}
    rpc_client_topics = {}
    action_server_topics = {}
    action_client_topics = {}

    def __init__(self, *args, **kwargs):
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        self._logger = logging.getLogger(__name__)

        self.notify = None
        self.get_tf_affection = None
        self.get_tf = None

        load_dotenv()
        broker_host = os.getenv('BROKER_HOST', 'broker.emqx.io')
        broker_port = int(os.getenv('BROKER_PORT', "8883"))
        broker_ssl = bool(os.getenv('BROKER_SSL', "True"))
        broker_username = os.getenv('BROKER_USERNAME', '')
        broker_password = os.getenv('BROKER_PASSWORD', '')

        try:
            self.conn_params = MQTTConnectionParameters(
                host=broker_host,
                port=broker_port,
                ssl=broker_ssl,
                username=broker_username,
                password=broker_password,
                reconnect_attempts=0,
            )

            # self.conn_params = RedisConnectionParameters(
            #     host="locahost",
            #     port=6379,
            # )

            super().__init__(
                connection_params=self.conn_params,
                heartbeats=False,
                workers_rpc=10,
                **kwargs
            )
        except:
            self._logger.critical("Error in connection parameters")

        self._logger.info('[*] Commlib factory initiated from %s:%s',
                          calframe[1][1].split('/')[-1], calframe[1][2])

    def print_topics(self):
        """
        Print the topics for publishers, subscribers, RPC servers, and RPC clients.

        Returns:
            None
        """
        self._logger.warning("\nPublisher topics:")
        for topic, place in CommlibFactory.publisher_topics.items():
            self._logger.info("\t%s @ %s", topic, place)
        self._logger.warning("Subscriber topics:")
        for topic, place in CommlibFactory.subscriber_topics.items():
            self._logger.info("\t%s @ %s", topic, place)
        self._logger.warning("RPC server topics:")
        for topic, place in CommlibFactory.rpc_server_topics.items():
            self._logger.info("\t%s @ %s", topic, place)
        self._logger.warning("RPC client topics:")
        for topic, place in CommlibFactory.rpc_client_topics.items():
            self._logger.info("\t%s @ %s", topic, place)
        self._logger.warning("Action server topics:")
        for topic, place in CommlibFactory.action_server_topics.items():
            self._logger.info("\t%s @ %s", topic, place)
        self._logger.warning("Action client topics:")
        for topic, place in CommlibFactory.action_client_topics.items():
            self._logger.info("\t%s @ %s", topic, place)
        self._logger.info("")

    def notify_ui(self, type_ = None, data = None):
        """
        Notify the UI with a specific type and data.

        Args:
            type (str, optional): The type of notification to send. Defaults to None.
            data (any, optional): The data to include in the notification. Defaults to None.

        Returns:
            None
        """
        if self.notify is not None:
            self.notify.publish({
                'type': type_,
                'data': data
            })
            self._logger.info("UI inform %s: %s", type, data)

    def inform(self, broker, topic, type_, extras = ""):
        """
        Logs an informational message about a communication event.

        Args:
            broker (str): The broker involved in the communication.
            topic (str): The topic of the communication.
            type (str): The type of communication event.
            extras (str, optional): Additional information about the event. Defaults to an empty string.

        Returns:
            None
        """
        self._logger.info(
            "%s::%s <%s> @ %s", broker, type_, topic, extras if extras != '' else '-'
        )

    def getPublisher(self, broker = "mqtt", topic = None, auto_run = True):
        """
        Creates and runs a publisher for the specified broker and topic.
        Args:
            broker (str): The type of broker to use. Default is "mqtt".
            topic (str, optional): The topic to publish to. Default is None.
        Returns:
            Publisher: An instance of the created publisher.
        Side Effects:
            - Runs the created publisher.
            - Logs information about the publisher creation.
            - Increments the count of publishers for the specified broker in the stats.
        """
        ret = self.create_publisher(
            topic = topic
        )
        if auto_run:
            ret.run()

        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        # self.inform(broker, topic, "Publisher", f"{calframe[1][1].split('/')[-1]}:{calframe[1][2]}")
        CommlibFactory.stats[broker]['publishers'] += 1
        if topic in CommlibFactory.publisher_topics:
            CommlibFactory.publisher_topics[topic].append(f"{calframe[1][1].split('/')[-1]}:{calframe[1][2]}")
        else:
            CommlibFactory.publisher_topics[topic] = [f"{calframe[1][1].split('/')[-1]}:{calframe[1][2]}"]
        return ret

    def getSubscriber(self, broker = "mqtt", topic = None, callback = None, auto_run = True):
        """
        Creates and runs a subscriber for the specified broker and topic, and logs the creation.

        Args:
            broker (str): The type of broker to use (default is "mqtt").
            topic (str): The topic to subscribe to (default is None).
            callback (function): The callback function to handle incoming messages (default is None).

        Returns:
            object: The created subscriber instance.

        Side Effects:
            - Runs the subscriber.
            - Logs the creation of the subscriber.
            - Increments the subscriber count in CommlibFactory.stats for the specified broker.
        """
        ret = self.create_subscriber(
            topic = topic,
            on_message = callback
        )
        if auto_run:
            ret.run()
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        # self.inform(broker, topic, "Subscriber", 
                    # f"{calframe[1][1].split('/')[-1]}:{calframe[1][2]}")
        CommlibFactory.stats[broker]['subscribers'] += 1
        if topic in CommlibFactory.subscriber_topics:
            CommlibFactory.subscriber_topics[topic].append(f"{calframe[1][1].split('/')[-1]}:{calframe[1][2]}")
        else:
            CommlibFactory.subscriber_topics[topic] = [f"{calframe[1][1].split('/')[-1]}:{calframe[1][2]}"]
        return ret

    def getRPCService(self, broker = "mqtt", rpc_name = None, callback = None, auto_run = True):
        """
        Creates and runs an RPC service, then informs the broker about the new service.

        Args:
            broker (str): The type of broker to use (default is "mqtt").
            rpc_name (str, optional): The name of the RPC service. Defaults to None.
            callback (callable, optional): The callback function to handle requests. Defaults to None.

        Returns:
            RPCService: The created and running RPC service instance.
        """
        ret = self.create_rpc(
            on_request = callback,
            rpc_name = rpc_name
        )
        if auto_run:
            ret.run()
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        # self.inform(broker, rpc_name, "RPCService", 
                    # f"{calframe[1][1].split('/')[-1]}:{calframe[1][2]}")
        CommlibFactory.stats[broker]['rpc servers'] += 1
        if rpc_name in CommlibFactory.rpc_server_topics:
            CommlibFactory.rpc_server_topics[rpc_name].append(f"{calframe[1][1].split('/')[-1]}:{calframe[1][2]}")
        else:
            CommlibFactory.rpc_server_topics[rpc_name] = [f"{calframe[1][1].split('/')[-1]}:{calframe[1][2]}"]
        return ret

    def getRPCClient(self, broker = "mqtt", rpc_name = None, auto_run = True):
        """
        Creates and runs an RPC client, informs about its creation, and updates the statistics.

        Args:
            broker (str): The type of broker to use. Defaults to "mqtt".
            rpc_name (str, optional): The name of the RPC client. Defaults to None.

        Returns:
            object: The created and running RPC client instance.
        """
        ret = self.create_rpc_client(
            rpc_name = rpc_name
        )
        if auto_run:
            ret.run()
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        # self.inform(broker, rpc_name, "RPCClient", 
        #             f"{calframe[1][1].split('/')[-1]}:{calframe[1][2]}")
        CommlibFactory.stats[broker]['rpc clients'] += 1
        if rpc_name in CommlibFactory.rpc_client_topics:
            CommlibFactory.rpc_client_topics[rpc_name].append(f"{calframe[1][1].split('/')[-1]}:{calframe[1][2]}")
        else:
            CommlibFactory.rpc_client_topics[rpc_name] = [f"{calframe[1][1].split('/')[-1]}:{calframe[1][2]}"]
        return ret

    def getActionServer(self, broker = "mqtt", action_name = None, callback = None, auto_run = True):
        """
        Creates and runs an action server, and logs its creation.

        Parameters:
        broker (str): The type of broker to use (default is "mqtt").
        action_name (str): The name of the action (default is None).
        callback (function): The callback function to be called on goal (default is None).

        Returns:
        ActionServer: The created and running action server instance.
        """
        ret = self.create_action(
            on_goal = callback,
            action_name = action_name
        )
        if auto_run:
            ret.run()
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        # self.inform(broker, action_name, "ActionServer", 
        #             f"{calframe[1][1].split('/')[-1]}:{calframe[1][2]}")
        CommlibFactory.stats[broker]['action servers'] += 1
        if action_name in CommlibFactory.action_server_topics:
            CommlibFactory.action_server_topics[action_name].append(f"{calframe[1][1].split('/')[-1]}:{calframe[1][2]}")
        else:
            CommlibFactory.action_server_topics[action_name] = [f"{calframe[1][1].split('/')[-1]}:{calframe[1][2]}"]
        return ret

    def getActionClient(self, broker = "mqtt", action_name = None, auto_run = True):
        """
        Creates and runs an action client, then logs the action and updates statistics.

        Args:
            broker (str): The type of broker to use. Defaults to "mqtt".
            action_name (str, optional): The name of the action. Defaults to None.

        Returns:
            ActionClient: The created and running action client instance.

        Side Effects:
            - Logs the action client creation with the broker, action name, and caller information.
            - Increments the count of action clients in the statistics for the specified broker.
        """
        ret = self.create_action_client(
            action_name = action_name
        )
        if auto_run:
            ret.run()
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        # self.inform(broker, action_name, "ActionClient", 
        #             f"{calframe[1][1].split('/')[-1]}:{calframe[1][2]}")
        CommlibFactory.stats[broker]['action clients'] += 1
        if action_name in CommlibFactory.action_client_topics:
            CommlibFactory.action_client_topics[action_name].append(f"{calframe[1][1].split('/')[-1]}:{calframe[1][2]}")
        else:
            CommlibFactory.action_client_topics[action_name] = [f"{calframe[1][1].split('/')[-1]}:{calframe[1][2]}"]
        return ret
