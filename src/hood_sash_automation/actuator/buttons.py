# src/hood_sash_automation/actuator/buttons.py

import RPi.GPIO as GPIO
import threading
import time

class PhysicalButtons(threading.Thread):
    def __init__(self, actuator, up_pin, down_pin, stop_pin=None, bounce_time=300):
        super().__init__(daemon=True)
        self.actuator = actuator
        self.up_pin = up_pin
        self.down_pin = down_pin
        self.stop_pin = stop_pin
        self.bounce_time = bounce_time
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.up_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.down_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        if self.stop_pin:
            GPIO.setup(self.stop_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def run(self):
        while True:
            if GPIO.input(self.up_pin) == GPIO.LOW:
                self.handle_up_press()
                time.sleep(self.bounce_time / 1000)

            if GPIO.input(self.down_pin) == GPIO.LOW:
                self.handle_down_press()
                time.sleep(self.bounce_time / 1000)

            if self.stop_pin and GPIO.input(self.stop_pin) == GPIO.LOW:
                self.handle_stop_press()
                time.sleep(self.bounce_time / 1000)
            
            time.sleep(0.1)

    def handle_up_press(self):
        print("Up button pressed")
        # Move to the highest position
        self.actuator.move_to_position_async(5)

    def handle_down_press(self):
        print("Down button pressed")
        # Move to the lowest position (home)
        self.actuator.move_to_position_async(1)

    def handle_stop_press(self):
        print("Stop button pressed")
        self.actuator.stop() 
