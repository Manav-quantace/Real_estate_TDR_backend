from __future__ import annotations
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    workflow: str = Field(..., description="workflow scope for the account")
    username: str
    password: str


class ResetPasswordRequest(BaseModel):
    workflow: str = Field(..., description="workflow scope for the account")
    username: str
    new_password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
