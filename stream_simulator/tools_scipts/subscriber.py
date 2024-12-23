"""
File that subscribes to a topic.
"""
#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import time

from stream_simulator.connectivity import CommlibFactory

def subscriber_callback(message):
    """
    Callback function to handle incoming messages.

    Args:
        message (str): The message received from the AMQP subscriber.
        meta (dict): Metadata associated with the message.

    Returns:
        None
    """
    print(f">> {message}")

cmlib = CommlibFactory(node_name="Test")
SUB = cmlib.getSubscriber(
    topic=sys.argv[1],
    callback=subscriber_callback,
    broker=sys.argv[2]
)

SUB.run()
print(f"Subscribed to {sys.argv[1]} with broker {sys.argv[2]}")
while True:
    time.sleep(1)
