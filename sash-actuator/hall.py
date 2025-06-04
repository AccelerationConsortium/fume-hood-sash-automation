# hall.py
"""
HallArray – lightweight handler for up to N open-collector Hall-effect switches.

Usage
-----
from hall import HallArray

pins = [5, 6, 13, 19, 26]          # BCM pin numbers
hall = HallArray(pins)             # begins listening immediately

# poll snapshot whenever you like
print(hall.snapshot())             # list of levels: 0 = magnet, 1 = off

# or react to edges via callback
def cb(ch, state, idx):
    print(f"Sensor {idx} on GPIO{ch}: {'ON' if state==0 else 'OFF'}")
hall.set_callback(cb)

...
hall.close()                       # always call on exit
"""

import RPi.GPIO as GPIO
import threading

class HallArray:
    def __init__(self, pins, bouncetime=5):
        """
        pins : iterable of BCM GPIO numbers
        bouncetime : debounce in ms for edge detection
        """
        self.pins  = list(pins)
        self._lock = threading.Lock()
        self._cb   = None

        GPIO.setmode(GPIO.BCM)

        # Initialize actual state by reading pin levels
        self.state = []
        for p in self.pins:
            GPIO.setup(p, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self.state.append(GPIO.input(p))  # read actual state
            GPIO.add_event_detect(
                p,
                GPIO.BOTH,
                callback=self._isr,
                bouncetime=bouncetime,
            )

    # ---------------- public API ---------------- #
    def set_callback(self, func):
        """Register a user callback(chan, state, idx) fired on any edge."""
        self._cb = func

    def snapshot(self):
        """Return a thread-safe copy of the current sensor states."""
        with self._lock:
            return self.state.copy()

    def close(self):
        """Release GPIOs — call once before program exit."""
        GPIO.cleanup(self.pins)

    # ---------------- internal ISR -------------- #
    def _isr(self, channel):
        idx   = self.pins.index(channel)
        level = GPIO.input(channel)          # 0 = magnet present
        with self._lock:
            self.state[idx] = level
        if self._cb:
            self._cb(channel, level, idx)
