#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import sys, traceback
import time
import os

from stream_simulator.connectivity import CommlibFactory
import threading

class Test(unittest.TestCase):
    NORMAL_STATUS = 4
    PREEMT_STATUS = 3
    def setUp(self):
        pass

    def test_get(self):
        try:
            # Get simulation actors
            sim_name = "streamsim"
            cl = CommlibFactory.getRPCClient(
                broker = "redis",
                rpc_name = f"{sim_name}.get_device_groups"
            )
            res = cl.call({})

            robots = res["robots"]
            for r in robots:
                cl = CommlibFactory.getRPCClient(
                    broker = "redis",
                    rpc_name = f"robot.{r}.nodes_detector.get_connected_devices"
                )
                res = cl.call({})

                # Get skid steer actuator
                for s in res["devices"]:
                    if s["type"] == "SKID_STEER":
                        # create an action client
                        self.action_client = CommlibFactory.getActionClient(
                            broker = "redis",
                            action_name = s["base_topic"] + ".set"
                        )

                        # test normal execution of the action process
                        resp = self.set_action(
                            linear = 0.1,
                            rotational = 0.314,
                            duration = 3
                        )

                        # validate results
                        self.assertEqual('status' in resp, True)
                        self.assertEqual('result' in resp, True)
                        self.assertEqual(resp['status'], Test.NORMAL_STATUS)
                        self.assertEqual(resp['result'], {})           

                        # test goal preemption
                        preemt_at = 3
                        self._preemt_thread = threading.Thread(target=self.sudden_preemtion, args=(preemt_at, ), daemon=True)
                        self._preemt_thread.start()

                        resp = self.set_action(
                            linear = 0.1,
                            rotational = 0.314,
                            duration = 10
                        )

                        # validate results
                        self.assertEqual('status' in resp, True)
                        self.assertEqual('result' in resp, True)
                        self.assertEqual(resp['status'], Test.PREEMT_STATUS)
                        self.assertEqual(resp['result'], {})      
        except:
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)
    
    def set_action(self, linear, rotational, duration):
        # send an action
        self._preemt = False

        resp = self.action_client.send_goal({
            'linearVelocity': linear,
            'rotationalVelocity': rotational,
            'duration': duration
        })

        self.goal_id_play = resp['goal_id']

        while self.action_client.get_result(self.goal_id_play)["status"] == 1:
            if self._preemt:
                break
            time.sleep(0.1)
        
        final_res = self.action_client.get_result(self.goal_id_play)

        return final_res

    def sudden_preemtion(self, delay_time):
        time.sleep(delay_time)

        self.action_client.cancel_goal(self.goal_id_play)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
