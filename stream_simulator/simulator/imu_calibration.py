import time
from math import atan2
import numpy as np
from numpy import genfromtxt

class CircularBuffer:
    def __init__(self, size):
        self._data = [0] * size
        self._size = size

        self._pos_to_add = 0
        self._is_ready = False

    def update(self, new_value):
        self._data[self._pos_to_add] = new_value
        self._pos_to_add = (self._pos_to_add + 1) % self._size

        if self._pos_to_add == (self._size - 1):
            self._is_ready = True

    def getMovAver(self):
        if self._is_ready:
            return sum(self._data) / self._size
        else:
            return 0.0

    def getSize(self):
        return self._size


class IMUCalibration:
    # accelerometer
    _buffer_accel_x = None
    _buffer_accel_y = None
    _buffer_accel_z = None

    # gyroscope
    _calib_time = 1
    _aver_gyro_roll = 0.0
    _aver_gyro_pitch = 0.0
    _aver_gyro_yaw = 0.0
    _samples = 0

    # magnetometer
    # to add

    def __init__(self, calib_time, buf_size):
        self._buffer_accel_x = CircularBuffer(buf_size)
        self._buffer_accel_y = CircularBuffer(buf_size)
        self._buffer_accel_z = CircularBuffer(buf_size)

        self._buffer_magne_roll = CircularBuffer(5)
        self._buffer_magne_pitch = CircularBuffer(5)
        self._buffer_magne_yaw = CircularBuffer(5)

        self._calib_time = calib_time

        self._start_time = 0
        
        self._data =  {
                "accel": {
                    "x": 0,
                    "y": 0,
                    "z": 0
                },
                "gyro": {
                    "roll": 0,
                    "pitch": 0,
                    "yaw": 0
                },
                "magne": {
                    "roll": 0,
                    "pitch": 0,
                    "yaw": 0
                }
            }

        # read magnetometer's calibration arrays
        path = "/home/pi/new_infrastructure/stream-sim-backend/stream_simulator/simulator/"

        self.A_1 = genfromtxt(path + 'cal_magne_a_1.csv', delimiter=',')
        self.b = genfromtxt(path + 'cal_magne_b.csv', delimiter=',')

    def start(self):
        self._start_time = time.time()

    def update(self, data):
        self._copyData(data)

        # moving aver of window "size"
        self._buffer_accel_x.update(self._data["accel"]["x"])
        self._buffer_accel_y.update(self._data["accel"]["y"])
        self._buffer_accel_z.update(self._data["accel"]["z"])

        self._buffer_magne_roll.update(self._data["magne"]["roll"])
        self._buffer_magne_pitch.update(self._data["magne"]["pitch"])
        self._buffer_magne_yaw.update(self._data["magne"]["yaw"])

        # record aver(offset) error for time "t"
        self._samples += 1
        if (time.time() - self._start_time) < self._calib_time:
            self._aver_gyro_roll = (self._aver_gyro_roll * (self._samples - 1) + self._data["gyro"]["roll"]) / self._samples
            self._aver_gyro_pitch = (self._aver_gyro_pitch * (self._samples - 1) + self._data["gyro"]["pitch"]) / self._samples
            self._aver_gyro_yaw = (self._aver_gyro_yaw * (self._samples - 1) + self._data["gyro"]["yaw"]) / self._samples

    def getCalibData(self):
        self._data["accel"]["x"] = self._buffer_accel_x.getMovAver()
        self._data["accel"]["y"] = self._buffer_accel_y.getMovAver()
        self._data["accel"]["z"] = self._buffer_accel_z.getMovAver()
            
        if (time.time() - self._start_time) > self._calib_time:
            self._data["gyro"]["roll"] -= self._aver_gyro_roll
            self._data["gyro"]["pitch"] -= self._aver_gyro_pitch
            self._data["gyro"]["yaw"] -= self._aver_gyro_yaw
        else:
            self._data["gyro"]["roll"] = 0.0
            self._data["gyro"]["pitch"] = 0.0
            self._data["gyro"]["yaw"] = 0.0

        magne_readings = [self._buffer_magne_roll.getMovAver(), self._buffer_magne_pitch.getMovAver(), self._buffer_magne_yaw.getMovAver()]

        s = np.array(magne_readings).reshape(3, 1)
        s = np.dot(self.A_1, s - self.b)

        self._data["magne"]["roll"] = s[0,0]
        self._data["magne"]["pitch"] = s[1,0]
        self._data["magne"]["yaw"] = s[2,0]

        print("Imu angle: ", atan2(s[1,0],s[0,0]))

        return self._data

    def _copyData(self, data):
        self._data["accel"]["x"] = data.accel.x
        self._data["accel"]["y"] = data.accel.y
        self._data["accel"]["z"] = data.accel.z

        self._data["gyro"]["yaw"] = data.gyro.z
        self._data["gyro"]["pitch"] = data.gyro.y
        self._data["gyro"]["roll"] = data.gyro.x

        self._data["magne"]["yaw"] = data.magne.z
        self._data["magne"]["pitch"] = data.magne.y
        self._data["magne"]["roll"] = data.magne.x