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

class Frontend:
    def __init__(self):
        pygame.init()

        self.dir_path = os.path.dirname(os.path.realpath(__file__))
        self.robot_img = pygame.image.load(self.dir_path + '/imgs/Robot.png')

        self.screen = pygame.display.set_mode((100, 100))
        self.screen.fill((255, 255, 255))
        self.clock = pygame.time.Clock()

        self.new_w_sub = Subscriber(topic = "world:details", func = self.new_world)
        self.robot_pose_sub = Subscriber(topic = "robot_1:pose", func = self.robot_pose_update)
        self.new_w_sub.start()
        self.robot_pose_sub.start()

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

        self.start()

    def robot_pose_update(self, message):
        self.robot_pose = json.loads(message['data'])

    def start(self):
        self.done = False
        while not self.done:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.done = True

            self.screen.fill((255, 255, 255))

            # Print stuff
            for l in self.world["map"]["obstacles"]["lines"]:
                pygame.draw.line(self.screen, (0,0,0), \
                    (l["x1"], l["y1"]),
                    (l["x2"], l["y2"])
                )

            self.screen.blit(\
                pygame.transform.rotozoom(self.robot_img,\
                - (self.robot_pose["theta"] * 180) / math.pi, \
                100.0 /  1024.0), \
                (self.robot_pose["x"] / self.resolution - 30,\
                self.robot_pose["y"] / self.resolution - 30))

            pygame.display.flip()
            pygame.display.update()
            self.clock.tick(500000)

        pygame.quit()

sim = Frontend()
while True:
    time.sleep(1)
