from .motor_controller import MotorController
from pidevices.hardware_interfaces.gpio_implementations import PiGPIO
from enum import Enum


class DfrobotMotorControllerPiGPIO(MotorController):
    """Dfrobot motor controller implementation using hwpm pins. Extends
    :class:`MotorController`.

    Args:
        E1 (int): The pwm pin number of the first pwm channel.
        M1 (int): Pin number of first direction pin.
        E2 (int): The pwm pin number of the second pwm channel.
        M2 (int): Pin number of second direction pin.
    """
    SIDE = {
        "Left": 0,
        "Right": 1
    }

    def __init__(self,
                 E1, M1,
                 E2, M2,
                 range,
                 name="", max_data_length=0):
        super(DfrobotMotorControllerPiGPIO, self).__init__(name, max_data_length)

        self._E1 = E1
        self._M1 = M1
        self._E2 = E2
        self._M2 = M2

        self._range = range

        self._gpio = PiGPIO()
        self._is_init = False

    @property
    def E1(self):
        """Pin number of first pwm channel."""
        return self._E1

    @E1.setter
    def E1(self, E1):
        self._E1 = E1

    @property
    def E2(self):
        """Pin number of second pwm channel."""
        return self._E2

    @E2.setter
    def E2(self, E2):
        self._E2 = E2

    @property
    def M1(self):
        """Pin number of first direction pin."""
        return self._M1

    @M1.setter
    def M1(self, M1):
        self._M1 = M1

    @property
    def M2(self):
        """Pin number of second direction pin."""
        return self._M2

    @M2.setter
    def M2(self, M2):
        self._M2 = M2

    def _map(self, value, leftMin, leftMax, rightMin, rightMax):
        # Figure out how 'wide' each range is
        leftSpan = leftMax - leftMin
        rightSpan = rightMax - rightMin

        # Convert the left range into a 0-1 range (float)
        valueScaled = float(value - leftMin) / float(leftSpan)

        # Convert the 0-1 range into a value in the right range.
        return rightMin + (valueScaled * rightSpan)

    def start(self):
        if not self._is_init:
            self._is_init = True
            self._gpio.add_pins(E1=self._E1)
            self._gpio.add_pins(E2=self._E2)
            self._gpio.add_pins(M1=self._M1)
            self._gpio.add_pins(M2=self._M2)

            self._gpio.set_pin_function('E1', 'output')
            self._gpio.set_pin_function('E2', 'output')
            self._gpio.set_pin_function('M1', 'output')
            self._gpio.set_pin_function('M2', 'output')

            self._gpio.set_pin_pwm('E1', True)
            self._gpio.set_pin_pwm('E2', True)


    def move(self, linear, angular):
        # we assume that each side has a speed final speed which is the superposition of the linear and angular speed
        # positive angular rotation follows is clockwise
        left_side_speed = linear + angular / 2
        right_side_speed = linear - angular / 2

        self._move_side(self.SIDE["Left"], left_side_speed)
        self._move_side(self.SIDE["Right"], right_side_speed)


    def _move_side(self, side ,speed):

        



    def _speed_to_pwm(self, speed):
        pwm = 0
        return pwm

    

    # def move_linear_side(self, linear_speed, side):
    #     if not self._is_init:
    #         return

    #     if side:
    #         if 0 <= linear_speed and linear_speed < self._range:
    #             linear_speed = self._map(linear_speed, 0.0, 1.0, 0.5, 1.0)
    #             self._gpio.write('M1', 1)
    #             self._gpio.write('E1', linear_speed)
    #         elif 0 > linear_speed and linear_speed > -self._range:
    #             linear_speed = self._map(linear_speed, 0.0, -1.0, -0.5, -1.0)
    #             self._gpio.write('M1', 0)
    #             self._gpio.write('E1', -linear_speed)
    #     else:
    #         if 0 <= linear_speed and linear_speed < self._range:
    #             linear_speed = self._map(linear_speed, 0.0, 1.0, 0.5, 1.0)
    #             self._gpio.write('M2', 0)
    #             self._gpio.write('E2', linear_speed)
    #         elif 0 > linear_speed and linear_speed > -self._range:
    #             linear_speed = self._map(linear_speed, 0.0, -1.0, -0.5, -1.0)
    #             self._gpio.write('M2', 1)
    #             self._gpio.write('E2', -linear_speed)


    def stop(self):
        self._gpio.write('E1', 0.0)
        self._gpio.write('E2', 0.0)
        self._gpio.write('M1', 0)
        self._gpio.write('M2', 0)


    def terminate(self):
        if self._is_init:
            self._is_init = false

            self.stop()
            
            self._gpio.set_pin_pwm('E1', False)
            self._gpio.set_pin_pwm('E2', False)

            self._gpio.close()


