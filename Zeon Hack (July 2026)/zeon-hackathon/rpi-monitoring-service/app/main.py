from datetime import datetime, timezone
import base64
import os
import platform
import socket
import time
from typing import Any, Iterator

import cv2
import numpy as np
import psutil
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from app.camera_controller import CameraController, CameraControllerError
from app.led_controller import LedController, LedControllerError
from app.liquid_level_controller import LiquidLevelController, LiquidLevelControllerError


STARTED_AT = time.time()
CAMERA_CONTROLLER = CameraController()
LED_CONTROLLER = LedController()
LIQUID_LEVEL_CONTROLLER = LiquidLevelController()

app = FastAPI(
    title="Raspberry Pi Monitoring Service",
    description="REST interface for Raspberry Pi health checks, camera capture, liquid level, and Trinkey NeoPixel control.",
    version="0.5.0",
)


class LedOnRequest(BaseModel):
    hue: float = Field(..., ge=0, le=360, description="HSV hue in degrees.")
    saturation: float = Field(..., ge=0, le=1, description="HSV saturation from 0.0 to 1.0.")
    value: float = Field(..., ge=0, le=1, description="HSV value from 0.0 to 1.0.")
    brightness: float = Field(..., ge=0, le=1, description="NeoPixel brightness from 0.0 to 1.0.")


class LedFlashRequest(LedOnRequest):
    duration_ms: int = Field(150, ge=10, le=5000, description="How long each flash stays on.")
    count: int = Field(1, ge=1, le=50, description="Number of flashes.")
    gap_ms: int = Field(100, ge=0, le=5000, description="Off time between flashes.")


@app.get("/", tags=["status"])
def root() -> dict[str, str]:
    return {
        "service": "rpi-monitoring-service",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
        "camera": "/camera",
        "level": "/level",
        "level_tune": "/level/tune",
        "level_stream": "/level/stream",
    }


@app.get("/health", tags=["status"])
def health() -> dict[str, object]:
    disk = psutil.disk_usage("/")
    memory = psutil.virtual_memory()

    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "uptime_seconds": round(time.time() - STARTED_AT, 2),
        "system_uptime_seconds": round(time.time() - psutil.boot_time(), 2),
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory": {
            "total_mb": round(memory.total / 1024 / 1024, 2),
            "available_mb": round(memory.available / 1024 / 1024, 2),
            "used_percent": memory.percent,
        },
        "disk": {
            "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
            "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
            "used_percent": disk.percent,
        },
        "environment": os.getenv("APP_ENV", "production"),
    }


@app.get("/camera", tags=["camera"])
def camera_status() -> dict[str, object]:
    return CAMERA_CONTROLLER.status()


@app.get("/camera/image", tags=["camera"])
def camera_image(
    width: int = 1280,
    height: int = 720,
    quality: int = 90,
    timeout_ms: int = 1000,
    lens_position: float | None = None,
    hflip: bool = False,
    vflip: bool = False,
) -> FileResponse:
    if not 64 <= width <= 9152:
        raise HTTPException(status_code=422, detail="width must be between 64 and 9152")
    if not 64 <= height <= 6944:
        raise HTTPException(status_code=422, detail="height must be between 64 and 6944")
    if not 1 <= quality <= 100:
        raise HTTPException(status_code=422, detail="quality must be between 1 and 100")
    if not 0 <= timeout_ms <= 10000:
        raise HTTPException(status_code=422, detail="timeout_ms must be between 0 and 10000")
    if lens_position is None:
        lens_position = float(LIQUID_LEVEL_CONTROLLER.get_config()["camera_lens_position"])
    if not 0 <= lens_position <= 32:
        raise HTTPException(status_code=422, detail="lens_position must be between 0 and 32")

    try:
        image_path = CAMERA_CONTROLLER.capture_jpeg(
            width=width,
            height=height,
            quality=quality,
            timeout_ms=timeout_ms,
            hflip=hflip,
            vflip=vflip,
            lens_position=lens_position,
        )
    except CameraControllerError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return FileResponse(
        image_path,
        media_type="image/jpeg",
        filename="camera.jpg",
        background=BackgroundTask(image_path.unlink, missing_ok=True),
    )


