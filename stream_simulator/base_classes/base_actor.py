"""
File that contains the BaseThing class.
"""
#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import threading
import time
import abc
import math

from stream_simulator.base_classes import BaseThing

class BaseActor(BaseThing):
    """
    BaseActor is a class that represents an actor in a simulation environment. It inherits from the BaseThing class and provides functionality for automating the actor's behavior based on predefined configurations.
    """
    def __init__(self, _name, package, conf, _type=None, _range=None, _properties=None, auto_start=True):
        """
        Initializes a new instance of the BaseThing class.

        Args:
            _name (str): The name of the thing.
        """
        if package["logger"] is None:
            self.logger = logging.getLogger(_name)
        else:
            self.logger = package["logger"]

        super().__init__(_name, auto_start=False)

        id_ = BaseThing.id

        info = {
            "type": _type,
            "conf": conf,
            "id": id_,
            "name": _type.lower() + "_" + str(conf["id"])
        }

        self.info = info
        self.name = info['name']
        self.range = _range
        self.pose = {
            'x': conf['x'],
            'y': conf['y'],
            'theta': None
        }
        self.resolution = package['resolution']

        self.set_tf_communication(package)

        # Class variables
        self.automation = None
        self.stopped = None
        self.active = None
        self.terminated = True
        self.state_automation_terminated = True
        self.automation_thread = None
        self.state_automation_thread = None
        self.velocities_for_target = None
        self.pois_index = None
        self.resolution = package['resolution']
        self._x = None
        self._y = None
        self._theta = None
        self.dt = None
        self.target_to_reach = None
        self.internal_pose_pub = None

        self.id = conf["id"]
        namespace = ".".join(package["tf_declare_rpc_topic"].split(".")[:2])

        # tf handling
        tf_package = {
            "type": "actor",
            "namespace": namespace,
            "subtype": _type.lower(),
            "pose": self.pose,
            "name": self.name,
            "range": self.range,
            "id": self.id,
            "properties": _properties,
            "automation_motion": True if ('automation' in conf and "points" in conf['automation']) else False,
            "automation_state": True if ('automation' in conf and "steps" in conf['automation']) else False
        }

        self.tf_declare_rpc.call(tf_package)

        # Motion pose publisher
        topic = namespace + f".actor.{_type.lower()}." + self.name + ".pose.internal"
        self.internal_pose_pub = self.commlib_factory.get_publisher(
            topic = topic
        )
        self.logger.warning("%s %s publisher is initialized: %s", _type, self.name, topic)
        # Properties publishers
        topic = namespace + f".actor.{_type.lower()}." + self.name + ".properties"
        self.internal_properties_pub = self.commlib_factory.get_publisher(
            topic = topic
        )
        self.logger.warning("%s %s properties publisher is initialized: %s", _type, self.name, topic)

        self.commlib_factory.run()

        self.automation = None if 'automation' not in conf else conf['automation']
        # Automation handling
        self.state_automation_terminated = True
        self.terminated = True

        # Automation handling
        if self.automation is not None:
            self.stopped = False
            self.active = True
            self.logger.critical("Human %s is automated", self.name)
            if 'points' in self.automation: # we have automated motion
                self.velocities_for_target = {
                    'linear': self.automation['linear'],
                    'angular': self.automation['angular']
                }
                self.pois_index = 0
                for p in self.automation['points']:
                    p['x'] *= self.resolution
                    p['y'] *= self.resolution
                self.logger.info("Human %s: automation set", self.name)
                self.logger.info("Pois: %s", self.automation['points'])
                self._x = self.pose['x'] * self.resolution
                self._y = self.pose['y'] * self.resolution
                self._theta = 0
                self.dt = 0.5
                self.target_to_reach = None

                self.terminated = False
                self.automation_thread = threading.Thread(target = self.automation_thread_loop)
                self.automation_thread.start()
            if 'steps' in self.automation: # we have state machine
                self.logger.critical("Human %s is automated with state machine", self.name)
                self.state_automation_terminated = False
                self.state_automation_thread = \
                    threading.Thread(target = self.state_automation_thread_loop)
                self.state_automation_thread.start()

    def get_logger(self):
        """
        Retrieve the logger instance associated with this object.

        Returns:
            logging.Logger: The logger instance.
        """
        return self.logger

    def state_automation_thread_loop(self):
        """
        Manages the automation loop for the relay device.
        This method runs in a separate thread and controls the relay based on the 
        predefined automation steps. It supports reversing the steps and looping 
        through them based on the configuration.
        """
        self.logger.warning("%s state automation starts", self.name)
        self.stopped = False
        automation_steps = self.automation["steps"]
        step_index = -1
        reverse_mode = False
        while self.active:
            step_index += 1
            if step_index >= len(automation_steps):
                if self.automation["reverse"] and reverse_mode is False:
                    automation_steps.reverse()
                    step_index = 1
                    reverse_mode = True
                elif self.automation["reverse"] and reverse_mode is True:
                    if self.automation["loop"]:
                        automation_steps.reverse()
                        step_index = 1
                        reverse_mode = False
                    else:
                        self.active = False
                        break
                elif self.automation["reverse"] is False and self.automation["loop"]:
                    step_index = 0
                else:
                    self.active = False
                    break
            step = automation_steps[step_index]

            self.update_class_state_variables(step)

            sleep = step['duration']
            while sleep > 0 and self.active: # to be preemptable
                time.sleep(0.1)
                sleep -= 0.1

        self.state_automation_terminated = True
        self.logger.warning("Light %s automation stops", self.name)

    @abc.abstractmethod
    def update_class_state_variables(self, step):
        """
        Updates the class state variables from the current state dictionary.

        This method assigns the values from the `state` dictionary to the corresponding
        class attributes: motion, sound, language, range
        """
        return None

    def automation_thread_loop(self):
        """
        Automation thread loop for simulating human movement through predefined points of 
        interest (POIs).
        This method runs in a loop until the `stopped` attribute is set to True. It updates 
        the position and orientation of the human actor based on the target POIs and the 
        specified automation settings.
        The movement can be reversed and looped based on the configuration.
        """
        self.logger.warning("Started %s automation thread", self.name)
        t = time.time()

        has_target = False
        reverse_mode = False
        logging_counter = 0
        self.pois_index = -1
        while self.stopped is False:
            # update time interval
            dt = time.time() - t
            t = time.time()

            prev_x = self._x
            prev_y = self._y
            prev_th = self._theta

            # Mock mode here
            if has_target is False:
                if self.pois_index == len(self.automation['points']) - 1:
                    self.logger.warning("Reached the last POI")
                    if self.automation['reverse'] is True and reverse_mode is False:
                        self.automation['points'].reverse()
                        self.logger.critical("Reversed POIs %s", self.automation['points'])
                        self.pois_index = 0
                        self.target_to_reach = {
                            'x': self.automation['points'][self.pois_index]['x'],
                            'y': self.automation['points'][self.pois_index]['y']
                        }
                        has_target = True
                        reverse_mode = True
                    elif self.automation['reverse'] is True and reverse_mode is True:
                        if self.automation['loop'] is True:
                            self.automation['points'].reverse()
                            self.logger.critical("In loop: Reversed POIs %s", \
                                self.automation['points'])
                            self.pois_index = 0
                            self.target_to_reach = {
                                'x': self.automation['points'][self.pois_index]['x'],
                                'y': self.automation['points'][self.pois_index]['y']
                            }
                            has_target = True
                            reverse_mode = False
                        else:
                            self.stopped = True
                    elif self.automation['reverse'] is False and \
                        self.automation['loop'] is True:
                        self.pois_index = 0
                        self.target_to_reach = {
                            'x': self.automation['points'][self.pois_index]['x'],
                            'y': self.automation['points'][self.pois_index]['y']
                        }
                        has_target = True
                    elif self.automation['reverse'] is False and \
                        self.automation['loop'] is False:
                        self.stopped = True
                else:
                    self.pois_index += 1
                    self.logger.warning("New POI %s", self.pois_index)
                    self.target_to_reach = {
                        'x': self.automation['points'][self.pois_index]['x'],
                        'y': self.automation['points'][self.pois_index]['y']
                    }
                    has_target = True

            # Calculate velocities based on next POI
            lin_, ang_ = self.calculate_velocities_for_target()

            if ang_ == 0:
                self._x += lin_ * dt * math.cos(self._theta)
                self._y += lin_ * dt * math.sin(self._theta)
            else:
                arc = lin_ / ang_
                self._x += - arc * math.sin(self._theta) + \
                    arc * math.sin(self._theta + dt * ang_)
                self._y -= - arc * math.cos(self._theta) + \
                    arc * math.cos(self._theta + dt * ang_)
            self._theta += ang_ * dt

            xx = round(float(self._x), 4)
            yy = round(float(self._y), 4)
            theta2 = round(float(self._theta), 4)

            # Check if we reached the POI
            if math.hypot(\
                xx - self.target_to_reach['x'], \
                    yy - self.target_to_reach['y']) < 0.01:
                self.logger.warning("Reached POI %s", self.pois_index)
                self.logger.warning(" >> Current pois list: %s", self.automation['points'])
                has_target = False

            # Logging
            if self._x != prev_x or self._y != prev_y or self._theta != prev_th:
                logging_counter += 1
                if logging_counter % 10 == 0:
                    self.logger.info("%s: New pose: %f, %f, %f %s", \
                        self.name, xx, yy, theta2, \
                        f"[POI {self.pois_index} {self.automation['points'][self.pois_index]}]"\
                            if self.automation is not None else "")

            # Send internal pose
            if self._x != prev_x or self._y != prev_y:
                self.dispatch_pose_local()

            time.sleep(self.dt)

        self.logger.critical("Stopped %s simulation thread", self.name)
        self.terminated = True

    def dispatch_pose_local(self):
        """
        Publishes the robot's current pose to the internal_pose_pub topic.

        The pose includes the following information:
        - x: The x-coordinate of the robot's position.
        - y: The y-coordinate of the robot's position.
        - theta: The orientation of the robot in radians.
        - resolution: The resolution of the robot's position data.
        - name: The name of the robot.

        Returns:
            None
        """
        msg = {
            "x": self._x,
            "y": self._y,
            "theta": self._theta,
            "resolution": self.resolution,
            "name": self.name, # is this needed?
            "raw_name": self.name,
        }
        self.internal_pose_pub.publish(msg)

    def calculate_velocities_for_target(self):
        """
        Calculate the velocities required to reach the target.

        This method calculates the velocities needed to move towards the target
        specified by the 'target_to_reach' attribute. It uses the 
        'calculate_velocities_for_point' method to determine the velocities based 
        on the target's x and y coordinates.

        Returns:
            tuple: A tuple containing the calculated velocities.
        """
        return self.calculate_velocities_for_point(
            self.target_to_reach['x'],
            self.target_to_reach['y']
        )

    def calculate_velocities_for_point(self, x, y):
        """
        Calculate the linear and angular velocities required to reach a given point.
        This method calculates the linear and angular velocities required to reach the given 
        point (x, y) from the robot's current position. It uses the current position and 
        orientation of the robot to determine the required velocities.
        Args:
            x (float): The x-coordinate of the target point.
            y (float): The y-coordinate of the target point.
            poi_index (int): The index of the point of interest.
        Returns:
            tuple: A tuple containing the linear and angular velocities required to reach the 
            target point.
        """
        # Calculate the angle between the robot's current orientation and the target point
        angle = math.atan2(y - self._y, x - self._x)
        # Calculate the angle difference between the robot's orientation and the target angle
        angle_diff = angle - self._theta
        # Normalize the angle difference to be between -pi and pi
        angle_diff = (angle_diff + math.pi) % (2 * math.pi) - math.pi
        sign = 1 if angle_diff > 0 else -1
        # If angle diff is different than almost 0, only rotate
        if abs(angle_diff) > 0.002: # one degree
            angular_velocity = min(self.velocities_for_target['angular'], abs(angle_diff) * 2.0)
            return 0, angular_velocity * sign
        # Otherwise, move forward
        else:
            distance = math.hypot(x - self._x, y - self._y)
            linear_velocity = min(self.velocities_for_target['linear'], distance * 3.0)
            return linear_velocity, 0

    def stop(self):
        """
        Stops all controllers and the communication library factory, and sets the robot's 
        stopped flag to True.
        This method iterates through all controllers, logs a warning message for each, and 
        calls their stop method.
        It then stops the communication library factory and logs a warning message indicating 
        that the robot thread is being stopped.
        Finally, it sets the robot's stopped attribute to True.
        """
        self.logger.warning("%s Trying to stop thread", self.name)
        self.stopped = True
        while not self.terminated and not self.state_automation_terminated:
            time.sleep(0.1)
        self.logger.warning("%s Human thread stopped", self.name)
        # Commlib factory is stopped from base_thing