import board
import digitalio
import json
import neopixel_write
import supervisor
import sys
import time


pixel_pin = digitalio.DigitalInOut(board.NEOPIXEL)
pixel_pin.direction = digitalio.Direction.OUTPUT
pixel_color = (0, 0, 0)
pixel_brightness = 1


def hsv_to_rgb(hue, saturation, value):
    hue = float(hue) % 360
    saturation = max(0, min(1, float(saturation)))
    value = max(0, min(1, float(value)))

    chroma = value * saturation
    hue_section = hue / 60
    x = chroma * (1 - abs((hue_section % 2) - 1))

    if hue_section < 1:
        rgb = (chroma, x, 0)
    elif hue_section < 2:
        rgb = (x, chroma, 0)
    elif hue_section < 3:
        rgb = (0, chroma, x)
    elif hue_section < 4:
        rgb = (0, x, chroma)
    elif hue_section < 5:
        rgb = (x, 0, chroma)
    else:
        rgb = (chroma, 0, x)

    match = value - chroma
    return tuple(int((channel + match) * 255) for channel in rgb)


def respond(payload):
    print(json.dumps(payload))


def write_pixel(rgb, brightness):
    global pixel_color, pixel_brightness
    pixel_color = tuple(max(0, min(255, int(channel))) for channel in rgb)
    pixel_brightness = max(0, min(1, float(brightness)))
    data = bytes(int(channel * pixel_brightness) for channel in pixel_color)
    neopixel_write.neopixel_write(pixel_pin, data)


def set_from_hsv(command):
    brightness = max(0, min(1, float(command.get("brightness", 1))))
    write_pixel(hsv_to_rgb(command.get("h", 0), command.get("s", 1), command.get("v", 1)), brightness)


write_pixel((0, 0, 0), 1)


while True:
    if supervisor.runtime.serial_bytes_available:
        try:
            command = json.loads(sys.stdin.readline())
            action = command.get("action")

            if action == "on":
                set_from_hsv(command)
                respond({"ok": True, "action": "on", "rgb": pixel_color, "brightness": pixel_brightness})
            elif action == "flash":
                duration = max(0.01, min(5, float(command.get("duration_ms", 150)) / 1000))
                gap = max(0, min(5, float(command.get("gap_ms", 100)) / 1000))
                count = max(1, min(50, int(command.get("count", 1))))

                for index in range(count):
                    set_from_hsv(command)
                    time.sleep(duration)
                    write_pixel((0, 0, 0), 1)
                    if index < count - 1:
                        time.sleep(gap)

                respond({"ok": True, "action": "flash", "count": count})
            elif action == "off":
                write_pixel((0, 0, 0), 1)
                respond({"ok": True, "action": "off"})
            else:
                respond({"ok": False, "error": "unknown action"})
        except Exception as exc:
            respond({"ok": False, "error": str(exc)})

    time.sleep(0.01)
