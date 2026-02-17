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


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL to run DB tests.")
def test_params_init_returns_t0_and_current():
    test_db_url = os.environ["TEST_DATABASE_URL"]

    engine = create_engine(test_db_url, future=True)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    # create schema
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # app with db override
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
    p = Project(id=pid, workflow="saleable", title="Test Project", metadata_json={})
    db.add(p)
    db.commit()
    db.close()

    # login (demo auth from Part 3)
    r_login = client.post("/v1/auth/login", json={"workflow": "saleable", "username": "buyer1", "password": "pass123"})
    assert r_login.status_code == 200
    token = r_login.json()["access_token"]

    # call params/init
    r = client.get(
        f"/v1/params/init?workflow=saleable&projectId={pid}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "t0" in body and "current" in body
    assert body["t0"]["t"] == 0
    assert body["current"]["t"] == 0
    assert body["visibility"] in ("PUBLIC", "AUTHORITY/AUDITOR")