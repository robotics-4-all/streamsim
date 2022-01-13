from pidevices.sensors.generic_microphone import PyAudioMic
from collections import deque, Counter
from scipy.fft import fft
from enum import IntEnum
import numpy as np
import wave
import time

CHANNELS = 1
FRAMERATE = 16000


class BlockState(IntEnum):
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
    BLOCK_SIZE = 1024
    IMPORTANT_INDEXES = [8, 7, 6, 21, 22, 25, 9, 30, 29, 79, 24, 28, 27, 26, 14]
    MIN_FREQ_INDEX = 6
    MAX_FREQ_INDEX = 38
    NOISE_THRESHOLD = 380

    NO_SPEAK_TIMEOUT = 1.5

    def __init__(self, filter_size=7, sensitivity=2, hysterisis=3):
        # parse arguments
        self._filter_size = filter_size
        self._sensitivity = sensitivity
        self._hysterisis = hysterisis

        # queue holding previous blocks and their state
        self._previous_block = BlockQueue(size=(filter_size + hysterisis), sensitivity=sensitivity)
        self._current_block = BlockQueue(size=filter_size, sensitivity=sensitivity)

        self.reset()

    def reset(self):
        self._block_to_add = 100

        # list holding recorded block containing sound
        self._recording = bytearray()

        # sound energy threshold
        self._energy_threshold = VAD.NOISE_THRESHOLD

        # important frequencies of speech during training
        self._speech_important_freq = np.array(VAD.IMPORTANT_INDEXES)

        self._speaking_history = deque(maxlen=3)
        self._speaking = False
        self._timeout = VAD.NO_SPEAK_TIMEOUT
        self._has_spoken = False
        self._timer = time.time()

        self._counter = 0


    @property
    def timeout(self):
        return self._timeout
    
    @timeout.setter
    def timeout(self, timeout):
        self._timeout = timeout

    def _fft(self, data):
        window = np.frombuffer(data, dtype="int16")
        window = window - np.average(window)
        weights = np.hanning(len(window))
        block_freq = np.absolute(fft(window * weights))[0:512]

        return block_freq

    def _is_speaking(self, block_freq):
        energy_level = np.average(block_freq)
        
        if energy_level > self._energy_threshold:
            block_important_freq = (-block_freq).argsort()[:8]
            dom_freq = np.argmax(block_freq)

            matched_freq = len(np.intersect1d(block_important_freq,
                                              self._speech_important_freq))

            if matched_freq >= 4 and (dom_freq in range(VAD.MIN_FREQ_INDEX, 
                                                        VAD.MAX_FREQ_INDEX)):
                
                print("Speaking")
                self._update_state(True)
                return True

        print("Idle")
        self._update_state(False)
        
        return False        

    def voice_detected(self):
        if self._speaking:
            return True
        else:
            return False

    def _update_state(self, state):
        self._speaking_history.append(state)
        started_to_speak = (self._speaking_history.count(1) >= 2)

        if started_to_speak and not self._speaking:
            self._speaking = True
            self._timer = time.time()
        elif self._speaking:
            if state:
                self._timer = time.time()
            else:
                if time.time() - self._timer > self._timeout:
                    self._has_spoken = True

    def has_spoken(self):
        return self._has_spoken

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
    vad = VAD()
    mic = PyAudioMic(channels=CHANNELS,
                     framerate=FRAMERATE,
                     name="mic",
                     max_data_length=1)
    
    # time.sleep(3)

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


