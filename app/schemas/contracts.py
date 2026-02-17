from __future__ import annotations
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from app.core.types import WorkflowType


class TokenizedContractResponse(BaseModel):
    contractId: str
    workflow: WorkflowType
    projectId: str
    version: int
    priorContractId: Optional[str] = None
    settlementResultId: str
    createdAtIso: str
    contractHash: str

    ownershipDetails: Dict[str, Any]
    transactionData: Dict[str, Any]
    legalObligations: Dict[str, Any]


class ContractListResponse(BaseModel):
    workflow: WorkflowType
    projectId: str
    contracts: List[TokenizedContractResponse]