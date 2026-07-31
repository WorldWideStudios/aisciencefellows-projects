from typing import Literal

from pydantic import BaseModel, Field


class StorageLocation(BaseModel):
    side: Literal["left_module", "right_module"] = "left_module"
    shelf_idx: int = Field(0, ge=0)
    cell_idx: int = Field(0, ge=0)


class CultureRegistration(BaseModel):
    ip_address: str = Field(..., description="Culture IP address or hostname.")
    port: int = Field(..., ge=1, le=65535, description="Culture REST API port.")
    storage_location: StorageLocation | None = Field(None, description="OpenShelf cell for this culture.")
    dimensions: dict[str, float] = Field(
        default_factory=lambda: {"length": 1.0, "width": 1.0, "height": 1.0},
        description="Simple OpenShelf item dimensions.",
    )
    weight: float | None = Field(None, description="Optional item weight.")


class CultureRegistrationResponse(BaseModel):
    id: str
    ip_address: str
    port: int
    registered_at: str
    status: str
    storage_item_id: str
    storage_location: StorageLocation | None = None


class StorageRoutineRequest(BaseModel):
    storage_location: StorageLocation | None = Field(None, description="Overrides the registered OpenShelf cell.")
    dimensions: dict[str, float] | None = Field(None, description="Overrides registered item dimensions.")
    weight: float | None = None


class JobResponse(BaseModel):
    job_id: str
    section: Literal["cultures", "overwatch"]
    action: Literal["retrieve", "insert", "refill"]
    status: Literal["queued", "running", "completed", "failed"]
    created_at: str
    updated_at: str
    target_id: str
    result: dict[str, object] | None = None
