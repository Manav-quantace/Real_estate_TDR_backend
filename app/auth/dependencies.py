#app/auth/dependencies.py
from fastapi import Depends, Request, HTTPException

from app.core.auth_deps import get_current_principal


def get_current_participant_id(
    request: Request,
    principal=Depends(get_current_principal),
) -> str:
    """
    ⚠️ DEPRECATED — DO NOT USE FOR NEW ENDPOINTS

    This exists ONLY for legacy compatibility.
    All new endpoints MUST depend on get_current_principal.

    If this function is hit, it means legacy code is still active.
    """

    # Optional: fail fast in non-production
    if request.app.state.settings.ENV != "production":
        raise HTTPException(
            status_code=500,
            detail="get_current_participant_id is deprecated. Use get_current_principal.",
        )

    return principal.participant_id
