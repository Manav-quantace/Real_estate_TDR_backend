# app/schemas/participant.py

from pydantic import BaseModel, Field
from app.models.enums import ParticipantRole


class ParticipantCreate(BaseModel):
    workflow: str
    username: str
    password: str
    role: ParticipantRole
    display_name: str
