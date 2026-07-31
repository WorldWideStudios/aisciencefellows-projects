from __future__ import annotations

import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path


class CameraControllerError(RuntimeError):
    pass


class CameraController:
    def __init__(self) -> None:
        self._command = self._resolve_command()
        self._lock = threading.Lock()

    def status(self) -> dict[str, object]:
        command = self._resolve_command()
        cameras = self._list_cameras(command) if command else None
        return {
            "available": command is not None,
            "command": command,
            "cameras": cameras,
        }

    def capture_jpeg(
        self,
        width: int,
        height: int,
        quality: int,
        timeout_ms: int,
        hflip: bool,
        vflip: bool,
        lens_position: float | None = None,
    ) -> Path:
        command = self._resolve_command()
        if command is None:
            raise CameraControllerError("No rpicam-still or libcamera-still command was found")

        output_dir = Path(tempfile.gettempdir()) / "rpi-monitoring-service"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"camera-{time.time_ns()}.jpg"

        args = [
            command,
            "--output",
            str(output_path),
            "--encoding",
            "jpg",
            "--width",
            str(width),
            "--height",
            str(height),
            "--quality",
            str(quality),
            "--timeout",
            str(timeout_ms),
            "--nopreview",
            "--autofocus-mode",
            "manual",
        ]
        if lens_position is not None:
            args.extend(["--lens-position", str(lens_position)])
        if hflip:
            args.append("--hflip")
        if vflip:
            args.append("--vflip")

        with self._lock:
            result = subprocess.run(args, capture_output=True, text=True, timeout=(timeout_ms / 1000) + 15)
        if result.returncode != 0:
            output_path.unlink(missing_ok=True)
            message = (result.stderr or result.stdout or "Camera capture failed").strip()
            raise CameraControllerError(message)

        if not output_path.exists() or output_path.stat().st_size == 0:
            output_path.unlink(missing_ok=True)
            raise CameraControllerError("Camera capture produced no image")

        return output_path

    def _resolve_command(self) -> str | None:
        for command in ("rpicam-still", "libcamera-still"):
            path = shutil.which(command)
            if path:
                return path
        return None

    def _list_cameras(self, command: str) -> str | None:
        result = subprocess.run([command, "--list-cameras"], capture_output=True, text=True, timeout=10)
        output = (result.stdout or result.stderr).strip()
        return output or None
