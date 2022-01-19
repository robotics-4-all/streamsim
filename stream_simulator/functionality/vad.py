from pidevices.sensors.generic_microphone import PyAudioMic
from commlib.logger import Logger

from collections import deque, Counter
from scipy.fft import fft
import numpy as np

import configparser
import enum
import wave
import time
import os


class BlockState(enum.IntEnum):
    IDLE = 0
    SPEAKING = 1


class Block:
    index = 0

    def __init__(self, data, state):
        self._data = data
        self._state = state
        self._index = Block.index

        Block.index += 1
     
    @property
    def data(self):
        return self._data
        
    def __eq__(self, other):
        if isinstance(other, int):
            if self._state == other:
                return True
            else:
                return False
        else:
            print("Not implemented!")
            
    def __str__(self):
        return f"Block = (Index: {self._index}, Data: {self._data}, State: {self._state})"


class BlockQueue(deque):
    def __init__(self, size, sensitivity=1):
        super().__init__(maxlen=size)

        self._sensitivity = sensitivity

    @property
    def is_quite(self):
        if self.count(BlockState.SPEAKING) == 0:
            return True
        else:
            return False

    @property
    def has_speech(self):
        if self.count(BlockState.SPEAKING) >= self._sensitivity:
            return True
        else:
            return False

    @property
    def size(self):
        return len(self)

    def index(self, state):
        index = 0
        for i in self:
            if i._state == state:
                break
            
            index += 1
        
        return index

    def nodrop_append(self, block):
        prev_block = None

        if len(self) == self.maxlen:
            prev_block = self.popleft()
            
        self.append(block)

        return prev_block


