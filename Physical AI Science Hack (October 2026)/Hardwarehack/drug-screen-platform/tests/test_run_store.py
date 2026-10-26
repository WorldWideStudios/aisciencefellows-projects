"""Tests for the per-plate run folders."""

import pytest

from run_store import RunStore, slugify
from verify_plan import example_layout


def test_slugify():
    assert slugify("Ferroptosis screen 1") == "ferroptosis-screen-1"
    assert slugify("a/b") == "a-b"
    assert slugify("") == "untitled"
    assert slugify("../../etc") == "etc"
    assert slugify("Zellkultur µM") == "zellkultur-um"


def test_layout_round_trip(tmp_path):
    store = RunStore(tmp_path)
    layout = example_layout()
    path = store.save_layout(layout)
    assert path == tmp_path / "example-screen" / "layout.json"
    assert store.load_layout("Example screen").name == "Example screen"
    assert store.list_plates() == ["example-screen"]


def test_files_and_run_info(tmp_path):
    store = RunStore(tmp_path)
    store.write_file("Plate 1", "before.jpg", b"\xff\xd8\xff\xd9")
    assert store.path("plate-1", "before.jpg").read_bytes() == b"\xff\xd8\xff\xd9"
    store.save_run_info("Plate 1", {"run_id": "r1"})
    assert store.load_run_info("Plate 1") == {"run_id": "r1"}
    assert store.load_run_info("Missing") == {}


def test_path_refuses_traversal(tmp_path):
    store = RunStore(tmp_path)
    with pytest.raises(ValueError):
        store.path("plate", "../layout.json")
    with pytest.raises(FileNotFoundError):
        store.path("plate", "after.jpg")
