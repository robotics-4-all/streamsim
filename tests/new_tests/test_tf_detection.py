#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import traceback
import time

from stream_simulator.connectivity import CommlibFactory

# name: the name of the device
# type: [sound, language, emotion, speech2Text] for microphone
# type: [human, gender, age, emotion, motion, qr, barcode, text, color, robot] for camera

try:
    # Get simulation actors
    sim_name = "streamsim.123"
    cfact = CommlibFactory(node_name = "Test")
    cl = cfact.getRPCClient(
        rpc_name = f"{sim_name}.tf.simulated_detection"
    )
    print(cl.call({
        'name': sys.argv[1],
        'type': sys.argv[2]
    }))
    time.sleep(1)
except: # pylint: disable=bare-except
    traceback.print_exc(file=sys.stdout)
    exit(1)
