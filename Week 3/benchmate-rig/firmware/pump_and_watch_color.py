# pump_and_watch_color.py  —  pump reductant in, watch alamarBlue go blue -> pink,
#                              and print the start -> end change (your calibration).
# ---------------------------------------------------------------------------
# Click Run in Thonny (don't save as main.py). Watch the Shell.
#
# Wiring (same Pico, no rewiring):
#   Sensor:  VIN->3V3  GND->GND  SDA->GP0  SCL->GP1  LED->3V3
#   Pump:    MOSFET TRIG/PWM->GP15  MOSFET GND->Pico GND
#            12V supply->VIN+/VIN-  pump->OUT+/OUT-
#
# Flow:
#   1. Reads the color once before pumping (baseline = blue).
#   2. Runs the pump for PUMP_SECONDS (dispenses the reductant).
#   3. Reads color every READ_INTERVAL for WATCH_SECONDS.
#   4. Prints a summary: start, end, peak, and the change -> your two
#      calibration numbers (blue and pink).
#
# Tip: swirl the well gently after the pump stops so it mixes & develops.

from machine import Pin, I2C
import time

PUMP_SECONDS  = 2        # how long to run the pump
WATCH_SECONDS = 300      # vitamin C is slow (~minutes). Sodium dithionite: 30 is plenty.
READ_INTERVAL = 5        # seconds between color readings

# ---- sensor setup ----------------------------------------------------------
I2C_ADDR = 0x29
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=100000)


def w8(reg, val):
    i2c.writeto_mem(I2C_ADDR, 0x80 | reg, bytes([val]))   # 0x80 = command bit


def sensor_init():
    w8(0x00, 0x01); time.sleep_ms(3)   # power on
    w8(0x00, 0x03)                       # enable the light sensor
    w8(0x01, 0xD5)                       # integration time ~101 ms
    w8(0x0F, 0x01)                       # gain 4x
    time.sleep_ms(120)


def read_rb():
    d = i2c.readfrom_mem(I2C_ADDR, 0x80 | 0x20 | 0x14, 8)  # R,G,B,Clear
    c = d[0] | d[1] << 8
    r = d[2] | d[3] << 8
    g = d[4] | d[5] << 8
    b = d[6] | d[7] << 8
    rb = r / b if b else 0
    return r, g, b, c, rb


def show(label):
    r, g, b, c, rb = read_rb()
    print("%-8s  R=%5d  G=%5d  B=%5d   red/blue=%.2f" % (label, r, g, b, rb))
    return rb


# ---- pump setup ------------------------------------------------------------
pump = Pin(15, Pin.OUT)
pump.low()   # off until we explicitly turn it on

# ---- run it ----------------------------------------------------------------
found = i2c.scan()
if I2C_ADDR not in found:
    print("!! Sensor not found on I2C. Check VIN, GND, SDA->GP0, SCL->GP1.")
    print("   Devices seen:", [hex(a) for a in found])
else:
    sensor_init()

    start_rb = show("before")          # baseline (blue)

    print("pump ON")
    pump.high()
    time.sleep(PUMP_SECONDS)
    pump.low()
    print("pump OFF  (give the well a gentle swirl to mix)")

    peak_rb = start_rb
    peak_t = 0
    last_rb = start_rb
    elapsed = 0
    while elapsed < WATCH_SECONDS:
        time.sleep(READ_INTERVAL)
        elapsed += READ_INTERVAL
        rb = show("t+%ds" % elapsed)
        last_rb = rb
        if rb > peak_rb:
            peak_rb = rb
            peak_t = elapsed

    # ---- summary -----------------------------------------------------------
    print("\n--------------- summary ---------------")
    print("start (blue)   red/blue = %.2f" % start_rb)
    print("end            red/blue = %.2f" % last_rb)
    print("peak           red/blue = %.2f  (at t+%ds)" % (peak_rb, peak_t))
    print("change                  = %+.2f" % (last_rb - start_rb))
    if peak_rb > start_rb + 0.10:
        print("-> it reduced: blue -> pink. nice work!")
        print("   calibration points:  BLUE = %.2f   PINK = %.2f" % (start_rb, peak_rb))
        print("   (use these later for BENCHMATE_DEAD_INDEX / LIVE_INDEX)")
    else:
        print("-> little change. give it more time or a better mix,")
        print("   add a bit more reductant, or check the sensor's read on the well.")
    print("---------------------------------------")