@app.get("/level", tags=["level"])
def level(
    width: int | None = None,
    height: int | None = None,
    quality: int | None = None,
    timeout_ms: int | None = None,
    hflip: bool | None = None,
    vflip: bool | None = None,
    lens_position: float | None = None,
) -> dict[str, object]:
    """Capture a camera image and return liquid-level analysis with an overlay."""

    config = LIQUID_LEVEL_CONTROLLER.get_config()
    width = int(width if width is not None else config["camera_width"])
    height = int(height if height is not None else config["camera_height"])
    quality = int(quality if quality is not None else config["camera_quality"])
    timeout_ms = int(timeout_ms if timeout_ms is not None else config["camera_timeout_ms"])
    hflip = bool(hflip if hflip is not None else config["hflip"])
    vflip = bool(vflip if vflip is not None else config["vflip"])
    lens_position = float(lens_position if lens_position is not None else config["camera_lens_position"])

    if not 64 <= width <= 9152:
        raise HTTPException(status_code=422, detail="width must be between 64 and 9152")
    if not 64 <= height <= 6944:
        raise HTTPException(status_code=422, detail="height must be between 64 and 6944")
    if not 1 <= quality <= 100:
        raise HTTPException(status_code=422, detail="quality must be between 1 and 100")
    if not 0 <= timeout_ms <= 10000:
        raise HTTPException(status_code=422, detail="timeout_ms must be between 0 and 10000")
    if not 0 <= lens_position <= 32:
        raise HTTPException(status_code=422, detail="lens_position must be between 0 and 32")

    try:
        result = _capture_level_result(width, height, quality, timeout_ms, hflip, vflip, lens_position)
    except CameraControllerError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    original_base64 = base64.b64encode(result["original_bytes"]).decode("ascii")
    overlay_base64 = base64.b64encode(result["overlay_bytes"]).decode("ascii")

    return {
        "level": result["level"],
        "original_image": {
            "content_type": "image/jpeg",
            "encoding": "base64",
            "data": original_base64,
            "data_url": f"data:image/jpeg;base64,{original_base64}",
        },
        "overlay_image": {
            "content_type": "image/jpeg",
            "encoding": "base64",
            "data": overlay_base64,
            "data_url": f"data:image/jpeg;base64,{overlay_base64}",
        },
    }


@app.get("/level/config", tags=["level"])
def level_config() -> dict[str, object]:
    return {
        "config": LIQUID_LEVEL_CONTROLLER.get_config(),
        "config_path": str(LIQUID_LEVEL_CONTROLLER.config_path),
    }


@app.put("/level/config", tags=["level"])
def save_level_config(updates: dict[str, Any] = Body(...)) -> dict[str, object]:
    try:
        config = LIQUID_LEVEL_CONTROLLER.save_config(updates)
    except LiquidLevelControllerError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "status": "saved",
        "config": config,
        "config_path": str(LIQUID_LEVEL_CONTROLLER.config_path),
    }


@app.post("/level/config/reset", tags=["level"])
def reset_level_config() -> dict[str, object]:
    try:
        config = LIQUID_LEVEL_CONTROLLER.reset_config()
    except LiquidLevelControllerError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "status": "reset",
        "config": config,
        "config_path": str(LIQUID_LEVEL_CONTROLLER.config_path),
    }


@app.get("/level/stream", tags=["level"])
def level_stream() -> StreamingResponse:
    return StreamingResponse(
        _level_stream_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/level/tune", tags=["level"], response_class=HTMLResponse)
def level_tune() -> str:
    return _LEVEL_TUNE_HTML


@app.get("/led", tags=["led"])
def led_status() -> dict[str, object]:
    return LED_CONTROLLER.status()


@app.post("/led/on", tags=["led"])
def led_on(request: LedOnRequest) -> dict[str, object]:
    try:
        response = LED_CONTROLLER.turn_on(
            hue=request.hue,
            saturation=request.saturation,
            value=request.value,
            brightness=request.brightness,
        )
    except LedControllerError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "status": "ok",
        "led": "on",
        "trinkey": response,
    }


@app.post("/led/off", tags=["led"])
def led_off() -> dict[str, object]:
    try:
        response = LED_CONTROLLER.turn_off()
    except LedControllerError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "status": "ok",
        "led": "off",
        "trinkey": response,
    }


@app.post("/led/flash", tags=["led"])
def led_flash(request: LedFlashRequest) -> dict[str, object]:
    try:
        response = LED_CONTROLLER.flash(
            hue=request.hue,
            saturation=request.saturation,
            value=request.value,
            brightness=request.brightness,
            duration_ms=request.duration_ms,
            count=request.count,
            gap_ms=request.gap_ms,
        )
    except LedControllerError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "status": "ok",
        "led": "flashed",
        "trinkey": response,
    }


