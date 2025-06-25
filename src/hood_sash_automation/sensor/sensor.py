# src/hood_sash_automation/sensor/sensor.py

import RPi.GPIO as GPIO
import threading
import time
import logging

class SashSensor(threading.Thread):
    def __init__(self, hall_pin, led_pin, poll_interval=0.05):
        super().__init__(daemon=True)
        self.hall_pin = hall_pin
        self.led_pin = led_pin
        self.poll_interval = poll_interval
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.hall_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.led_pin, GPIO.OUT)

        self._lock = threading.Lock()
        self._state = self.get_state_from_gpio()
        self.on_state_change = None

    def run(self):
        while True:
            current_state = self.get_state_from_gpio()
            with self._lock:
                if current_state != self._state:
                    self._state = current_state
                    logging.info(f"Sensor state changed: {self._state}")
                    GPIO.output(self.led_pin, GPIO.HIGH if self._state else GPIO.LOW)
                    if self.on_state_change:
                        self.on_state_change(self._state)
            time.sleep(self.poll_interval)
    
    def get_state_from_gpio(self):
        """Returns True if magnet present (sash up), False if not (sash down)"""
        return GPIO.input(self.hall_pin) == GPIO.LOW

    def get_current_state(self):
        with self._lock:
            return self._state

    def cleanup(self):
        GPIO.cleanup([self.hall_pin, self.led_pin]) 
