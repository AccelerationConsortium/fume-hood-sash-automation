import RPi.GPIO as GPIO
import threading
import time
class HallArray:
    def __init__(self, pins, bouncetime=5, poll_interval=0.02):
        self.pins = list(pins)
        self.state = [1] * len(self.pins)
        self._lock = threading.Lock()
        self._cb = None
        self._stop = threading.Event()
        self.poll_interval = poll_interval
        GPIO.setmode(GPIO.BCM)
        for i, pin in enumerate(self.pins):
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self.state[i] = GPIO.input(pin)
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
    def set_callback(self, func):
        self._cb = func
    def snapshot(self):
        with self._lock:
            for i, pin in enumerate(self.pins):
                self.state[i] = GPIO.input(pin)
            return self.state.copy()
    def close(self):
        self._stop.set()
        self._thread.join(timeout=1)
        GPIO.cleanup(self.pins)
    def _poll_loop(self):
        while not self._stop.is_set():
            for idx, pin in enumerate(self.pins):
                level = GPIO.input(pin)
                callback = None
                with self._lock:
                    if level != self.state[idx]:
                        self.state[idx] = level
                        callback = self._cb
                if callback:
                    callback(pin, level, idx)
            time.sleep(self.poll_interval)