def _capture_level_result(
    width: int,
    height: int,
    quality: int,
    timeout_ms: int,
    hflip: bool,
    vflip: bool,
    lens_position: float,
) -> dict[str, Any]:
    image_path = None
    try:
        image_path = CAMERA_CONTROLLER.capture_jpeg(
            width=width,
            height=height,
            quality=quality,
            timeout_ms=timeout_ms,
            hflip=hflip,
            vflip=vflip,
            lens_position=lens_position,
        )
        original_bytes = image_path.read_bytes()
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise LiquidLevelControllerError("OpenCV could not decode the captured image")

        try:
            reading = LIQUID_LEVEL_CONTROLLER.estimate(image)
            level_payload = LIQUID_LEVEL_CONTROLLER.response_for(reading)
            overlay = LIQUID_LEVEL_CONTROLLER.overlay(image, reading)
        except LiquidLevelControllerError as exc:
            level_payload = {
                "status": "analysis_failed",
                "estimated_volume_ml": None,
                "liquid_height_mm": None,
                "capacity_ml": None,
                "percent_of_capacity": None,
                "confidence": 0,
                "error": str(exc),
            }
            overlay = LIQUID_LEVEL_CONTROLLER.error_overlay(image, str(exc))

        overlay_bytes = LIQUID_LEVEL_CONTROLLER.encode_jpeg(overlay, quality=quality)
        return {
            "level": level_payload,
            "original_bytes": original_bytes,
            "overlay_bytes": overlay_bytes,
        }
    finally:
        if image_path is not None:
            image_path.unlink(missing_ok=True)


def _level_stream_frames() -> Iterator[bytes]:
    while True:
        config = LIQUID_LEVEL_CONTROLLER.get_config()
        try:
            result = _capture_level_result(
                width=int(config["camera_width"]),
                height=int(config["camera_height"]),
                quality=int(config["camera_quality"]),
                timeout_ms=int(config["camera_timeout_ms"]),
                hflip=bool(config["hflip"]),
                vflip=bool(config["vflip"]),
                lens_position=float(config["camera_lens_position"]),
            )
            frame = result["overlay_bytes"]
        except Exception as exc:
            frame = _error_frame(str(exc))

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n"
            + f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii")
            + frame
            + b"\r\n"
        )
        time.sleep(int(config["stream_interval_ms"]) / 1000)


