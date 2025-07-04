# relay.py  – minimal, active-HIGH relay driver
    import RPi.GPIO as GPIO

class ActuatorRelay:
    """
    Controls a 2-channel relay board.
      up_pin  : GPIO that energises the UP/EXTEND relay
      down_pin: GPIO that energises the DOWN/RETRACT relay
    Logic: GPIO HIGH → relay ON,  GPIO LOW → relay OFF
    """

    def __init__(self, up_pin=27, down_pin=17):
        self.up_pin   = up_pin
        self.down_pin = down_pin

        GPIO.setmode(GPIO.BCM)
        GPIO.setup([self.up_pin, self.down_pin],
                   GPIO.OUT,
                   initial=GPIO.LOW)       # both relays OFF

    # ------------ actuator commands ------------
    def up_on(self):
        self.down_off()
        GPIO.output(self.up_pin, GPIO.HIGH)
    def up_off(self):   GPIO.output(self.up_pin,   GPIO.LOW)

    def down_on(self):
        self.up_off()
        GPIO.output(self.down_pin, GPIO.HIGH)
    def down_off(self): GPIO.output(self.down_pin, GPIO.LOW)

    def all_off(self):  GPIO.output([self.up_pin, self.down_pin], GPIO.LOW)

    # ------------ tidy exit ------------
    def close(self):
        self.all_off()
        GPIO.cleanup([self.up_pin, self.down_pin])
