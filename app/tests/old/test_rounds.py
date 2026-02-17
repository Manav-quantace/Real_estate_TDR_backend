import os
import uuid
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import create_app
from app.db.base import Base
from app.db.session import get_db
from app.models.project import Project


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL to run DB tests."
)
def test_round_iteration_requires_lock():
    engine = create_engine(os.environ["TEST_DATABASE_URL"], future=True)
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    app = create_app()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    # create project
    db = TestingSessionLocal()
    pid = uuid.uuid4()
    db.add(Project(id=pid, workflow="saleable", title="Rounds Test", metadata_json={}))
    db.commit()
    db.close()

    # login as authority
    auth = client.post(
        "/v1/auth/login",
        json={"workflow": "saleable", "username": "auth1", "password": "pass123"},
    )
    assert auth.status_code == 200
    token = auth.json()["access_token"]

    # open t=0
    r0 = client.post(
        "/v1/rounds/open",
        json={"workflow": "saleable", "projectId": str(pid)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r0.status_code == 200
    assert r0.json()["current"]["t"] == 0
    assert r0.json()["current"]["is_open"] is True

    # cannot open t=1 until lock
    r1_fail = client.post(
        "/v1/rounds/open",
        json={"workflow": "saleable", "projectId": str(pid)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1_fail.status_code == 200  # returns same open round (still t=0)

    # close then lock t=0
    close = client.post(
        "/v1/rounds/close",
        json={"workflow": "saleable", "projectId": str(pid), "t": 0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert close.status_code == 200
    assert close.json()["current"]["is_open"] is False

    lock = client.post(
        "/v1/rounds/lock",
        json={"workflow": "saleable", "projectId": str(pid), "t": 0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert lock.status_code == 200
    assert lock.json()["current"]["is_locked"] is True

    # now open t=1
    r1 = client.post(
        "/v1/rounds/open",
        json={"workflow": "saleable", "projectId": str(pid)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 200
    assert r1.json()["current"]["t"] == 1
    assert r1.json()["current"]["is_open"] is True
