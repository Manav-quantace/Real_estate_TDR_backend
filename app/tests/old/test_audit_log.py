import os, uuid, pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import create_app
from app.db.base import Base
from app.db.session import get_db

from app.models.project import Project
from app.services.audit_service import audit_event, AuditAction


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL to run DB tests."
)
def test_audit_log_endpoint_filters_and_request_id():
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

    # Create project + seed audit rows directly
    db = TestingSessionLocal()
    pid = uuid.uuid4()
    db.add(Project(id=pid, workflow="clearland", title="Audit Test", metadata_json={}))
    db.commit()

    # Fake request object: easiest is to hit a route and then read request-id from response,
    # but here we directly insert using a minimal request shim.
    class ReqShim:
        def __init__(self):
            self.method = "POST"
            self.url = type("U", (), {"path": "/v1/bids/quote"})()
            self.state = type("S", (), {"request_id": "RID-123"})()

    req = ReqShim()

    audit_event(
        db,
        request=req,
        actor_participant_id="p1",
        actor_role="BUYER",
        workflow="clearland",
        project_id=pid,
        t=0,
        action=AuditAction.BID_SUBMITTED_QUOTE,
        payload_summary={
            "workflow": "clearland",
            "projectId": str(pid),
            "t": 0,
            "bidId": "BID-1",
        },
        ref_id="BID-1",
    )
    audit_event(
        db,
        request=req,
        actor_participant_id="auth",
        actor_role="GOV_AUTHORITY",
        workflow="clearland",
        project_id=pid,
        t=0,
        action=AuditAction.ROUND_LOCKED,
        payload_summary={
            "workflow": "clearland",
            "projectId": str(pid),
            "t": 0,
            "roundId": "R-0",
        },
        ref_id="R-0",
    )
    db.close()

    # Retrieve audit via endpoint
    r = client.get(f"/v1/ledger/audit?workflow=clearland&projectId={pid}&t=0")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["workflow"] == "clearland"
    assert body["projectId"] == str(pid)
    assert body["t"] == 0
    assert len(body["records"]) == 2
    assert all(rec["requestId"] == "RID-123" for rec in body["records"])
