#app/schemas/projects.py
from __future__ import annotations

from typing import Literal, Optional, Union, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from app.core.types import WorkflowType


# -----------------------
# Workflow-specific metadata
# -----------------------


class SaleableMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["saleable"] = "saleable"

    owner_type: Literal["cooperative_society", "private_owner"]
    society_name: Optional[str] = None
    owner_name: Optional[str] = None

    consent_state: Literal["draft", "consented", "withdrawn"]
    bidding_window_start_iso: str
    bidding_window_end_iso: str

    property_city: str
    property_zone: str
    property_address: str
    builtup_area_sqft: float = Field(..., gt=0)


class SlumMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["slum"] = "slum"

    portal_slum_dweller_enabled: bool = True
    portal_slum_land_developer_enabled: bool = True
    portal_affordable_housing_dev_enabled: bool = True

    government_land_type: Literal["road", "rail", "other"]
    jurisdiction_body: str
    project_city: str
    project_zone: str


# -----------------------
# SUBSIDIZED (FIXED)
# -----------------------


class SubsidizedEconomicModelSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    LU: Dict[str, float]
    PRU: Dict[str, float]
    TDRU: Dict[str, float]
    DCU: Dict[str, float]

    COSTS: Dict[str, float]
    WEIGHTS: Dict[str, float]

    OBJECTIVE: Optional[str] = None
    SOURCE: Optional[str] = None


class SubsidizedMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["subsidized"] = "subsidized"

    scheme_type: Optional[Literal["MHADA", "pagadi", "heritage", "other"]] = None
    project_city: str
    project_zone: str

    # Independent valuer (existing behavior preserved)
    independent_valuer_valuation_inr: Optional[float] = Field(default=None, ge=0)
    valuation_status: Literal["not_submitted", "submitted", "verified"] = (
        "not_submitted"
    )

    # ✅ NEW — book economic model
    economic_model: SubsidizedEconomicModelSchema


class ClearLandMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["clearland"] = "clearland"

    city: str
    zone: str
    parcel_area_sq_m: float = Field(..., gt=0)

    parcel_size_band: Literal["S", "M", "L", "XL"]

    parcel_status: Literal["available", "reserved", "under_review", "sold"] = (
        "available"
    )


ProjectMetadata = Union[
    SaleableMetadata, SlumMetadata, SubsidizedMetadata, ClearLandMetadata
]


# -----------------------
# Request/Response models
# -----------------------


class ProjectCreateRequest(BaseModel):
    workflow: WorkflowType
    title: str = Field(..., min_length=1, max_length=256)
    metadata: ProjectMetadata


class ProjectPatchRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=256)
    status: Optional[str] = Field(default=None, min_length=1, max_length=64)
    metadata: Optional[ProjectMetadata] = None


class ProjectResponse(BaseModel):
    projectId: str
    workflow: WorkflowType
    title: str
    status: str

    isPublished: bool
    publishedAtIso: Optional[str] = None
    createdAtIso: str
    updatedAtIso: str

    metadata: Dict[str, Any]


class ProjectListResponse(BaseModel):
    workflow: WorkflowType
    projects: List[ProjectResponse]
