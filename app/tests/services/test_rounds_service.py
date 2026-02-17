import uuid
import pytest
from datetime import datetime, timezone

from app.services.rounds_service import RoundService
from app.models.project import Project
from app.models.enums import RoundState


def create_project(db, workflow="saleable"):
    p = Project(
        id=uuid.uuid4(),
        workflow=workflow,
        title="Test Project",
        status="draft",
    )
    db.add(p)
    db.commit()
    return p


def test_open_first_round(db):
    svc = RoundService()
    project = create_project(db)

    r = svc.open_next_round(
        db,
        workflow="saleable",
        project_id=project.id,
        window_start=None,
        window_end=None,
    )

    assert r.t == 0
    assert r.is_open is True
    assert r.is_locked is False
    assert r.state == RoundState.draft.value


def test_cannot_open_second_round_without_lock(db):
    svc = RoundService()
    project = create_project(db)

    svc.open_next_round(db, workflow="saleable", project_id=project.id,
                        window_start=None, window_end=None)

    with pytest.raises(ValueError):
        svc.open_next_round(db, workflow="saleable", project_id=project.id,
                            window_start=None, window_end=None)


def test_close_then_lock_then_open_next(db):
    svc = RoundService()
    project = create_project(db)

    r0 = svc.open_next_round(db, workflow="saleable", project_id=project.id,
                             window_start=None, window_end=None)

    r0 = svc.close_round(db, workflow="saleable", project_id=project.id, t=0)
    assert r0.state == RoundState.submitted.value

    r0 = svc.lock_round(db, workflow="saleable", project_id=project.id, t=0)
    assert r0.state == RoundState.locked.value

    r1 = svc.open_next_round(db, workflow="saleable", project_id=project.id,
                             window_start=None, window_end=None)

    assert r1.t == 1
    assert r1.is_open is True


def test_cannot_lock_open_round(db):
    svc = RoundService()
    project = create_project(db)

    r = svc.open_next_round(db, workflow="saleable", project_id=project.id,
                            window_start=None, window_end=None)

    with pytest.raises(ValueError):
        svc.lock_round(db, workflow="saleable", project_id=project.id, t=r.t)
