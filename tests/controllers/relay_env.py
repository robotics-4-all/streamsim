#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import sys, traceback
import time
import os

from stream_simulator.connectivity import CommlibFactory

class Test_relay_env(unittest.TestCase):
    def setUp(self):
        pass

    def test_correct_input(self):
        try:
            devices = self.rapi.devicesObj.devices
            for i in devices:
                d = devices[i]
                if d == None:
                    continue

                if d.type == Devices.ENCODER:

                    # Get measurement
                    out = self.rapi.getEncoderMeasurement(InputMessage({
                        'deviceId': d.id,
                        'fromIndex': 0,
                        'toIndex': -1,
                        'fromTime': None
                    }))
                    out.print()

                    # Data format
                	  # measurements has a <class 'list'>:
                	  #   [0]  has a <class 'dict'>:
                	  #     deviceId has a <class 'str'>:
                	  #       id_399c901f4baf4d279c28afcc54c0c434 is <class 'str'> [84 bytes]
                	  #     timestamp has a <class 'float'>:
                	  #       1576671679.6556659 is <class 'float'> [24 bytes]
                	  #     value has a <class 'float'>:
                	  #       1.0 is <class 'float'> [24 bytes]
                	  #   [1]  has a <class 'dict'>:
                	  #     deviceId has a <class 'str'>:
                	  #       id_399c901f4baf4d279c28afcc54c0c434 is <class 'str'> [84 bytes]
                	  #     timestamp has a <class 'float'>:
                	  #       1576671678.6551247 is <class 'float'> [24 bytes]
                	  #     value has a <class 'float'>:
                	  #       1.0 is <class 'float'> [24 bytes]

                    now = time.time()
                    self.assertNotEqual(out.data, {})
                    self.assertEqual('measurements' in out.data, True)
                    self.assertEqual(len(out.data['measurements']), 2)
                    for datum in out.data['measurements']:
                        self.assertEqual('deviceId' in datum, True)
                        self.assertEqual('timestamp' in datum, True)
                        self.assertEqual('value' in datum, True)
                        self.assertLess(datum['timestamp'], now)
                        # self.assertLess(datum['value'], 40)
                        # self.assertGreater(datum['value'], -20)


        except:
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
