import unittest
import sys, traceback
import time
import os

from stream_simulator.connectivity import CommlibFactory

import threading
import logging


class TestTF(unittest.TestCase):
    def setUp(self):
        self._sim_name = "streamsim"
        self._sub_alive = True

    def test_tf(self):
        for name, step in self._steps():
            try:
                step()
            except Exception as e:
                self.fail("{} failed ({}: {})".format(step, type(e), e))

    def _steps(self):
        for name in dir(self):
            if name.startswith("step"):
                yield name, getattr(self, name) 

    def step_1_tf_declare(self):
        try:
            get_declarations_topic = self._sim_name + ".tf.get_declarations"

            rpc_client = CommlibFactory.getRPCClient(
                broker = "redis",
                rpc_name = get_declarations_topic
            )
            
            self.response = rpc_client.call({})

            print(self.response)            
        except:
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)

    def step_2_tf_get_affections(self):
        try:
            get_affections_topic = self._sim_name + ".tf.get_affections"

            rpc_client = CommlibFactory.getRPCClient(
                broker = "redis",
                rpc_name = get_affections_topic
            )

            for d in self.response['declarations']:
                device_name = d["name"]

                msg = {
                    "name": device_name
                }
                
                response = rpc_client.call(msg)

                print(f"tf of {device_name}: {response}")
        except:
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)

    def step_3_tf_get_tf(self):
        try:
            get_tf_topic = self._sim_name + ".tf.get_tf"

            rpc_client = CommlibFactory.getRPCClient(
                broker = "redis",
                rpc_name = get_tf_topic
            )
            
            for d in self.response['declarations']:
                device_name = d["name"]

                msg = {
                    "name": device_name
                }
                
                response = rpc_client.call(msg)

                print(f"tf of {device_name}: {response}")
        except:
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)

    def step_4_tf_detections_notify(self):
        try:
            detections_notify_topic = self._sim_name + ".tf.detections.notify"

            self._sub_thread = threading.Thread(target=self._subscriber, args=(detections_notify_topic,), daemon=True)
            self._sub_thread.start()
            
        except:
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)

    def step_5_tf_sim_detection(self):
        try:
            sim_detection_topic = self._sim_name + ".tf.simulated_detection"

            rpc_client = CommlibFactory.getRPCClient(
                broker = "redis",
                rpc_name = sim_detection_topic
            )
            
            for d in self.response['declarations']:
                device_name = d["name"]
                device_type = d["type"]

                msg = {
                    "name": device_name,
                    "type": device_type
                }
                
                response = rpc_client.call(msg)

                print(f"tf of {device_name}: {response}")
        except:
            traceback.print_exc(file=sys.stdout)
            self.assertTrue(False)

    def _subscriber(self, topic):

        def sub_callback(message, meta):
            print("Subscriber received: ", message)
        
        subscriber = CommlibFactory.getSubscriber(
            broker = "redis",
            topic = topic,
            callback = sub_callback
        )
        subscriber.run()

        while self._sub_alive:
            time.sleep(0.1)

        subscriber.stop()

    def tearDown(self):
        self._sub_alive = False
        self._sub_thread.join()

if __name__ == "__main__":
    unittest.main()
