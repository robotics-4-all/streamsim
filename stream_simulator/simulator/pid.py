import time


class PID:
    def __init__(self, sample_rate, kp, ki, kd):
        self._sample_period = float(1 / sample_rate)

        self._current_time = time.time()
        self._prev_time = self._current_time
        
        self._prev_error = 0.0

        self._windup = 19.0

        self._kp = kp
        self._ki = ki
        self._kd = kd 

        self._Pterm = 0.0
        self._Iterm = 0.0
        self._Dterm = 0.0

        self._low_pass = [0, 0, 0]
        self._filter_size = 5

    @property
    def sample_rate(self):
        return 1 / self._sample_period

    @sample_rate.setter
    def sample_rate(self, rate):
        if rate > 0:
            self._sample_period = float(1 / rate)
    
    @property
    def windup(self):
        return self._windup

    @windup.setter
    def windup(self, windup):
        if rate > 0:
            self._windup = windup

    @property
    def kp(self):
        return self._kp
    
    @kp.setter
    def kp(self, kp_gain):
        if kp_gain >= 0:
            self._kp = kp_gain

    @property
    def ki(self):
        return self._ki

    @ki.setter
    def ki(self, ki_gain):
        if ki_gain >= 0:
            self._ki = ki_gain

    @property
    def kd(self):
        return self._kd

    @kd.setter
    def kd(self, kd_gain):
        if kd_gain >= 0:
            self._kd = kd_gain


    def calcPID(self, error):
        self._current_time = time.time()

        delta_time = self._current_time - self._prev_time
        delta_error = error - self._prev_error
        
        pid_val = 0.0

        if delta_time > self._sample_period:
            #to add windup for integral component
            self._Pterm = error
            if self._Iterm > self._windup:
                self._Iterm = 0.9 * self._windup
            elif self._Iterm < -self._windup:
                self._Iterm = -0.9 * self._windup
            else:
                self._Iterm += error * delta_time
            
            self._Dterm = (delta_error / delta_time) if delta_time > 0 else 0.0
            self._low_pass.append(self._Dterm)
            if len(self._low_pass) > self._filter_size:
                self._low_pass.pop()
            


            pid_val = (self._kp * self._Pterm) + (self._ki * self._Iterm) + (self._kd * sum(self._low_pass) / self._filter_size)

            # update state
            self._prev_time = self._current_time
            self._prev_error = error
            
            
        return pid_val
            
