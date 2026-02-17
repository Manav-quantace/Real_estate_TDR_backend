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


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL to run DB tests."
)
def test_post_ask_bid_rbac_and_round_open():
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

    # Setup project + round open
    db = TestingSessionLocal()
    pid = uuid.uuid4()
    db.add(Project(id=pid, workflow="clearland", title="Ask Test", metadata_json={}))
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

    # Login developer (must exist in your Part 3 auth seed map)
    dev_token = client.post(
        "/v1/auth/login",
        json={"workflow": "clearland", "username": "dev1", "password": "pass123"},
    ).json()["access_token"]

    # Submit ask bid
    resp = client.post(
        f"/v1/bids/ask?workflow=clearland&projectId={pid}",
        json={
            "workflow": "clearland",
            "projectId": str(pid),
            "t": 0,
            "dcu_units": "100.0000",
            "ask_price_per_unit_inr": "50000.00",
            "total_ask_inr": "5000000.00",
            "compensatory_dcu_units": "10.0000",
            "compensatory_ask_price_per_unit_inr": "60000.00",
            "delta_ask_next_round_inr": "1000.00",
        },
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "bidId" in body and "receipt_id" in body
    assert not any(
        k in body
        for k in ["orderbook", "asks", "bids", "marketDepth", "askBook", "quoteBook"]
    )

    # Buyer cannot submit ask
    buyer_token = client.post(
        "/v1/auth/login",
        json={"workflow": "clearland", "username": "buyer1", "password": "pass123"},
    ).json()["access_token"]
    denied = client.post(
        f"/v1/bids/ask?workflow=clearland&projectId={pid}",
        json={
            "workflow": "clearland",
            "projectId": str(pid),
            "t": 0,
            "dcu_units": "1.0000",
            "ask_price_per_unit_inr": "1.00",
        },
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert denied.status_code == 403

    # Close round then deny
    auth_token = client.post(
        "/v1/auth/login",
        json={"workflow": "clearland", "username": "auth1", "password": "pass123"},
    ).json()["access_token"]
    close = client.post(
        "/v1/rounds/close",
        json={"workflow": "clearland", "projectId": str(pid), "t": 0},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert close.status_code == 200

    denied2 = client.post(
        f"/v1/bids/ask?workflow=clearland&projectId={pid}",
        json={
            "workflow": "clearland",
            "projectId": str(pid),
            "t": 0,
            "dcu_units": "2.0000",
            "ask_price_per_unit_inr": "2.00",
        },
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert denied2.status_code == 409