def _error_frame(message: str) -> bytes:
    image = np.full((360, 640, 3), 255, dtype=np.uint8)
    cv2.putText(image, "Stream error", (24, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    cv2.putText(image, message[:80], (24, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1)
    return LIQUID_LEVEL_CONTROLLER.encode_jpeg(image, quality=80)


_LEVEL_TUNE_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Level Tuning</title>
  <style>
    body { margin: 0; font-family: Arial, sans-serif; background: #101418; color: #eef3f8; }
    main { display: grid; grid-template-columns: minmax(420px, 1fr) 360px; gap: 20px; padding: 20px; }
    img { width: 100%; max-height: calc(100vh - 40px); object-fit: contain; background: #000; }
    form { display: grid; gap: 12px; align-content: start; }
    label { display: grid; gap: 4px; font-size: 13px; color: #c8d2dc; }
    input { width: 100%; box-sizing: border-box; padding: 8px; border: 1px solid #384550; background: #151c23; color: #fff; border-radius: 6px; }
    input[type="checkbox"] { width: auto; }
    button { padding: 10px 12px; border: 0; border-radius: 6px; background: #44b3ff; color: #051019; font-weight: 700; cursor: pointer; }
    button.secondary { background: #2a3440; color: #e7edf3; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    pre { white-space: pre-wrap; background: #151c23; padding: 10px; border-radius: 6px; max-height: 180px; overflow: auto; }
    @media (max-width: 900px) { main { grid-template-columns: 1fr; } img { max-height: 60vh; } }
  </style>
</head>
<body>
  <main>
    <section>
      <img id="stream" src="/level/stream" alt="level overlay stream">
    </section>
    <form id="config-form">
      <div class="row">
        <label>Width<input name="camera_width" type="number"></label>
        <label>Height<input name="camera_height" type="number"></label>
      </div>
      <div class="row">
        <label>Quality<input name="camera_quality" type="number"></label>
        <label>Timeout ms<input name="camera_timeout_ms" type="number"></label>
      </div>
      <label>Manual lens position<input name="camera_lens_position" type="number" step="0.01"></label>
      <div class="row">
        <label><span>Horizontal flip</span><input name="hflip" type="checkbox"></label>
        <label><span>Vertical flip</span><input name="vflip" type="checkbox"></label>
      </div>
      <div class="row">
        <label>Stream interval ms<input name="stream_interval_ms" type="number"></label>
        <label>Overlay alpha<input name="overlay_alpha" type="number" step="0.01"></label>
      </div>
      <div class="row">
        <label>Vial OD mm<input name="vial_outer_diameter_mm" type="number" step="0.1"></label>
        <label>Wall thickness mm<input name="vial_wall_thickness_mm" type="number" step="0.1"></label>
      </div>
      <div class="row">
        <label>Cylinder height mm<input name="vial_cylinder_height_mm" type="number" step="0.1"></label>
        <label>Cylinder bottom Y<input name="cylinder_bottom_y_ratio" type="number" step="0.01"></label>
      </div>
      <label>Bottom exclusion mm<input name="surface_bottom_exclusion_mm" type="number" step="0.1"></label>
      <div class="row">
        <label>Left search start<input name="left_search_start_ratio" type="number" step="0.01"></label>
        <label>Left search end<input name="left_search_end_ratio" type="number" step="0.01"></label>
      </div>
      <div class="row">
        <label>Right search start<input name="right_search_start_ratio" type="number" step="0.01"></label>
        <label>Right search end<input name="right_search_end_ratio" type="number" step="0.01"></label>
      </div>
      <div class="row">
        <label>Surface search start<input name="surface_search_start_ratio" type="number" step="0.01"></label>
        <label>Surface search end<input name="surface_search_end_ratio" type="number" step="0.01"></label>
      </div>
      <label>Surface candidate threshold<input name="surface_candidate_threshold" type="number" step="0.01"></label>
      <div class="row">
        <label>Side vertical start<input name="side_vertical_start_ratio" type="number" step="0.01"></label>
        <label>Side vertical end<input name="side_vertical_end_ratio" type="number" step="0.01"></label>
      </div>
      <div class="row">
        <label>Center inset<input name="center_band_inset_ratio" type="number" step="0.01"></label>
        <label>Row smoothing<input name="row_smoothing_window" type="number"></label>
      </div>
      <button type="submit">Save</button>
      <button class="secondary" id="reset" type="button">Reset</button>
      <button class="secondary" id="snapshot" type="button">Refresh Stream</button>
      <pre id="status"></pre>
    </form>
  </main>
  <script>
    const form = document.querySelector("#config-form");
    const statusBox = document.querySelector("#status");
    const stream = document.querySelector("#stream");

    async function loadConfig() {
      const response = await fetch("/level/config");
      const payload = await response.json();
      for (const [key, value] of Object.entries(payload.config)) {
        const input = form.elements[key];
        if (!input) continue;
        if (input.type === "checkbox") input.checked = Boolean(value);
        else input.value = value;
      }
      statusBox.textContent = JSON.stringify(payload, null, 2);
    }

    function formPayload() {
      const payload = {};
      for (const input of form.elements) {
        if (!input.name) continue;
        if (input.type === "checkbox") payload[input.name] = input.checked;
        else if (input.type === "number") payload[input.name] = Number(input.value);
        else payload[input.name] = input.value;
      }
      return payload;
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const response = await fetch("/level/config", {
        method: "PUT",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(formPayload()),
      });
      const payload = await response.json();
      statusBox.textContent = JSON.stringify(payload, null, 2);
      stream.src = "/level/stream?ts=" + Date.now();
    });

    document.querySelector("#reset").addEventListener("click", async () => {
      const response = await fetch("/level/config/reset", {method: "POST"});
      statusBox.textContent = JSON.stringify(await response.json(), null, 2);
      await loadConfig();
      stream.src = "/level/stream?ts=" + Date.now();
    });

    document.querySelector("#snapshot").addEventListener("click", () => {
      stream.src = "/level/stream?ts=" + Date.now();
    });

    loadConfig().catch((error) => { statusBox.textContent = String(error); });
  </script>
</body>
</html>
"""
