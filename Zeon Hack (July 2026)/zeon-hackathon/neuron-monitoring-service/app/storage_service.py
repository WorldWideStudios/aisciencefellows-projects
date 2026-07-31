from typing import Any, Literal

from fastapi import HTTPException

from app.clients import OpenShelfClient, ServiceClientError
from app.models import StorageLocation, StorageRoutineRequest
from app.state import OPENSHELF_ROUTINE_LOCK, create_storage_job, require_culture, utc_now


class CultureStorageService:
    def __init__(self, openshelf: OpenShelfClient) -> None:
        self.openshelf = openshelf

    def run(
        self,
        culture_id: str,
        action: Literal["retrieve", "insert"],
        request: StorageRoutineRequest | None = None,
    ) -> dict[str, object]:
        culture = require_culture(culture_id)
        location = self._resolve_location(culture, request)

        if not OPENSHELF_ROUTINE_LOCK.acquire(blocking=False):
            raise HTTPException(status_code=409, detail="OpenShelf is already running a storage routine")

        job = create_storage_job(culture_id, action)
        try:
            job["status"] = "running"
            job["updated_at"] = utc_now()

            if action == "insert":
                result = self._store(culture, location, request)
            else:
                result = self._retrieve(location)

            job["status"] = "completed"
            job["updated_at"] = utc_now()
            job["result"] = result
            return dict(job)
        except ServiceClientError as exc:
            job["status"] = "failed"
            job["updated_at"] = utc_now()
            job["result"] = {"error": str(exc)}
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        finally:
            OPENSHELF_ROUTINE_LOCK.release()

    def _store(
        self,
        culture: dict[str, object],
        location: StorageLocation | dict[str, object],
        request: StorageRoutineRequest | None,
    ) -> dict[str, object]:
        culture["storage_location"] = self._location_payload(location)
        item = self._create_openshelf_item(culture, request)
        command = {
            "command": "store_item",
            "location": self._location_payload(location),
            "item": self._culture_item_payload(culture, request),
        }

        command_result = self.openshelf.post_command(command)
        final_status = self.openshelf.wait_for_command_completion()
        return {
            "openshelf_item": item,
            "openshelf_command": command,
            "openshelf_command_result": command_result,
            "openshelf_final_status": final_status,
        }

    def _retrieve(self, location: StorageLocation | dict[str, object]) -> dict[str, object]:
        command = {
            "command": "retrieve_item",
            "location": self._location_payload(location),
        }
        command_result = self.openshelf.post_command(command)
        final_status = self.openshelf.wait_for_command_completion()
        return {
            "openshelf_command": command,
            "openshelf_command_result": command_result,
            "openshelf_final_status": final_status,
        }

    def _create_openshelf_item(
        self,
        culture: dict[str, object],
        request: StorageRoutineRequest | None,
    ) -> Any:
        item = self._culture_item_payload(culture, request)
        try:
            return self.openshelf.create_item(item)
        except ServiceClientError as exc:
            if not self._looks_like_existing_item_error(exc):
                raise
            return self.openshelf.get_item(str(item["upca"]))

    @staticmethod
    def _resolve_location(
        culture: dict[str, object],
        request: StorageRoutineRequest | None,
    ) -> StorageLocation | dict[str, object]:
        location = request.storage_location if request and request.storage_location else culture.get("storage_location")
        if location is None:
            raise HTTPException(status_code=400, detail="storage_location is required before using OpenShelf storage")
        return location

    @staticmethod
    def _location_payload(location: StorageLocation | dict[str, object]) -> dict[str, object]:
        if isinstance(location, StorageLocation):
            return location.model_dump()
        return dict(location)

    @staticmethod
    def _culture_item_payload(
        culture: dict[str, object],
        request: StorageRoutineRequest | None,
    ) -> dict[str, object]:
        culture_id = str(culture["id"])
        return {
            "upca": culture["storage_item_id"],
            "name": f"Culture {culture_id}",
            "dimensions": request.dimensions if request and request.dimensions else culture["dimensions"],
            "weight": request.weight if request and request.weight is not None else culture.get("weight"),
            "metadata": {
                "culture_id": culture_id,
                "rpi_monitoring_service": f"http://{culture['ip_address']}:{culture['port']}",
            },
        }

    @staticmethod
    def _looks_like_existing_item_error(exc: ServiceClientError) -> bool:
        message = str(exc).lower()
        return " 400 " in message or " 409 " in message or "already" in message