class VAD:
    FILEPATH = "../configurations/vad/vad.conf"
    BLOCK_SIZE = 1024
    DOMINANT_INDEXES = "8, 7, 6, 21, 22, 25, 9, 30, 29, 79, 24, 28, 27, 26, 14"
    MIN_TARGET_INDEX = 6
    MAX_TARGET_INDEX = 38
    NOISE_THRESHOLD = 700
    NO_SPEAK_TIMEOUT = 1.5
    SPEECH_TIMEOUT = 3
    SPEECH_SENSITIVITY = 0.3
    SENSITIVITY = 0.6

    def __init__(self, filter_size=7, sensitivity=2, hysterisis=3):
        self._logger = Logger(VAD.__name__)

        self.load_params()

        self._filter_size = filter_size
        self._sensitivity = sensitivity
        self._hysterisis = hysterisis

        # queue holding previous blocks and their state
        self._previous_block = BlockQueue(size=(filter_size + hysterisis), sensitivity=sensitivity)
        self._current_block = BlockQueue(size=filter_size, sensitivity=sensitivity)

        self.reset()

    def _import_param(self, namespace, param, default):
        result = None

        try:
            result = self._config[namespace][param]
            self._logger.debug("Imported variable {} with value: {}".format(
                param, result
            ))
        except Exception as e:
            result = None
            self._logger.warning("Could not import {} from namespace {}!".format(
                param, namespace
            ))

        if result is None:
            result = default
            self._logger.info("Imported parameter: {} as default!".format(param))

        return result

    def load_params(self):
        if not os.path.isfile(VAD.FILEPATH):
            self._logger.error("No configuration file: <{}> found!".format(VAD.FILEPATH))

        self._config = configparser.ConfigParser()
        self._config.read(VAD.FILEPATH)

        self._min_target_index = int(self._import_param(namespace='Algorithm',
                                                        param='MIN_TARGET_INDEX',
                                                        default=VAD.MIN_TARGET_INDEX))

        self._max_target_index = int(self._import_param(namespace='Algorithm',
                                                        param='MAX_TARGET_INDEX',
                                                        default=VAD.MAX_TARGET_INDEX))

        self._noise_threshold = float(self._import_param(namespace='Algorithm',
                                                         param='NOISE_THRESHOLD',
                                                         default=VAD.NOISE_THRESHOLD))

        self._dominant_indexes = (self._import_param(namespace='Algorithm',
                                                         param='DOMINANT_INDEXES',
                                                         default=VAD.DOMINANT_INDEXES))  

        self._dominant_freq_indexes = list(map(int, self._dominant_indexes.split(",")))

        self._no_speak_timeout = float(self._import_param(namespace='Settings',
                                                         param='NO_SPEAK_TIMEOUT',
                                                         default=VAD.NO_SPEAK_TIMEOUT))
        
        self._speech_timeout = float(self._import_param(namespace='Settings',
                                                         param='SPEECH_TIMEOUT',
                                                         default=VAD.SPEECH_TIMEOUT))

        self._speech_sensitivity = float(self._import_param(namespace='Settings',
                                                         param='SENSITIVITY',
                                                         default=VAD.SENSITIVITY))

        self._speech_sensitivity = round(10 * (1 - self._speech_sensitivity)) 

    def reset(self):
        self._block_to_add = 100

        # list holding recorded block containing sound
        self._recording = bytearray()

        # important frequencies of speech during training
        self._speaking_history = deque(maxlen=10)
        self._speaking_started = False
        self._has_spoken = False
        self._speach_timeout_timer = time.time()
        self._no_speak_timeout_timer = time.time()

        self._counter = 0

    @property
    def speech_timeout(self):
        return self._speech_timeout
    
    @speech_timeout.setter
    def speech_timeout(self, timeout):
        self._speech_timeout = timeout

    def _fft(self, data):
        window = np.frombuffer(data, dtype="int16")
        window = window - np.average(window)
        weights = np.hanning(len(window))
        block_freq = np.absolute(fft(window * weights))[0:512]

        return block_freq

    def _is_speaking(self, block_freq):
        if not self._has_spoken:
            energy_level = np.average(block_freq)
            
            if energy_level > self._noise_threshold:
                block_important_freq = (-block_freq).argsort()[:8]
                dom_freq = np.argmax(block_freq)

                matched_freq = len(np.intersect1d(block_important_freq,
                                                self._dominant_freq_indexes))

                if matched_freq >= 4 and (dom_freq in range(VAD.MIN_TARGET_INDEX, 
                                                            VAD.MAX_TARGET_INDEX)):
                    
                    print("Speaking")
                    self._update_state(True)
                    return True

            print("Idle")
            self._update_state(False)
            
            return False
        
        return False

    def voice_detected(self):
        if self._speaking_started:
            return True
        else:
            return False

    def _update_state(self, state):
        self._speaking_history.append(state)
        started_to_speak = (self._speaking_history.count(BlockState.SPEAKING) >= self._speech_sensitivity)

        if started_to_speak and not self._speaking_started:
            self._speaking_started = True
            self._speach_timeout_timer = time.time()
        elif self._speaking_started:
            if state:
                self._speach_timeout_timer = time.time()
            else:
                if time.time() - self._speach_timeout_timer > self._no_speak_timeout:
                    self._has_spoken = True
                    self._logger.info("Timeout occured! No speech during {} secs.".format(
                        self._speech_timeout
                    ))
        else:
            if (time.time() - self._no_speak_timeout_timer) > self._no_speak_timeout:
                self._has_spoken = True
                self._logger.info("Timeout occured! Speech not started during last {} secs".format(
                    self._no_speak_timeout
                ))

    def has_spoken(self):
        return self._has_spoken

    def start_train(self):
        self._train_noise_threshold = 0
        self._train_noise_samples = 0
    
    def train(self, data, timestamp):
        block_freq = self._fft(data)
        curr_noise_level = np.average(block_freq)

        self._train_noise_threshold += curr_noise_level
        self._train_noise_samples += 1

    def finish_train(self):
        if self._train_noise_samples > 0:
            self._noise_threshold = (3/2) * self._train_noise_threshold / self._train_noise_samples

            try:
                self._config.set('Algorithm', 'NOISE_THRESHOLD', str(self._noise_threshold))
                self._logger.info("Noise level succesfully setted to: {}".format(self._noise_threshold))
            except Exception as e:
                self._logger.error("Error occurent when tried to save: {}".format(e))
    def update(self, data, timestamp):
        # calculate frequencies of data block
        block_freq = self._fft(data)

        state = self._is_speaking(block_freq)
        
        block = Block(data=data, state=state)

        self._current_block.append(block)
        self._previous_block.append(block)

        if self._current_block.has_speech:
            while self._previous_block.size != 0:
                self._recording.extend(self._previous_block.popleft().data)
            
            if state == 1:
                self._block_to_add = 0
            else:
                self._block_to_add += 1
        else:
            if self._block_to_add <= self._sensitivity:
                self._recording.extend(self._previous_block.pop().data)
                self._block_to_add += 1

        if not self._current_block.is_quite:
            while self._current_block.index(BlockState.SPEAKING) >= self._hysterisis:
                self._current_block.popleft()
            
            while self._previous_block.index(BlockState.SPEAKING) >= self._hysterisis:
                self._previous_block.popleft()


if __name__ == "__main__":
    CHANNELS = 1
    FRAMERATE = 16000

    vad = VAD()
    mic = PyAudioMic(channels=CHANNELS,
                     framerate=FRAMERATE,
                     name="mic",
                     max_data_length=1)

    vad.start_train()
    mic.read(secs=3, stream_cb=vad.train)
    vad.finish_train()

    time.sleep(5)

    vad.reset()
    print("Starting")
    recording = mic.async_read(secs=100, file_path="/home/pi/test.wav", stream_cb=vad.update)

    while not vad.has_spoken():
        time.sleep(0.1)

    mic.cancel()
    
    time.sleep(0.2)
    
    f = wave.open("test.wav", 'w')
    f.setnchannels(1)
    f.setframerate(FRAMERATE)
    f.setsampwidth(2)
    f.setnframes(256)
    f.writeframes(vad._recording)
    f.close()

    print("Recording size: ", len(vad._recording))
    mic.stop()
