from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from pathlib import Path

import cv2
import numpy as np


DEFAULT_FULL_DEPTH_RATIO = 0.291015625
DEFAULT_CONFIG: dict[str, object] = {
    "camera_width": 1280,
    "camera_height": 720,
    "camera_quality": 90,
    "camera_timeout_ms": 1000,
    "camera_lens_position": 20.0,
    "hflip": False,
    "vflip": False,
    "stream_interval_ms": 300,
    "vial_outer_diameter_mm": 30.0,
    "vial_wall_thickness_mm": 1.0,
    "vial_cylinder_height_mm": 42.0,
    "cylinder_bottom_y_ratio": 1.03,
    "surface_bottom_exclusion_mm": 2.0,
    "overlay_alpha": 0.35,
    "side_vertical_start_ratio": 0.10,
    "side_vertical_end_ratio": 0.85,
    "left_search_start_ratio": 0.25,
    "left_search_end_ratio": 0.48,
    "right_search_start_ratio": 0.58,
    "right_search_end_ratio": 0.85,
    "center_band_inset_ratio": 0.25,
    "surface_search_start_ratio": 0.45,
    "surface_search_end_ratio": 0.80,
    "surface_candidate_threshold": 0.55,
    "row_smoothing_window": 9,
}


class LiquidLevelControllerError(RuntimeError):
    pass


@dataclass(frozen=True)
class LiquidLevelReading:
    volume_ml: float
    liquid_height_mm: float
    capacity_ml: float
    percent_of_capacity: float
    confidence: float
    liquid_surface_y: int
    cylinder_bottom_y: int
    vial_left_x: int
    vial_right_x: int
    mm_per_pixel: float


