from __future__ import annotations

import glob
import json
import os
import threading
import time
from typing import Any

import serial


class LedControllerError(RuntimeError):
    pass


class LedController:
    def __init__(self) -> None:
        self._lock = threading.Lock()

    def status(self) -> dict[str, object]:
        port = self._resolve_port()
        return {
            "available": port is not None,
            "port": port,
        }

    def turn_on(self, hue: float, saturation: float, value: float, brightness: float) -> dict[str, Any]:
        return self._send(
            {
                "action": "on",
                "h": hue,
                "s": saturation,
                "v": value,
                "brightness": brightness,
            }
        )

    def turn_off(self) -> dict[str, Any]:
        return self._send({"action": "off"})

    def flash(
        self,
        hue: float,
        saturation: float,
        value: float,
        brightness: float,
        duration_ms: int,
        count: int,
        gap_ms: int,
    ) -> dict[str, Any]:
        return self._send(
            {
                "action": "flash",
                "h": hue,
                "s": saturation,
                "v": value,
                "brightness": brightness,
                "duration_ms": duration_ms,
                "count": count,
                "gap_ms": gap_ms,
            },
            timeout_seconds=max(3, ((duration_ms + gap_ms) * count / 1000) + 2),
        )

    def _resolve_port(self) -> str | None:
        configured = os.getenv("LED_SERIAL_PORT")
        if configured:
            return configured

        patterns = [
            "/dev/serial/by-id/*QT2040*Trinkey*",
            "/dev/serial/by-id/*Adafruit*",
            "/dev/ttyACM*",
            "/dev/ttyUSB*",
        ]
        for pattern in patterns:
            matches = sorted(glob.glob(pattern))
            if matches:
                return matches[0]
        return None

    def _send(self, command: dict[str, Any], timeout_seconds: float = 3) -> dict[str, Any]:
        port = self._resolve_port()
        if port is None:
            raise LedControllerError("Trinkey serial device was not found")

        payload = json.dumps(command, separators=(",", ":")).encode("utf-8") + b"\n"

        with self._lock:
            try:
                with serial.Serial(port, baudrate=115200, timeout=0.2, write_timeout=2) as connection:
                    connection.reset_input_buffer()
                    connection.write(payload)
                    connection.flush()
                    deadline = time.monotonic() + timeout_seconds
                    while time.monotonic() < deadline:
                        line = connection.readline().decode("utf-8", errors="replace").strip()
                        if not line:
                            continue
                        try:
                            response = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if response.get("ok") is True:
                            return response
                        raise LedControllerError(str(response.get("error", "Trinkey rejected command")))
            except serial.SerialException as exc:
                raise LedControllerError(f"Could not communicate with Trinkey: {exc}") from exc

        raise LedControllerError("Timed out waiting for Trinkey response")
