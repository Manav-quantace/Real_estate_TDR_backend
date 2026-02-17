import os, uuid, pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import create_app
from app.db.base import Base
from app.db.session import get_db

from app.models.project import Project
from app.models.audit_log import AuditLogRecord


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL to run DB tests."
)
def test_audit_export_rbac_participant_only_sees_own_rows():
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

    # seed project + audit rows
    db = TestingSessionLocal()
    pid = uuid.uuid4()
    db.add(
        Project(
            id=pid,
            workflow="clearland",
            title="ExportTest",
            metadata_json={
                "kind": "clearland",
                "city": "Mumbai",
                "zone": "W1",
                "parcel_area_sq_m": 1.0,
                "parcel_size_band": "S",
            },
        )
    )
    db.commit()

    db.add(
        AuditLogRecord(
            request_id="RID-1",
            route="/v1/x",
            method="POST",
            actor_participant_id="p1",
            actor_role="BUYER",
            workflow="clearland",
            project_id=pid,
            t=0,
            action="BID_SUBMITTED_QUOTE",
            status="ok",
            payload_hash="h1",
            payload_summary_json={"bidId": "b1"},
            ref_id="b1",
        )
    )
    db.add(
        AuditLogRecord(
            request_id="RID-2",
            route="/v1/y",
            method="POST",
            actor_participant_id="p2",
            actor_role="BUYER",
            workflow="clearland",
            project_id=pid,
            t=0,
            action="BID_SUBMITTED_QUOTE",
            status="ok",
            payload_hash="h2",
            payload_summary_json={"bidId": "b2"},
            ref_id="b2",
        )
    )
    db.commit()
    db.close()

    # login as participant p1
    tok_p1 = client.post(
        "/v1/auth/login",
        json={"workflow": "clearland", "username": "p1", "password": "pass123"},
    ).json()["access_token"]

    r = client.get(
        f"/v1/export/audit.csv?workflow=clearland&projectId={pid}",
        headers={"Authorization": f"Bearer {tok_p1}"},
    )
    assert r.status_code == 200, r.text
    text = r.text
    assert "p1" in text
    assert "p2" not in text


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL to run DB tests."
)
def test_audit_export_authority_sees_all_rows():
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

    db = TestingSessionLocal()
    pid = uuid.uuid4()
    db.add(
        Project(
            id=pid,
            workflow="clearland",
            title="ExportTest2",
            metadata_json={
                "kind": "clearland",
                "city": "Mumbai",
                "zone": "W1",
                "parcel_area_sq_m": 1.0,
                "parcel_size_band": "S",
            },
        )
    )
    db.commit()

    db.add(
        AuditLogRecord(
            request_id="RID-1",
            route="/v1/x",
            method="POST",
            actor_participant_id="p1",
            actor_role="BUYER",
            workflow="clearland",
            project_id=pid,
            t=0,
            action="BID_SUBMITTED_QUOTE",
            status="ok",
            payload_hash="h1",
            payload_summary_json={"bidId": "b1"},
            ref_id="b1",
        )
    )
    db.add(
        AuditLogRecord(
            request_id="RID-2",
            route="/v1/y",
            method="POST",
            actor_participant_id="p2",
            actor_role="BUYER",
            workflow="clearland",
            project_id=pid,
            t=0,
            action="BID_SUBMITTED_QUOTE",
            status="ok",
            payload_hash="h2",
            payload_summary_json={"bidId": "b2"},
            ref_id="b2",
        )
    )
    db.commit()
    db.close()

    tok_auth = client.post(
        "/v1/auth/login",
        json={"workflow": "clearland", "username": "auth1", "password": "pass123"},
    ).json()["access_token"]

    r = client.get(
        f"/v1/export/audit.csv?workflow=clearland&projectId={pid}",
        headers={"Authorization": f"Bearer {tok_auth}"},
    )
    assert r.status_code == 200, r.text
    text = r.text
    assert "p1" in text and "p2" in text
