from datetime import datetime, timezone
import os
import platform
import socket
import time
from uuid import uuid4

import psutil
from fastapi import FastAPI, HTTPException

from app.clients import OpenShelfClient, RpiMonitoringClient, ServiceClientError
from app.models import CultureRegistration, CultureRegistrationResponse, JobResponse, StorageRoutineRequest
from app.state import CULTURES, JOBS, STARTED_AT, create_job, require_culture
from app.storage_service import CultureStorageService


openshelf_client = OpenShelfClient()
rpi_client = RpiMonitoringClient()
storage_service = CultureStorageService(openshelf_client)

app = FastAPI(
    title="Neuron Monitoring Service",
    description="Local REST interface for neuron monitoring workflows.",
    version="0.1.0",
)


@app.get("/", tags=["status"])
def root() -> dict[str, str]:
    return {
        "service": "neuron-monitoring-service",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
        "cultures": "/cultures",
        "culture_storage": "/cultures/storage",
        "overwatch": "/overwatch",
        "jobs": "/jobs",
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
        "environment": os.getenv("APP_ENV", "local"),
    }


@app.get("/cultures", tags=["cultures"])
def list_cultures() -> dict[str, object]:
    return {
        "cultures": list(CULTURES.values()),
        "count": len(CULTURES),
    }


@app.post("/cultures/register", tags=["cultures"], response_model=CultureRegistrationResponse)
def register_culture(request: CultureRegistration) -> dict[str, object]:
    culture_id = str(uuid4())
    culture = {
        "id": culture_id,
        "ip_address": request.ip_address,
        "port": request.port,
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "status": "registered",
        "storage_item_id": f"culture-{culture_id}",
        "storage_location": request.storage_location.model_dump() if request.storage_location else None,
        "dimensions": request.dimensions,
        "weight": request.weight,
    }
    CULTURES[culture_id] = culture
    return dict(culture)


@app.get("/cultures/{id}/registered", tags=["cultures"])
def registered_culture(id: str) -> dict[str, object]:
    return {"culture": require_culture(id)}


@app.get("/cultures/storage", tags=["cultures"])
def culture_storage() -> dict[str, object]:
    return {
        "status": "ok",
        "registered_cultures": len(CULTURES),
        "pending_jobs": sum(
            1
            for job in JOBS.values()
            if job["section"] == "cultures" and job["status"] in ("queued", "running")
        ),
    }


@app.post("/cultures/storage/insert/{id}", tags=["cultures"], response_model=JobResponse)
def insert_culture_into_storage(id: str, request: StorageRoutineRequest | None = None) -> dict[str, object]:
    return storage_service.run(id, "insert", request)


@app.post("/cultures/storage/retrieve/{id}", tags=["cultures"], response_model=JobResponse)
def retrieve_culture_from_storage(id: str, request: StorageRoutineRequest | None = None) -> dict[str, object]:
    return storage_service.run(id, "retrieve", request)


@app.get("/cultures/{id}/level", tags=["cultures"])
def culture_level(id: str) -> dict[str, object]:
    culture = require_culture(id)
    try:
        return _level_response(id, culture)
    except ServiceClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/overwatch/levels", tags=["overwatch"])
def overwatch_levels() -> dict[str, object]:
    levels = [_safe_level_response(culture_id, culture) for culture_id, culture in CULTURES.items()]
    return {
        "levels": levels,
        "count": len(levels),
    }


@app.post("/overwatch/refill/{id}", tags=["overwatch"], response_model=JobResponse)
def refill_culture(id: str) -> dict[str, object]:
    require_culture(id)
    return create_job("overwatch", "refill", id)


@app.get("/jobs", tags=["jobs"])
def list_jobs() -> dict[str, object]:
    return {
        "jobs": list(JOBS.values()),
        "count": len(JOBS),
    }


def _level_response(culture_id: str, culture: dict[str, object]) -> dict[str, object]:
    level = rpi_client.get_level(culture)
    return {
        "culture_id": culture_id,
        "status": "ok",
        "level": level.get("level") if isinstance(level, dict) else level,
        "source": {
            "ip_address": culture["ip_address"],
            "port": culture["port"],
        },
    }


def _safe_level_response(culture_id: str, culture: dict[str, object]) -> dict[str, object]:
    try:
        return _level_response(culture_id, culture)
    except ServiceClientError as exc:
        return {
            "culture_id": culture_id,
            "status": "failed",
            "level": None,
            "error": str(exc),
            "source": {
                "ip_address": culture["ip_address"],
                "port": culture["port"],
            },
        }
