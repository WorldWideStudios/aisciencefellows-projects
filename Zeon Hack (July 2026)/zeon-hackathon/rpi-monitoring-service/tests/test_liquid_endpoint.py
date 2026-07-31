from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("cv2")

from app.liquid_level_controller import LiquidLevelController


IMAGE_DIRECTORY = Path(os.getenv("LIQUID_DEMO_IMAGE_DIR", "/Users/sai/Downloads"))
FULL_IMAGE = IMAGE_DIRECTORY / "camera-4.jpg"
LOW_IMAGE = IMAGE_DIRECTORY / "camera-6.jpg"

pytestmark = pytest.mark.skipif(
    not FULL_IMAGE.exists() or not LOW_IMAGE.exists(),
    reason="Set LIQUID_DEMO_IMAGE_DIR to the directory containing camera-4.jpg and camera-6.jpg",
)

controller = LiquidLevelController()


def test_full_reference_image_is_ok() -> None:
    reading = controller.estimate_bytes(FULL_IMAGE.read_bytes())
    payload = controller.response_for(reading)

    assert payload["status"] == "ok"
    assert payload["estimated_volume_ml"] > 0
    assert payload["liquid_height_mm"] > 0
    assert payload["capacity_ml"] > 0


def test_low_image_requests_one_ml_of_media() -> None:
    full_reading = controller.estimate_bytes(FULL_IMAGE.read_bytes())
    low_reading = controller.estimate_bytes(LOW_IMAGE.read_bytes())
    full_payload = controller.response_for(full_reading)
    low_payload = controller.response_for(low_reading)

    assert low_payload["status"] == "ok"
    assert low_payload["estimated_volume_ml"] < full_payload["estimated_volume_ml"]


def test_invalid_image_is_rejected() -> None:
    with pytest.raises(Exception):
        controller.estimate_bytes(b"not an image")
