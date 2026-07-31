from datetime import datetime, timezone
import threading
import time
from typing import Literal
from uuid import uuid4

from fastapi import HTTPException


STARTED_AT = time.time()
CULTURES: dict[str, dict[str, object]] = {}
JOBS: dict[str, dict[str, object]] = {}
OPENSHELF_ROUTINE_LOCK = threading.Lock()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_culture(culture_id: str) -> dict[str, object]:
    culture = CULTURES.get(culture_id)
    if culture is None:
        raise HTTPException(status_code=404, detail=f"Culture {culture_id} was not found")
    return culture


def create_job(
    section: Literal["cultures", "overwatch"],
    action: Literal["retrieve", "insert", "refill"],
    target_id: str,
) -> dict[str, object]:
    now = utc_now()
    job_id = str(uuid4())
    job = {
        "job_id": job_id,
        "section": section,
        "action": action,
        "status": "queued",
        "created_at": now,
        "updated_at": now,
        "target_id": target_id,
    }
    JOBS[job_id] = job
    return dict(job)


def create_storage_job(culture_id: str, action: Literal["retrieve", "insert"]) -> dict[str, object]:
    require_culture(culture_id)
    return create_job("cultures", action, culture_id)