class LiquidLevelController:
    """Estimate vial liquid volume from a fixed, front-facing camera image.

    The detector uses the vial's vertical side edges only for pixel-to-mm scale.
    It then tracks the strongest horizontal liquid surface in a tunable search
    band and converts the surface height into volume from known cylinder
    dimensions.
    """

    def __init__(self) -> None:
        self.config_path = Path(
            os.getenv("LIQUID_LEVEL_CONFIG_PATH", Path.cwd() / "level_config.json")
        )
        self.config = self._load_config()

    def get_config(self) -> dict[str, object]:
        self.config = self._load_config()
        return dict(self.config)

    def save_config(self, updates: dict[str, object]) -> dict[str, object]:
        config = self._validate_config({**self.get_config(), **updates})
        self.config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        self.config = config
        return dict(config)

    def reset_config(self) -> dict[str, object]:
        config = self._config_from_environment()
        self.config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        self.config = config
        return dict(config)

    def estimate_bytes(self, image_bytes: bytes) -> LiquidLevelReading:
        if not image_bytes:
            raise LiquidLevelControllerError("The uploaded image is empty")

        encoded = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        if image is None:
            raise LiquidLevelControllerError("OpenCV could not decode the uploaded image")
        return self.estimate(image)

    def estimate_path(self, image_path: Path) -> LiquidLevelReading:
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise LiquidLevelControllerError(f"OpenCV could not decode {image_path}")
        return self.estimate(image)

    def estimate(self, image: np.ndarray) -> LiquidLevelReading:
        self.config = self._load_config()
        if image.ndim != 3 or image.shape[2] != 3:
            raise LiquidLevelControllerError("Expected a three-channel BGR image")

        height, width = image.shape[:2]
        if width < 320 or height < 240:
            raise LiquidLevelControllerError("Image must be at least 320x240 pixels")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        left_x, right_x, side_confidence = self._find_vial_sides(blurred)
        vial_width = right_x - left_x
        center_inset = float(self.config["center_band_inset_ratio"])
        center_left = int(left_x + center_inset * vial_width)
        center_right = int(right_x - center_inset * vial_width)

        row_mean = blurred[:, center_left:center_right].astype(np.float32).mean(axis=1)
        smoothing_window = int(self.config["row_smoothing_window"])
        smoothed_rows = np.convolve(
            row_mean,
            np.ones(smoothing_window, dtype=np.float32) / smoothing_window,
            mode="same",
        )
        row_edges = np.abs(np.diff(smoothed_rows))

        outer_diameter_mm = float(self.config["vial_outer_diameter_mm"])
        wall_thickness_mm = float(self.config["vial_wall_thickness_mm"])
        cylinder_height_mm = float(self.config["vial_cylinder_height_mm"])
        cylinder_bottom = int(float(self.config["cylinder_bottom_y_ratio"]) * height)
        mm_per_pixel = outer_diameter_mm / vial_width
        cylinder_height_px = cylinder_height_mm / mm_per_pixel
        cylinder_top = int(round(cylinder_bottom - cylinder_height_px))

        surface_start = max(cylinder_top, int(float(self.config["surface_search_start_ratio"]) * height))
        configured_surface_end = int(float(self.config["surface_search_end_ratio"]) * height)
        bottom_exclusion_px = int(float(self.config["surface_bottom_exclusion_mm"]) / mm_per_pixel)
        surface_end = min(configured_surface_end, cylinder_bottom - bottom_exclusion_px)
        if surface_end <= surface_start:
            raise LiquidLevelControllerError("Could not construct a liquid search region")

        surface_window = row_edges[surface_start:surface_end]
        surface_offset = self._find_liquid_surface_offset(surface_window)
        liquid_surface = surface_start + surface_offset
        surface_peak = float(surface_window[surface_offset])
        surface_baseline = float(np.percentile(surface_window, 90))
        surface_prominence = surface_peak / max(surface_baseline, 0.001)

        if not cylinder_top < liquid_surface < cylinder_bottom:
            raise LiquidLevelControllerError("Detected liquid surface is outside the configured cylinder height")

        liquid_height_mm = float(np.clip((cylinder_bottom - liquid_surface) * mm_per_pixel, 0, cylinder_height_mm))
        inner_diameter_mm = outer_diameter_mm - (2 * wall_thickness_mm)
        if inner_diameter_mm <= 0:
            raise LiquidLevelControllerError("Inner vial diameter must be positive")
        capacity_ml = self._cylinder_volume_ml(inner_diameter_mm, cylinder_height_mm)
        volume_ml = self._cylinder_volume_ml(inner_diameter_mm, liquid_height_mm)
        percent_of_capacity = 100 * volume_ml / capacity_ml if capacity_ml > 0 else 0

        prominence_confidence = float(np.clip((surface_prominence - 1.0) / 2.0, 0, 1))
        confidence = round(0.55 * side_confidence + 0.45 * prominence_confidence, 3)

        return LiquidLevelReading(
            volume_ml=round(volume_ml, 2),
            liquid_height_mm=round(liquid_height_mm, 2),
            capacity_ml=round(capacity_ml, 2),
            percent_of_capacity=round(percent_of_capacity, 1),
            confidence=confidence,
            liquid_surface_y=liquid_surface,
            cylinder_bottom_y=cylinder_bottom,
            vial_left_x=left_x,
            vial_right_x=right_x,
            mm_per_pixel=round(mm_per_pixel, 5),
        )

    def response_for(self, reading: LiquidLevelReading) -> dict[str, object]:
        self.config = self._load_config()
        return {
            "status": "ok",
            "estimated_volume_ml": reading.volume_ml,
            "liquid_height_mm": reading.liquid_height_mm,
            "capacity_ml": reading.capacity_ml,
            "percent_of_capacity": reading.percent_of_capacity,
            "confidence": reading.confidence,
            "geometry": {
                "liquid_surface_y": reading.liquid_surface_y,
                "cylinder_bottom_y": reading.cylinder_bottom_y,
                "vial_left_x": reading.vial_left_x,
                "vial_right_x": reading.vial_right_x,
                "mm_per_pixel": reading.mm_per_pixel,
                "surface_bottom_exclusion_mm": float(self.config["surface_bottom_exclusion_mm"]),
                "surface_candidate_threshold": float(self.config["surface_candidate_threshold"]),
            },
        }

    def overlay(self, image: np.ndarray, reading: LiquidLevelReading) -> np.ndarray:
        overlay = image.copy()
        height, _ = image.shape[:2]
        left = reading.vial_left_x
        right = reading.vial_right_x
        bottom = reading.cylinder_bottom_y
        visible_bottom = min(bottom, height - 1)
        cylinder_height_px = float(self.config["vial_cylinder_height_mm"]) / reading.mm_per_pixel
        top = int(round(bottom - cylinder_height_px))
        surface = reading.liquid_surface_y

        cv2.line(overlay, (left, top), (right, top), (255, 255, 255), 2)
        cv2.line(overlay, (left, visible_bottom), (right, visible_bottom), (255, 255, 255), 2)
        cv2.line(overlay, (left, surface), (right, surface), (0, 255, 255), 3)
        cv2.rectangle(overlay, (left, surface), (right, visible_bottom), (255, 180, 0), -1)
        alpha = float(self.config["overlay_alpha"])
        blended = cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0)

        cv2.line(blended, (left, top), (right, top), (255, 255, 255), 2)
        cv2.line(blended, (left, visible_bottom), (right, visible_bottom), (255, 255, 255), 2)
        cv2.line(blended, (left, top), (left, visible_bottom), (255, 255, 255), 1)
        cv2.line(blended, (right, top), (right, visible_bottom), (255, 255, 255), 1)
        cv2.line(blended, (left, surface), (right, surface), (0, 255, 255), 3)
        label = f"{reading.volume_ml:.2f} mL"
        cv2.putText(
            blended,
            label,
            (max(10, left), max(30, surface - 12)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )
        return blended

    def encode_jpeg(self, image: np.ndarray, quality: int = 90) -> bytes:
        ok, encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if not ok:
            raise LiquidLevelControllerError("OpenCV could not encode the overlay image")
        return encoded.tobytes()

    def error_overlay(self, image: np.ndarray, message: str) -> np.ndarray:
        overlay = image.copy()
        text = f"Level analysis failed: {message}"
        height, width = overlay.shape[:2]
        cv2.rectangle(overlay, (0, 0), (width, min(height, 80)), (0, 0, 0), -1)
        cv2.putText(
            overlay,
            text[:90],
            (16, 48),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )
        return overlay

    def _find_vial_sides(self, blurred: np.ndarray) -> tuple[int, int, float]:
        height, width = blurred.shape
        gradient_x = np.abs(cv2.Sobel(blurred, cv2.CV_32F, 1, 0, ksize=3))
        vertical_band = gradient_x[
            int(float(self.config["side_vertical_start_ratio"]) * height) :
            int(float(self.config["side_vertical_end_ratio"]) * height)
        ]
        column_strength = np.percentile(vertical_band, 75, axis=0)

        left_start = int(float(self.config["left_search_start_ratio"]) * width)
        left_end = int(float(self.config["left_search_end_ratio"]) * width)
        right_start = int(float(self.config["right_search_start_ratio"]) * width)
        right_end = int(float(self.config["right_search_end_ratio"]) * width)
        left_x = left_start + int(np.argmax(column_strength[left_start:left_end]))
        right_x = right_start + int(np.argmax(column_strength[right_start:right_end]))

        vial_width = right_x - left_x
        if vial_width < 0.25 * width:
            raise LiquidLevelControllerError("Could not find both sides of the vial")

        search_baseline = float(np.median(column_strength[left_start:right_end]))
        side_peak = min(float(column_strength[left_x]), float(column_strength[right_x]))
        side_confidence = float(np.clip((side_peak / max(search_baseline, 1.0) - 1.0) / 5.0, 0, 1))
        return left_x, right_x, side_confidence

    def _find_liquid_surface_offset(self, surface_window: np.ndarray) -> int:
        if surface_window.size == 0:
            raise LiquidLevelControllerError("Liquid search region is empty")

        max_edge = float(np.max(surface_window))
        if max_edge <= 0:
            return int(np.argmax(surface_window))

        threshold = float(self.config["surface_candidate_threshold"]) * max_edge
        candidate_indexes = np.flatnonzero(surface_window >= threshold)
        if candidate_indexes.size == 0:
            return int(np.argmax(surface_window))

        # Prefer the lower sustained edge. On translucent cylinders, the upper
        # reflection can be sharper than the real meniscus/back liquid boundary.
        groups = np.split(candidate_indexes, np.where(np.diff(candidate_indexes) > 2)[0] + 1)
        best_group = max(groups, key=lambda indexes: (int(indexes[-1]), len(indexes)))
        return int(best_group[np.argmax(surface_window[best_group])])

    @staticmethod
    def _cylinder_volume_ml(inner_diameter_mm: float, height_mm: float) -> float:
        radius_mm = inner_diameter_mm / 2
        volume_mm3 = math.pi * radius_mm * radius_mm * height_mm
        return volume_mm3 / 1000

    @staticmethod
    def _read_float(name: str, default: float, minimum: float, maximum: float) -> float:
        raw_value = os.getenv(name)
        if raw_value is None:
            return default
        try:
            value = float(raw_value)
        except ValueError as exc:
            raise LiquidLevelControllerError(f"{name} must be a number") from exc
        if not minimum <= value <= maximum:
            raise LiquidLevelControllerError(f"{name} must be between {minimum} and {maximum}")
        return value

    def _load_config(self) -> dict[str, object]:
        config = self._config_from_environment()
        if self.config_path.exists():
            try:
                saved = json.loads(self.config_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise LiquidLevelControllerError(f"Invalid JSON in {self.config_path}") from exc
            if not isinstance(saved, dict):
                raise LiquidLevelControllerError(f"{self.config_path} must contain a JSON object")
            config.update(saved)
        return self._validate_config(config)

    def _config_from_environment(self) -> dict[str, object]:
        config = dict(DEFAULT_CONFIG)
        config["vial_outer_diameter_mm"] = self._read_float(
            "LIQUID_VIAL_OUTER_DIAMETER_MM",
            30.0,
            minimum=1.0,
            maximum=200.0,
        )
        config["vial_wall_thickness_mm"] = self._read_float(
            "LIQUID_VIAL_WALL_THICKNESS_MM",
            1.0,
            minimum=0.0,
            maximum=20.0,
        )
        config["vial_cylinder_height_mm"] = self._read_float(
            "LIQUID_VIAL_CYLINDER_HEIGHT_MM",
            42.0,
            minimum=1.0,
            maximum=300.0,
        )
        return config

    def _validate_config(self, config: dict[str, object]) -> dict[str, object]:
        validated = dict(DEFAULT_CONFIG)
        for key in DEFAULT_CONFIG:
            if key in config:
                validated[key] = config[key]

        float_ranges = {
            "vial_outer_diameter_mm": (1.0, 200.0),
            "vial_wall_thickness_mm": (0.0, 20.0),
            "vial_cylinder_height_mm": (1.0, 300.0),
            "cylinder_bottom_y_ratio": (0.01, 1.25),
            "surface_bottom_exclusion_mm": (0.0, 100.0),
            "camera_lens_position": (0.0, 32.0),
            "overlay_alpha": (0.0, 1.0),
            "side_vertical_start_ratio": (0.0, 0.99),
            "side_vertical_end_ratio": (0.01, 1.0),
            "left_search_start_ratio": (0.0, 0.99),
            "left_search_end_ratio": (0.01, 1.0),
            "right_search_start_ratio": (0.0, 0.99),
            "right_search_end_ratio": (0.01, 1.0),
            "center_band_inset_ratio": (0.0, 0.45),
            "surface_search_start_ratio": (0.0, 0.99),
            "surface_search_end_ratio": (0.01, 1.0),
            "surface_candidate_threshold": (0.05, 1.0),
        }
        for key, (minimum, maximum) in float_ranges.items():
            value = float(validated[key])
            if not minimum <= value <= maximum:
                raise LiquidLevelControllerError(f"{key} must be between {minimum} and {maximum}")
            validated[key] = value

        int_ranges = {
            "camera_width": (320, 9152),
            "camera_height": (240, 6944),
            "camera_quality": (1, 100),
            "camera_timeout_ms": (0, 10000),
            "stream_interval_ms": (250, 10000),
            "row_smoothing_window": (3, 99),
        }
        for key, (minimum, maximum) in int_ranges.items():
            value = int(validated[key])
            if not minimum <= value <= maximum:
                raise LiquidLevelControllerError(f"{key} must be between {minimum} and {maximum}")
            if key == "row_smoothing_window" and value % 2 == 0:
                value += 1
            validated[key] = value

        for key in ("hflip", "vflip"):
            value = validated[key]
            if isinstance(value, str):
                validated[key] = value.lower() in ("1", "true", "yes", "on")
            else:
                validated[key] = bool(value)

        if float(validated["side_vertical_start_ratio"]) >= float(validated["side_vertical_end_ratio"]):
            raise LiquidLevelControllerError("side_vertical_start_ratio must be less than side_vertical_end_ratio")
        if float(validated["left_search_start_ratio"]) >= float(validated["left_search_end_ratio"]):
            raise LiquidLevelControllerError("left_search_start_ratio must be less than left_search_end_ratio")
        if float(validated["right_search_start_ratio"]) >= float(validated["right_search_end_ratio"]):
            raise LiquidLevelControllerError("right_search_start_ratio must be less than right_search_end_ratio")
        if float(validated["surface_search_start_ratio"]) >= float(validated["surface_search_end_ratio"]):
            raise LiquidLevelControllerError("surface_search_start_ratio must be less than surface_search_end_ratio")
        if float(validated["surface_search_end_ratio"]) >= float(validated["cylinder_bottom_y_ratio"]):
            raise LiquidLevelControllerError("surface_search_end_ratio must be less than cylinder_bottom_y_ratio")
        if float(validated["vial_outer_diameter_mm"]) <= 2 * float(validated["vial_wall_thickness_mm"]):
            raise LiquidLevelControllerError("vial wall thickness is too large for the outer diameter")

        return validated
