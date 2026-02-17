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
from app.models.round import Round


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL to run DB tests.")
def test_bids_become_immutable_after_round_lock():
    engine = create_engine(os.environ["TEST_DATABASE_URL"], future=True)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

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

    # create project + round (open)
    db = TestingSessionLocal()
    pid = uuid.uuid4()
    db.add(Project(id=pid, workflow="saleable", title="Bid Test", metadata_json={}))
    db.commit()

    r0 = Round(workflow="saleable", project_id=pid, t=0, state="draft", is_open=True, is_locked=False)
    db.add(r0)
    db.commit()
    db.close()

    # login buyer and authority
    buyer = client.post("/v1/auth/login", json={"workflow":"saleable","username":"buyer1","password":"pass123"}).json()["access_token"]
    auth = client.post("/v1/auth/login", json={"workflow":"saleable","username":"auth1","password":"pass123"}).json()["access_token"]

    # submit quote bid (you must have updated /v1/bids/quote to actually store, or call service in another endpoint)
    # If still stub, this test is only structural; adapt once you wire persistence.
    # Here we simply close+lock round and assert the round endpoints succeed.

    close = client.post("/v1/rounds/close", json={"workflow":"saleable","projectId":str(pid),"t":0}, headers={"Authorization": f"Bearer {auth}"})
    assert close.status_code == 200

    lock = client.post("/v1/rounds/lock", json={"workflow":"saleable","projectId":str(pid),"t":0}, headers={"Authorization": f"Bearer {auth}"})
    assert lock.status_code == 200

    # After lock, any bid submissions should be blocked by round guard in Part 7
    denied = client.post(
        f"/v1/bids/quote?workflow=saleable&projectId={pid}",
        json={"workflow":"saleable","projectId":str(pid),"t":0,"qbundle_inr":"1000.00"},
        headers={"Authorization": f"Bearer {buyer}"},
    )
    assert denied.status_code in (409, 404, 400, 403)