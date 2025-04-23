#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This script initializes and starts a stream simulator.
Modules:
    time: Provides various time-related functions.
    logging: Provides a flexible framework for emitting log messages from Python programs.
    stream_simulator: Custom module that contains the Simulator class.
Usage:
    Run the script to start the simulator. The simulator will continue running until a 
    keyboard interrupt (Ctrl+C) is received.
Classes:
    Simulator: A class from the stream_simulator module that handles the simulation process.
"""

import time
import logging
import sys
import os
from multiprocessing import Process, Event

from stream_simulator import Simulator
from stream_simulator.connectivity import CommlibFactory


def start_simulation(_uid, precision_mode, message, stop_event):
    """
    Initializes and starts the simulator with the provided parameters.

    Args:
        _uid (str): Unique identifier for the simulator instance.
        precision_mode (bool): Whether precision mode is enabled.
        message (str): Message used to configure the simulator.
        stop_event (multiprocessing.Event): Event to signal stopping the simulator.

    Returns:
        None
    """
    logging.warning("Starting simulator in subprocess")
    Simulator(uid=_uid, precision_mode=precision_mode, message=message)
    while not stop_event.is_set():
        time.sleep(1)


class MainStreamsim:
    """
    Main class for the Stream Simulator.
    This class is responsible for initializing and starting the simulator.
    """
    def __init__(self, _uid, precision_mode):
        self.uid = _uid
        self.precision_mode = precision_mode
        self.commlib_factory = CommlibFactory(node_name="MainStreamsim")
        self.process = None
        self.stop_event = None

        self.configuration_rpc_server = self.commlib_factory.get_rpc_service(
            callback=self.configuration_callback,
            rpc_name=f"streamsim.{_uid}.set_configuration_local"
        )

        self.devices_rpc_server = self.commlib_factory.get_rpc_service(
            callback=self.reset,
            rpc_name=f"streamsim.{_uid}.reset"
        )

        self.commlib_factory.run()

    def reset(self, _):
        """
        Reset the simulator.
        This function is called when a reset message is received.
        """
        logging.info("Reset callback received")
        if self.process:
            self.process.terminate()
            self.process.join()
        logging.info("Out: Execution finished")

    def configuration_callback(self, message):
        """
        Callback function for handling configuration messages.
        This function is called when a configuration message is received.
        """
        logging.info("Configuration callback received")
        try:
            self.stop_event = Event()
            self.process = Process(target=start_simulation, args=(self.uid, self.precision_mode, message, self.stop_event))
            self.process.start()
        except Exception as e:
            logging.error("Error on message: %s", e)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("You must provide a UID as argument:")
        print(">> python3 main.py UID")
        exit(0)

    uid = sys.argv[1]
    _precision_mode = sys.argv[2] if len(sys.argv) > 2 else False
    if _precision_mode:
        logging.info(">> Precision mode enabled.")

    COLAB = False
    try:
        from google.colab import drive  # type: ignore # pylint: disable=unused-import
        COLAB = True
    except ImportError:
        pass

    if COLAB:
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        logging.basicConfig(
            format='%(levelname)s : %(name)s : %(message)s',
            force=True
        )
    else:
        logging.basicConfig(
            format='%(levelname)s : %(name)s : %(message)s',
        )

    ZERO_LOGS = int(os.getenv("STREAMSIM_ZERO_LOGS", 0))
    LOG_LEVEL = os.getenv("STREAMSIM_LOG_LEVEL", "INFO")

    if ZERO_LOGS:
        logging.disable()
    else:
        logging.getLogger().setLevel(LOG_LEVEL)

    try:
        m = MainStreamsim(uid, _precision_mode)
        logging.info("Stream simulator started")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Bye!")
        exit(0)