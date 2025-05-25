#!/usr/bin/env python3
"""
SensorArray – lightweight handler for up to N open-collector Hall-effect or limit switches.

Usage
-----
from hall import HallArray

# Example with 5 Hall sensors + 2 limit switches:
# BCM pin numbers for sensors: last two entries are limit switches
pins = [5, 6, 13, 19, 26, 16, 20]
hall = HallArray(pins)  # begins listening immediately

# Poll snapshot whenever you like:
print(hall.snapshot())  # list of levels: 0 = active (magnet present / switch closed), 1 = idle (no magnet / switch open)

# Or react to edges via callback:
def cb(ch, state, idx):
    status = 'ON' if state == 0 else 'OFF'
    print(f"Sensor {idx+1} on GPIO{ch}: {status}")
hall.set_callback(cb)

...

hall.close()  # always call on exit
"""

import RPi.GPIO as GPIO
import threading

class HallArray:
    def __init__(self, pins, bouncetime=5):
        """
        pins : iterable of BCM GPIO numbers
               e.g. [5,6,13,19,26,16,20] for 7 sensors
        bouncetime : debounce time in ms for edge detection
        """
        self.pins  = list(pins)
        self.state = [1] * len(self.pins)        # pulled-up idle state
        self._lock = threading.Lock()
        self._cb   = None

        GPIO.setmode(GPIO.BCM)
        for p in self.pins:
            GPIO.setup(p, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(
                p,
                GPIO.BOTH,
                callback=self._isr,
                bouncetime=bouncetime,
            )

    # ---------------- public API ---------------- #
    def set_callback(self, func):
        """Register a user callback(channel, state, idx) fired on any edge."""
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
        level = GPIO.input(channel)          # 0 = active (magnet present / switch closed)
        with self._lock:
            self.state[idx] = level
        if self._cb:
            self._cb(channel, level, idx)
