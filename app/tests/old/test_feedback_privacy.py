import os, uuid, pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import create_app
from app.db.base import Base
from app.db.session import get_db
from app.models.project import Project
from app.models.round import Round


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL to run DB tests."
)
def test_feedback_round_no_leakage():
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

    # setup project + round
    db = TestingSessionLocal()
    pid = uuid.uuid4()
    db.add(
        Project(id=pid, workflow="clearland", title="Feedback Test", metadata_json={})
    )
    db.commit()
    db.add(
        Round(
            workflow="clearland",
            project_id=pid,
            t=0,
            state="draft",
            is_open=True,
            is_locked=False,
        )
    )
    db.commit()
    db.close()

    token = client.post(
        "/v1/auth/login",
        json={"workflow": "clearland", "username": "buyer1", "password": "pass123"},
    ).json()["access_token"]

    resp = client.get(
        f"/v1/feedback/round?workflow=clearland&projectId={pid}&t=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Must include aggregates
    assert "aggregates" in body
    assert "quote" in body["aggregates"]
    assert "ask" in body["aggregates"]

    # Must NOT include sensitive keys
    forbidden = [
        "participant_id",
        "participantId",
        "payload",
        "payload_json",
        "bidId",
        "orderbook",
        "asks",
        "bids",
        "marketDepth",
        "askBook",
        "quoteBook",
    ]
    for k in forbidden:
        assert k not in body
