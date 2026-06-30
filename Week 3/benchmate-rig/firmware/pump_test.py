# pump_test.py  —  run the peristaltic pump for 2 seconds
# --------------------------------------------------------
# Wiring: MOSFET TRIG/PWM -> Pico GP15, MOSFET GND -> Pico GND,
#         12V supply -> VIN+/VIN-, pump -> OUT+/OUT-.
# Run this in Thonny (green Run button). The pump should turn for 2 seconds.
# Re-run to pump again. If it pushes water the wrong way, swap the two pump
# wires on OUT+/OUT-.

from machine import Pin
import time

pump = Pin(15, Pin.OUT)   # GP15 -> MOSFET TRIG/PWM

print("pump ON")
pump.high()               # open the MOSFET -> 12V reaches the pump
time.sleep(2)             # run for 2 seconds
pump.low()                # close the MOSFET -> pump off
print("pump OFF")
