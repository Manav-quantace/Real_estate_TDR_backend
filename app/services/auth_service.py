# app/services/auth_service.py  (COMPLETE)
from sqlalchemy.orm import Session

from app.core.security import verify_password, hash_password
from app.db.session import SessionLocal
from app.models.participant import Participant
from app.models.enums import ParticipantRole
from app.policies.rbac import Principal


def authenticate(workflow: str, username: str, password: str) -> Principal | None:
    db: Session = SessionLocal()

    p = (
        db.query(Participant)
        .filter(
            Participant.workflow == workflow,
            Participant.username == username,
            Participant.is_active.is_(True),
        )
        .first()
    )

    if not p:
        return None

    if not verify_password(password, p.password_hash):
        return None

    return Principal(
        participant_id=str(p.id),
        workflow=p.workflow,
        role=ParticipantRole(p.role),
        display_name=p.display_name,
    )


def overwrite_password(workflow: str, username: str, new_password: str) -> bool:
    db: Session = SessionLocal()

    p = (
        db.query(Participant)
        .filter(
            Participant.workflow == workflow,
            Participant.username == username,
            Participant.is_active.is_(True),
        )
        .first()
    )

    if not p:
        return False

    p.password_hash = hash_password(new_password)
    db.commit()
    return True
