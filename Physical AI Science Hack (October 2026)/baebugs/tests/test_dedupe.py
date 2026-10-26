import os

from baebugs import dedupe as D


def test_pointer_roundtrip(tmp_path):
    (tmp_path / "keep").mkdir(); (tmp_path / "copy").mkdir()
    (tmp_path / "keep/a.jpg").write_bytes(b"A" * 1000)
    (tmp_path / "copy/a.jpg").write_bytes(b"A" * 1000)
    (tmp_path / "copy/b.jpg").write_bytes(b"B" * 10)
    os.link(tmp_path / "keep/a.jpg", tmp_path / "keep/a_link.jpg")       # hardlink: no saving
    p = D.plan([tmp_path], tmp_path, keep_prefixes=("keep",))
    assert p["pointers"] == 1 and p["bytes_saved"] == 1000 and p["items"][0]["canonical"] == "keep/a.jpg"
    assert D.apply(p)["replaced"] == 1
    ptr = tmp_path / "copy/a.jpg.ptr.json"
    assert ptr.exists() and not (tmp_path / "copy/a.jpg").exists() and D.verify(ptr, tmp_path)["ok"]
    out = D.materialize(ptr, tmp_path)
    assert out.read_bytes() == b"A" * 1000 and not ptr.exists()


def test_link_mode(tmp_path):
    (tmp_path / "keep").mkdir(); (tmp_path / "copy").mkdir()
    (tmp_path / "keep/a.jpg").write_bytes(b"A" * 1000); (tmp_path / "copy/a.jpg").write_bytes(b"A" * 1000)
    p = D.plan([tmp_path], tmp_path, keep_prefixes=("keep",))
    assert D.apply(p, mode="link")["replaced"] == 1
    assert (tmp_path / "copy/a.jpg").stat().st_ino == (tmp_path / "keep/a.jpg").stat().st_ino
    assert D.plan([tmp_path], tmp_path, ("keep",))["bytes_saved"] == 0          # second pass: nothing left
    assert (tmp_path / "dedupe_pointers.jsonl").read_text().count("\n") == 1


def test_linked_copies_all_relinked(tmp_path):
    (tmp_path / "keep").mkdir(); (tmp_path / "copy").mkdir(); (tmp_path / "stage").mkdir()
    (tmp_path / "keep/a.jpg").write_bytes(b"A" * 1000); (tmp_path / "copy/a.jpg").write_bytes(b"A" * 1000)
    os.link(tmp_path / "copy/a.jpg", tmp_path / "stage/a.jpg")        # staging hardlink of the copy
    p = D.plan([tmp_path], tmp_path, keep_prefixes=("keep",))
    assert p["pointers"] == 2 and p["bytes_saved"] == 1000
    D.apply(p, mode="link")
    ino = (tmp_path / "keep/a.jpg").stat().st_ino
    assert {(tmp_path / x).stat().st_ino for x in ("copy/a.jpg", "stage/a.jpg")} == {ino}
    assert D.plan([tmp_path], tmp_path, ("keep",))["pointers"] == 0
