#app/api/v1/auth.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends

from app.schemas.auth import LoginRequest, TokenResponse, ResetPasswordRequest
from app.services.auth_service import authenticate, overwrite_password
from app.core.security import create_access_token
from app.core.auth_deps import get_current_principal

router = APIRouter(prefix="/auth")


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    principal = authenticate(req.workflow, req.username, req.password)
    if not principal:
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    token = create_access_token(
        subject=principal.participant_id,
        claims={
            "workflow": principal.workflow,
            "participant_id": principal.participant_id,
            "role": principal.role.value,
            "display_name": principal.display_name,
        },
    )
    return TokenResponse(access_token=token)


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest):
    ok = overwrite_password(req.workflow, req.username, req.new_password)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")

    return {"status": "password overwritten"}


@router.get("/me")
def get_me(principal=Depends(get_current_principal)):
    return {
        "participant_id": principal.participant_id,
        "workflow": principal.workflow,
        "role": principal.role.value,
        "display_name": principal.display_name,
    }
