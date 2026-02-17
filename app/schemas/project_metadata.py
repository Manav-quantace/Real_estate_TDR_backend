#/app/schemas/project_metadata.py
from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field


class BaseProjectMeta(BaseModel):
    workflow: str = Field(..., description="Discriminator")


class SaleableProjectMeta(BaseProjectMeta):
    workflow: Literal["saleable"]
    society_or_owner_type: str = Field(..., description="cooperative society / private owner")
    consent_state: str = Field(..., description="consent status (UI/authority published)")
    schedule: dict = Field(default_factory=dict, description="bidding schedule fields (structural)")
    property_snapshot: dict = Field(default_factory=dict, description="read-only after publish snapshot")


class SlumProjectMeta(BaseProjectMeta):
    workflow: Literal["slum"]
    land_ownership: str = Field(..., description="government land ownership category (structural)")
    tripartite_enabled: bool = Field(default=True)
    portals: dict = Field(
        default_factory=lambda: {
            "slum_dweller": True,
            "slum_land_developer": True,
            "affordable_housing_developer": True,
        },
        description="portal availability flags",
    )
    slum_cluster_snapshot: dict = Field(default_factory=dict, description="slum cluster metadata (structural)")


class SubsidizedProjectMeta(BaseProjectMeta):
    workflow: Literal["subsidized"]
    subsidy_type: str = Field(..., description="MHADA / pagadi / heritage etc")
    independent_valuer_valuation: dict = Field(default_factory=dict, description="valuer field + status")


class ClearLandProjectMeta(BaseProjectMeta):
    workflow: Literal["clearland"]
    parcel_size_band: Optional[str] = Field(default=None)
    zoning_snapshot: dict = Field(default_factory=dict, description="zone/FSI etc (structural)")
    availability_snapshot: dict = Field(default_factory=dict, description="published unit availability (structural)")


ProjectMeta = Annotated[
    Union[SaleableProjectMeta, SlumProjectMeta, SubsidizedProjectMeta, ClearLandProjectMeta],
    Field(discriminator="workflow"),
]