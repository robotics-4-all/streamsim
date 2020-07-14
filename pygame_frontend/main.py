#!/usr/bin/python
# -*- coding: utf-8 -*-

import pygame
import time
import random
import json
import os
import math
import threading

from stream_simulator import Logger
from stream_simulator import ConnParams

if ConnParams.type == "amqp":
    from commlib_py.transports.amqp import Subscriber, RPCClient, Publisher
elif ConnParams.type == "redis":
    from commlib_py.transports.redis import Subscriber, RPCClient, Publisher

class Frontend:
    def __init__(self):
        pygame.init()

        try:
            self.namespace = os.environ['TEKTRAIN_NAMESPACE']
        except:
            self.logger.error("No TEKTRAIN_NAMESPACE environmental variable found. Please set it!")
            exit(0)

        self.dir_path = os.path.dirname(os.path.realpath(__file__))

        self.robot_img = pygame.image.load(self.dir_path + '/imgs/Robot.png')
        self.human_img = pygame.image.load(self.dir_path + '/imgs/Human.png')
        self.moving_human_img = pygame.image.load(self.dir_path + '/imgs/Moving_Human.png')
        self.speaking_human_img = pygame.image.load(self.dir_path + '/imgs/Speaking_Human.png')
        self.moving_speaking_human_img = pygame.image.load(self.dir_path + '/imgs/Moving_Speaking_Human.png')
        self.barcode_img = pygame.image.load(self.dir_path + '/imgs/Barcode.png')
        self.qr_img = pygame.image.load(self.dir_path + '/imgs/QR_code.png')
        self.sign_img = pygame.image.load(self.dir_path + '/imgs/Sign.png')
        self.sound_img = pygame.image.load(self.dir_path + '/imgs/Sound.png')
        self.colour_img = pygame.image.load(self.dir_path + '/imgs/Colour.png')

        self.robot_color = [0, 0, 0]
        self.robot_color_wipe = [0, 0, 0]
        self.wipe_timeout = 0

        self.robot_pose = {"x": 0, "y": 0, "theta": 0}

        self.screen = pygame.display.set_mode((100, 100))
        self.screen.fill((255, 255, 255))
        self.clock = pygame.time.Clock()

        # Subscribers
        self.new_w_sub = Subscriber(conn_params=ConnParams.get(), topic = "world:details", on_message = self.new_world)

        self.robot_pose_sub = Subscriber(conn_params=ConnParams.get(), topic = "robot_1:pose", on_message = self.robot_pose_update)

        self.leds_set_sub = Subscriber(conn_params=ConnParams.get(), topic = "robot_1:leds", on_message = self.leds_set_callback)

        self.leds_wipe_sub = Subscriber(conn_params=ConnParams.get(), topic = "robot_1:leds_wipe", on_message = self.leds_wipe_callback)

        self.detections_sub = Subscriber(conn_params=ConnParams.get(), topic = "robot_1:detection", on_message = self.detections_callback)

        # Subscribers starting
        self.new_w_sub.run()
        self.robot_pose_sub.run()
        self.leds_set_sub.run()
        self.leds_wipe_sub.run()
        self.detections_sub.run()

        # RPC clients
        self.env_rpc_client = RPCClient(conn_params=ConnParams.get(), rpc_name="robot_1:env")
        self.devices_rpc_client = RPCClient(conn_params=ConnParams.get(), rpc_name=self.namespace + '/nodes_detector/get_connected_devices')

        self.font = pygame.font.Font('freesansbold.ttf', 9)

        self.linear = 0
        self.angular = 0

    def new_world(self, message, meta):
        self.done = True

        self.world = message
        self.resolution = self.world["map"]["resolution"]

        self.screen = pygame.display.set_mode((self.world["map"]["width"], self.world["map"]["height"]))
        self.screen.fill((255, 255, 255))

        pygame.display.set_caption("StreamSim - Frontend")
        pygame.font.init()
        self.font = pygame.font.SysFont(None, 30)

        self.clock = pygame.time.Clock()

        self.temperature = None

        # Get devices
        self.devices = self.devices_rpc_client.call(data = None)
        for d in self.devices['devices']:
            if d['type'] == 'SKID_STEER':
                self.vel_publisher = Publisher(conn_params=ConnParams.get(), topic=  d['base_topic'] + "/set")

        self.start()

    def robot_pose_update(self, message, meta):
        self.robot_pose = message

    def detections_callback(self, message, meta):
        self.detection_info = message

    def leds_set_callback(self, message, meta):
        res = message
        self.robot_color = [
            res["r"],
            res["g"],
            res["b"]
        ]

    def leds_wipe_callback(self, message, meta):
        res = message
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
                if event.type == pygame.KEYDOWN and event.key == pygame.K_UP:
                    self.linear += 0.1
                    print("GOING UP!")
                    self.vel_publisher.publish({"linear": self.linear, "angular": self.angular})
                if event.type == pygame.KEYDOWN and event.key == pygame.K_DOWN:
                    self.linear -= 0.1
                    self.vel_publisher.publish({"linear": self.linear, "angular": self.angular})
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RIGHT:
                    self.angular += 0.1
                    self.vel_publisher.publish({"linear": self.linear, "angular": self.angular})
                if event.type == pygame.KEYDOWN and event.key == pygame.K_LEFT:
                    self.angular -= 0.1
                    self.vel_publisher.publish({"linear": self.linear, "angular": self.angular})
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    self.angular = 0
                    self.linear = 0
                    self.vel_publisher.publish({"linear": self.linear, "angular": self.angular})

            self.screen.fill((255, 255, 255))

            place = 20
            try:
                for d in self.detection_info:
                    if self.detection_info[d] is True:
                        text = self.font.render(d, True, (100,100,255), (255, 255, 255))
                        textRect = text.get_rect()
                        textRect.center = (self.world["map"]["width"] - 100, place)
                        place += 20
                        self.screen.blit(text, textRect)
            except:
                pass

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

            for human in self.world["actors"]["humans"]:
                img = None
                if human["move"] == 0 and human["sound"] == 0:
                    img = self.human_img
                if human["move"] == 1 and human["sound"] == 0:
                    img = self.moving_human_img
                if human["move"] == 0 and human["sound"] == 1:
                    img = self.speaking_human_img
                if human["move"] == 1 and human["sound"] == 1:
                    img = self.moving_speaking_human_img

                self.screen.blit(pygame.transform.rotozoom(img, 0, 0.1), (human["x"], human["y"]))

            for actor in self.world["actors"]["sound_sources"]:
                self.screen.blit(pygame.transform.rotozoom(self.sound_img, 0, 0.1), (actor["x"] - 30, actor["y"] - 30))
            for actor in self.world["actors"]["qrs"]:
                self.screen.blit(pygame.transform.rotozoom(self.qr_img, 0, 0.1), (actor["x"] - 30, actor["y"] - 30))
            for actor in self.world["actors"]["barcodes"]:
                self.screen.blit(pygame.transform.rotozoom(self.barcode_img, 0, 0.1), (actor["x"] - 30, actor["y"] - 30))
            for actor in self.world["actors"]["colors"]:
                self.screen.blit(pygame.transform.rotozoom(self.colour_img, 0, 0.1), (actor["x"] - 30, actor["y"] - 30))
            for actor in self.world["actors"]["texts"]:
                self.screen.blit(pygame.transform.rotozoom(self.sign_img, 0, 0.1), (actor["x"] - 30, actor["y"] - 30))

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
