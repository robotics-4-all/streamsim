"""
This script initializes and starts a stream simulator.
Modules:
    time: Provides various time-related functions.
    logging: Provides a flexible framework for emitting log messages from Python programs.
    stream_simulator: Custom module that contains the Simulator class.
Usage:
    Run the script to start the simulator. The simulator will continue running until a keyboard interrupt (Ctrl+C) is received.
Classes:
    Simulator: A class from the stream_simulator module that handles the simulation process.
Functions:
    None
Exceptions:
    KeyboardInterrupt: Catches the keyboard interrupt to stop the simulator gracefully.
Logging:
    Configured to display log messages with the format 'LEVEL : LOGGER NAME : MESSAGE' at the DEBUG level.
"""
#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging

from stream_simulator import Simulator

COLAB = False
try:
    from google.colab import drive # pylint: disable=unused-import
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

s = Simulator()

# While keyboard interrupt is not received, keep the simulator running
try:
    while True:
        time.sleep(0.25)
except KeyboardInterrupt:
    s.stop()
    print("Bye!")
    exit(0)
