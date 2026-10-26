"""Canonical identity of trained weights: sha256 over the sorted state_dict tensors (EMA preferred).

The checkpoint FILE hash changes every save because ultralytics stamps the save time into it; the tensor
hash does not. Observed 2026-10-25 on magicstudio (CPU, torch 2.14.1, ultralytics 8.4.188): two
deterministic 1-epoch trainings of the same recipe gave different file sha256 and the SAME tensor sha256
(8ec5cb2f...). So: the graph can rebuild weights at the tensor level on the same hardware/software stack,
and a rebuild is verified by comparing tensor hashes, not file hashes. Non-deterministic GPU runs are
compared at the behaviour level (variance policy) instead.
"""
from __future__ import annotations

import hashlib


def tensor_sha256(path_or_ckpt):
    import torch
    ck = torch.load(path_or_ckpt, map_location="cpu", weights_only=False) if isinstance(path_or_ckpt, (str, bytes)) or hasattr(path_or_ckpt, "__fspath__") else path_or_ckpt
    model = ck.get("ema") or ck.get("model") if isinstance(ck, dict) else ck
    sd = model.float().state_dict() if hasattr(model, "state_dict") else model
    h = hashlib.sha256()
    for k in sorted(sd):
        h.update(k.encode()); h.update(sd[k].detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def same_realization(a, b):
    """Rebuild gate: two weight files are the same realization iff their tensor hashes match."""
    return tensor_sha256(a) == tensor_sha256(b)
