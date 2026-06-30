# sensor_test.py  —  first-light test for the TCS34725 color sensor
# ------------------------------------------------------------------
# Run this in Thonny with MicroPython on the Pico (just click Run).
# It prints the color every second. Hold something blue, then something
# pink/red, near the sensor and watch "red/blue" change.
#
# Wiring (sensor -> Pico): VIN->3V3, GND->GND, SDA->GP0, SCL->GP1, LED->3V3

import machine, utime

I2C_ADDR = 0x29
i2c = machine.I2C(0, sda=machine.Pin(0), scl=machine.Pin(1), freq=100000)

def w8(reg, val):
    i2c.writeto_mem(I2C_ADDR, 0x80 | reg, bytes([val]))   # 0x80 = command bit

# wake the sensor up
w8(0x00, 0x01); utime.sleep_ms(3)   # power on
w8(0x00, 0x03)                       # enable the light sensor
w8(0x01, 0xD5)                       # integration time ~101 ms
w8(0x0F, 0x01)                       # gain 4x
utime.sleep_ms(120)

# quick check the sensor is actually on the bus
found = i2c.scan()
if I2C_ADDR not in found:
    print("!! Sensor not found on I2C. Check VIN, GND, SDA->GP0, SCL->GP1.")
    print("   Devices seen:", [hex(a) for a in found])
else:
    print("Sensor found. Wave something blue, then pink, near it...\n")
    while True:
        d = i2c.readfrom_mem(I2C_ADDR, 0x80 | 0x20 | 0x14, 8)  # read R,G,B,Clear
        c = d[0] | d[1] << 8
        r = d[2] | d[3] << 8
        g = d[4] | d[5] << 8
        b = d[6] | d[7] << 8
        rb = r / b if b else 0
        print("R=%5d  G=%5d  B=%5d   red/blue=%.2f" % (r, g, b, rb))
        utime.sleep(1)
