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
Functions:
    None
Exceptions:
    KeyboardInterrupt: Catches the keyboard interrupt to stop the simulator gracefully.
Logging:
    Configured to display log messages with the format 'LEVEL : LOGGER NAME : MESSAGE' at 
    the DEBUG level.
"""
#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging
import sys
import os

from stream_simulator import Simulator

COLAB = False
try:
    from google.colab import drive # type: ignore # pylint: disable=unused-import
    COLAB = True
except ImportError:
    pass

if len(sys.argv) < 2:
    print("You must provide a UID as argument:")
    print(">> python3 main.py UID")
    exit(0)

uid = sys.argv[1]
_precision_mode = sys.argv[2] if len(sys.argv) > 2 else False
if _precision_mode:
    print(">> Precision mode enabled.")

if COLAB:
    # Clear any existing logging handlers
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

if ZERO_LOGS: logging.disable()
else: logging.getLogger().setLevel(LOG_LEVEL)

s = Simulator(uid = uid, precision_mode=_precision_mode)

# While keyboard interrupt is not received, keep the simulator running
try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    s.stop()
    print("Bye!")
    exit(0)
