"""
File that initializes an AppMakerExecutor.
"""

import os
import sys
import time
import logging
from dotenv import load_dotenv
import multiprocessing

from stream_simulator.connectivity import CommlibFactory

from stream_simulator import Simulator

COLAB = False
try:
    from google.colab import drive # type: ignore # pylint: disable=unused-import
    COLAB = True
except ImportError:
    pass

if COLAB:
    # Clear any existing logging handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        format='%(levelname)s : %(name)s : %(message)s',
        level=logging.DEBUG,
        force=True
    )
else:
    logging.basicConfig(
        format='%(levelname)s : %(name)s : %(message)s',
        level=logging.DEBUG
    )

def start_executor(uid, message):
    """
    Initializes and starts the AppMakerExecutor with the provided parameters.

    Args:
        uid (str): Unique identifier for the executor instance.
        feedback_topic (str): Topic for feedback communication.
        conn_params (dict): Connection parameters for the executor.
        message (str): Message containing the model to be loaded and executed.

    Returns:
        None
    """
    amexe = Simulator( # pylint: disable=not-callable
        uid=uid
    )
    amexe.configuration_callback(message)
    while True:
        time.sleep(0.1)

class StreamsimExecutor:
    """
    A class that initializes an Simulation.
    """
    def __init__(self, uid):
        self.uid = uid
        self.commlib_node = None
        self.conn_params = None
        self.commlib_factory = None
        self.local_commlib_factory = None
        self.configuration_rpc_server = None
        self.process = None
        self.logger = logging.getLogger(__name__)

    def on_message(self, message):
        """
        Handles incoming messages.

        Args:
            message (dict): The message received.

        Returns:
            None
        """
        try:
            self.logger.info("Received model")
            # Kill the previous process

            self.process = multiprocessing.Process(
                target=start_executor,
                args=(self.uid, message)
            )
            self.process.start()
            self.process.join()
            self.logger.info("All done")
        except Exception as e: # pylint: disable=broad-except
            self.logger.error("Error on message: %s", e)

    def run(self):
        """
        Runs the StreamsimExecutor.

        Returns:
            None
        """

        # ------ MQTT interface for locsys
        self.commlib_factory = CommlibFactory(
            node_name = "Streamsim mqtt manager",
            interface = "mqtt",
        )
        self.commlib_factory.create_subscriber(
            topic=f'streamsim.{self.uid}.set_configuration',
            on_message=self.on_message
        )
        self.logger.warning("Subscribed to %s", f'streamsim.{self.uid}.set_configuration')
        self.commlib_factory.run()

        # ------ Local interface for appdeployer
        self.local_commlib_factory = CommlibFactory(
            node_name="Streamsim local manager",
        )
        self.configuration_rpc_server = self.local_commlib_factory.get_rpc_service(
            callback = self.on_message,
            rpc_name = f"streamsim.{self.uid}.set_configuration_local"
        )
        self.commlib_factory.get_rpc_service(
            callback = self.reset,
            rpc_name = f'streamsim.{self.uid}.reset'
        )
        self.local_commlib_factory.run()

    def reset(self, _):
        """
        Resets the executor.

        Args:
            message (dict): The message received.

        Returns:
            None
        """
        if self.process:
            self.process.terminate()
        self.logger.info("Executor reset")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("You must provide a UID as argument:")
        print(">> python3 main.py UID")
        exit(0)

    _uid = sys.argv[1]
    sexec = StreamsimExecutor(_uid)
    sexec.run()
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        try:
            sexec.commlib_node.stop()
        except Exception as e: # pylint: disable=broad-except
            print("Error: ", e)
        print("Bye!")
        exit(0)
