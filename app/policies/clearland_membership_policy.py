from sqlalchemy.orm import Session
from app.models.clearland_project_memberships import ClearlandProjectMembership


def enforce_active_clearland_membership(
    *,
    db: Session,
    workflow: str,
    project_id,
    participant_id: str,
):
    """
    Enforces that a participant is actively enrolled in a clearland project.
    NO-OP for non-clearland workflows.
    Authority is expected to bypass this at call-site.
    """
    if workflow != "clearland":
        return

    row = (
        db.query(ClearlandProjectMembership)
        .filter_by(
            project_id=project_id,
            participant_id=participant_id,
            status="active",
        )
        .first()
    )

    if not row:
        raise PermissionError(
            "Participant is not an active member of this clearland project."
        )
