#!/usr/bin/python
# -*- coding: utf-8 -*-

import pygame
import time
import random
import json
import os
import math
import threading

from stream_simulator import Subscriber
from stream_simulator import RpcClient

class Frontend:
    def __init__(self):
        pygame.init()

        self.dir_path = os.path.dirname(os.path.realpath(__file__))
        self.robot_img = pygame.image.load(self.dir_path + '/imgs/Robot.png')
        self.robot_color = [0, 0, 0]
        self.robot_color_wipe = [0, 0, 0]
        self.wipe_timeout = 0

        self.screen = pygame.display.set_mode((100, 100))
        self.screen.fill((255, 255, 255))
        self.clock = pygame.time.Clock()

        # Subscribers
        self.new_w_sub = Subscriber(topic = "world:details", func = self.new_world)
        self.robot_pose_sub = Subscriber(topic = "robot_1:pose", func = self.robot_pose_update)
        self.leds_set_sub = Subscriber(topic = "robot_1:leds", func = self.leds_set_callback)
        self.leds_wipe_sub = Subscriber(topic = "robot_1:leds_wipe", func = self.leds_wipe_callback)

        # Subscribers starting
        self.new_w_sub.start()
        self.robot_pose_sub.start()
        self.leds_set_sub.start()
        self.leds_wipe_sub.start()

        # RPC clients
        self.env_rpc_client = RpcClient(topic = "robot_1:env")

    def new_world(self, message):
        self.done = True

        self.world = json.loads(json.loads(message['data'])) # Check this!
        self.resolution = self.world["map"]["resolution"]

        self.screen = pygame.display.set_mode((self.world["map"]["width"], self.world["map"]["height"]))
        self.screen.fill((255, 255, 255))

        pygame.display.set_caption("StreamSim - Frontend")
        pygame.font.init()
        self.font = pygame.font.SysFont(None, 30)

        self.clock = pygame.time.Clock()

        self.temperature = None

        print("Press \"t\" to trigger env get")

        self.start()

    def robot_pose_update(self, message):
        self.robot_pose = json.loads(message['data'])

    def leds_set_callback(self, message):
        res = json.loads(message['data'])
        self.robot_color = [
            res["r"],
            res["g"],
            res["b"]
        ]

    def leds_wipe_callback(self, message):
        res = json.loads(message['data'])
        self.robot_color_wipe = [
            res["r"],
            res["g"],
            res["b"]
        ]
        self.robot_color = [0,0,0]

    def start(self):
        self.done = False
        while not self.done:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.done = True
                if event.type == pygame.KEYDOWN and event.key == pygame.K_t:
                    print("Environmental sensor:", self.env_rpc_client.call({"from": 0, "to": 0}))

            self.screen.fill((255, 255, 255))

            # Print stuff
            for l in self.world["map"]["obstacles"]["lines"]:
                pygame.draw.line(self.screen, (0,0,0), \
                    (l["x1"], l["y1"]),
                    (l["x2"], l["y2"])
                , 5)

            self.screen.blit(\
                pygame.transform.rotozoom(self.robot_img,\
                - (self.robot_pose["theta"] * 180) / math.pi, \
                100.0 /  1024.0), \
                (self.robot_pose["x"] / self.resolution - 30,\
                self.robot_pose["y"] / self.resolution - 30))


            if self.robot_color_wipe != [0,0,0]:
                self.wipe_timeout = 100
                self.robot_color = [0,0,0]
                self.tmp_color = self.robot_color_wipe
                self.robot_color_wipe = [0,0,0]
            if self.wipe_timeout > 0:
                pygame.draw.circle(self.screen, tuple(self.tmp_color),\
                (int(self.robot_pose["x"] / self.resolution),\
                int(self.robot_pose["y"] / self.resolution)),
                10)
                self.wipe_timeout -= 1
            else:
                self.robot_color_wipe = [0,0,0]
                if self.robot_color != [0,0,0]:
                    pygame.draw.circle(self.screen, tuple(self.robot_color),\
                            (int(self.robot_pose["x"] / self.resolution),\
                            int(self.robot_pose["y"] / self.resolution)),
                            10)

            pygame.display.flip()
            pygame.display.update()
            self.clock.tick(500000)

        pygame.quit()

sim = Frontend()
while True:
    time.sleep(1)
