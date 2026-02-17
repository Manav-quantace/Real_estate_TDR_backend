from __future__ import annotations
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from app.core.types import WorkflowType


class SlumHouseholdDetails(BaseModel):
    household_id: Optional[str] = None
    family_members: int = Field(..., ge=1)
    vulnerable_members: Optional[int] = Field(default=0, ge=0)
    income_bracket: Optional[str] = None
    tenure_years: Optional[int] = Field(default=None, ge=0)


class SlumConsentToggles(BaseModel):
    consent_redevelopment: bool
    consent_relocation: bool
    consent_data_use: bool


class PreferenceBidPayload(BaseModel):
    workflow: WorkflowType
    projectId: str
    t: int = Field(..., ge=0)

    rehab_option: str = Field(..., description="Chosen rehabilitation option identifier")
    household: SlumHouseholdDetails
    consents: SlumConsentToggles

    additional_notes: Optional[str] = None


class MyPreferenceResponse(BaseModel):
    workflow: WorkflowType
    projectId: str
    t: int
    state: str
    submitted_at_iso: Optional[str] = None
    locked_at_iso: Optional[str] = None
    payload: Dict[str, Any]