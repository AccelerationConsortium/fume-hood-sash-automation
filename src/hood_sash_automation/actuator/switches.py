import threading
import time

import RPi.GPIO as GPIO


class HallArray:
    """Poll active-low Hall sensors and emit callbacks when their level changes."""

    def __init__(self, pins, bouncetime=5, poll_interval=0.02):
        self.pins = list(pins)
        self.state = [1] * len(self.pins)
        self._lock = threading.Lock()
        self._cb = None
        self._stop = threading.Event()
        self.poll_interval = poll_interval
        self.bouncetime = bouncetime / 1000.0
        self._last_event = [0.0] * len(self.pins)

        GPIO.setmode(GPIO.BCM)
        for i, pin in enumerate(self.pins):
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self.state[i] = GPIO.input(pin)

        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def set_callback(self, func):
        """Register a callback(channel, state, idx) fired on state changes."""
        self._cb = func

    def snapshot(self):
        """Return a thread-safe live read of all configured GPIO pins."""
        with self._lock:
            for i, pin in enumerate(self.pins):
                self.state[i] = GPIO.input(pin)
            return self.state.copy()

    def close(self):
        """Stop polling and release the configured GPIO pins."""
        self._stop.set()
        self._thread.join(timeout=1)
        GPIO.cleanup(self.pins)

    def _poll_loop(self):
        while not self._stop.is_set():
            self._poll_once()
            time.sleep(self.poll_interval)

    def _poll_once(self):
        for idx, pin in enumerate(self.pins):
            level = GPIO.input(pin)
            self._handle_level(pin, idx, level)

    def _handle_level(self, pin, idx, level):
        callback = None
        now = time.monotonic()

        with self._lock:
            if level == self.state[idx]:
                return
            if now - self._last_event[idx] < self.bouncetime:
                return

            self.state[idx] = level
            self._last_event[idx] = now
            callback = self._cb

        if callback:
            callback(pin, level, idx)

    def _isr(self, channel):
        """Compatibility hook for tests; production hardware uses polling."""
        idx = self.pins.index(channel)
        self._handle_level(channel, idx, GPIO.input(channel))
