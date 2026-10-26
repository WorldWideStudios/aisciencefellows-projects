import pytest

torch = pytest.importorskip("torch")
from baebugs.weights_id import tensor_sha256


def test_tensor_hash_ignores_metadata(tmp_path):
    m = torch.nn.Linear(3, 2)
    a, b = tmp_path / "a.pt", tmp_path / "b.pt"
    torch.save({"model": m, "date": "t1"}, a); torch.save({"model": m, "date": "t2"}, b)
    assert a.read_bytes() != b.read_bytes() and tensor_sha256(a) == tensor_sha256(b)
