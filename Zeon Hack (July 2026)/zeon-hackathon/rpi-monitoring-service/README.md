# Raspberry Pi Monitoring Service

FastAPI REST service for simple Raspberry Pi health checks.

## Endpoints

- `GET /health` - machine and service health data
- `GET /camera` - Raspberry Pi camera availability and detected cameras
- `GET /camera/image` - capture and return a JPEG image
- `GET /level` - capture an image and return liquid-level estimation plus original and overlay JPEGs as base64
- `GET /level/stream` - MJPEG stream of the camera image with the level overlay
- `GET /level/tune` - browser UI for tuning and saving level parameters
- `GET /level/config` - read saved level/camera configuration
- `PUT /level/config` - save level/camera configuration
- `POST /level/config/reset` - reset saved level/camera configuration
- `GET /led` - Trinkey serial availability
- `POST /led/on` - turn on the Trinkey NeoPixel with HSV and brightness
- `POST /led/off` - turn off the Trinkey NeoPixel
- `POST /led/flash` - flash the Trinkey NeoPixel with HSV, brightness, duration, and count
- `GET /docs` - Swagger UI
- `GET /openapi.json` - OpenAPI schema

## Local Run

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## Raspberry Pi Install

Copy this folder to `/home/hack/rpi-monitoring-service` on the Pi, then run:

```bash
cd /home/hack/rpi-monitoring-service
bash scripts/install_on_pi.sh
```

After installation:

- Health: `http://hackabot.local:8080/health`
- Swagger: `http://hackabot.local:8080/docs`

## LED Control

The Trinkey must run `trinkey/code.py` as `code.py` on its `CIRCUITPY` drive.
The installer uses USB serial at:

```text
/dev/serial/by-id/usb-Adafruit_QT2040_Trinkey_DF609C80671A2926-if00
```

Turn the LED on:

```bash
curl -X POST http://hackabot.local:8080/led/on \
  -H "Content-Type: application/json" \
  -d '{"hue":120,"saturation":1,"value":1,"brightness":0.3}'
```

Turn the LED off:

```bash
curl -X POST http://hackabot.local:8080/led/off
```

Flash the LED:

```bash
curl -X POST http://hackabot.local:8080/led/flash \
  -H "Content-Type: application/json" \
  -d '{"hue":0,"saturation":0,"value":1,"brightness":1,"duration_ms":150,"count":1,"gap_ms":100}'
```

## Camera Control

Check camera availability:

```bash
curl http://hackabot.local:8080/camera
```

Capture a JPEG:

```bash
curl "http://hackabot.local:8080/camera/image?width=1280&height=720&quality=90&timeout_ms=1000" \
  --output camera.jpg
```

Optional query parameters:

- `width` - image width, default `1280`
- `height` - image height, default `720`
- `quality` - JPEG quality from `1` to `100`, default `90`
- `timeout_ms` - camera warmup/capture timeout, default `1000`
- `lens_position` - manual focus reciprocal distance, default from saved config
- `hflip` - horizontal flip, default `false`
- `vflip` - vertical flip, default `false`

## Liquid Level

`GET /level` captures a new Raspberry Pi camera image, tracks the liquid surface,
and estimates liquid volume from the known vial cylinder geometry. It returns
JSON with the original JPEG, an overlay JPEG, and the level estimate:

```bash
curl "http://hackabot.local:8080/level?width=1280&height=720&quality=90&timeout_ms=1000"
```

The response shape is:

```json
{
  "level": {
    "status": "ok",
    "estimated_volume_ml": 1.7,
    "liquid_height_mm": 2.76,
    "capacity_ml": 25.86,
    "percent_of_capacity": 6.6,
    "confidence": 0.497,
    "geometry": {
      "liquid_surface_y": 444,
      "cylinder_bottom_y": 684,
      "vial_left_x": 410,
      "vial_right_x": 830,
      "mm_per_pixel": 0.07143
    }
  },
  "original_image": {
    "content_type": "image/jpeg",
    "encoding": "base64",
    "data": "..."
  },
  "overlay_image": {
    "content_type": "image/jpeg",
    "encoding": "base64",
    "data": "..."
  }
}
```

The detector uses the cylinder side edges to estimate pixel scale from the
known 30 mm outside diameter, tracks the horizontal liquid surface, and computes
liquid height from the configured cylinder bottom. The default geometry is
30 mm OD, 1 mm wall thickness, and 42 mm cylinder height. Keep the vial, camera,
lighting, focus, exposure, and white balance fixed during the live demo.

Calibration can be adjusted with:

- `LIQUID_VIAL_OUTER_DIAMETER_MM` - vial outside diameter; default `30`
- `LIQUID_VIAL_WALL_THICKNESS_MM` - vial wall thickness; default `1`
- `LIQUID_VIAL_CYLINDER_HEIGHT_MM` - vial cylinder height; default `42`

Saved runtime configuration is stored in `level_config.json` in the service
working directory. The `/level` endpoint reads this saved configuration on each
request, so settings saved from the tuning UI are used immediately.

Open the tuning UI:

```text
http://hackabot.local:8080/level/tune
```

Open the overlay stream directly:

```text
http://hackabot.local:8080/level/stream
```

Save tuning settings programmatically:

```bash
curl -X PUT http://hackabot.local:8080/level/config \
  -H "Content-Type: application/json" \
  -d '{"vial_outer_diameter_mm":30,"vial_wall_thickness_mm":1,"vial_cylinder_height_mm":42,"cylinder_bottom_y_ratio":0.95}'
```

Useful tuning fields include camera settings (`camera_width`, `camera_height`,
`camera_quality`, `camera_timeout_ms`, `camera_lens_position`, `hflip`,
`vflip`), geometry settings (`vial_outer_diameter_mm`, `vial_wall_thickness_mm`,
`vial_cylinder_height_mm`, `cylinder_bottom_y_ratio`,
`surface_bottom_exclusion_mm`), and detector search-window ratios
(`left_search_start_ratio`, `right_search_end_ratio`,
`surface_search_start_ratio`, `surface_search_end_ratio`,
`surface_candidate_threshold`).

The service always captures with manual focus by passing
`--autofocus-mode manual` to `rpicam-still`. `camera_lens_position` is the
`--lens-position` value, expressed as reciprocal distance: `0` is infinity,
`1` is roughly 1 m, and `10` is roughly 10 cm.

`surface_bottom_exclusion_mm` prevents the bottom/back edge of the cylinder from
being selected as the liquid surface. Increase it if the overlay line snaps to
the bottom reflection instead of the true meniscus.

`surface_candidate_threshold` controls how strong an edge must be to be
considered a candidate. The detector chooses the lower sustained candidate so
upper glare/reflection bands are less likely to win.

Run the supplied-image endpoint tests with:

```bash
LIQUID_DEMO_IMAGE_DIR=/path/to/images python -m pytest -q
```

## Service Commands

```bash
sudo systemctl status rpi-monitoring-service
sudo systemctl restart rpi-monitoring-service
sudo journalctl -u rpi-monitoring-service -f
```
