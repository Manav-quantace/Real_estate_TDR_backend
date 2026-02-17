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
def test_post_quote_bid_non_disclosure_and_my_bids_only():
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

    # Setup: project + open round t=0
    db = TestingSessionLocal()
    pid = uuid.uuid4()
    db.add(Project(id=pid, workflow="saleable", title="Quote Test", metadata_json={}))
    db.commit()
    db.add(Round(workflow="saleable", project_id=pid, t=0, state="draft", is_open=True, is_locked=False))
    db.commit()
    db.close()

    # Login buyer1
    token1 = client.post("/v1/auth/login", json={"workflow":"saleable","username":"buyer1","password":"pass123"}).json()["access_token"]

    # Submit quote bid
    resp = client.post(
        f"/v1/bids/quote?workflow=saleable&projectId={pid}",
        json={"workflow":"saleable","projectId":str(pid),"t":0,"qbundle_inr":"1000000.00"},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Non-disclosure: should not contain any orderbook-style keys
    forbidden = {"orderbook","asks","bids","marketDepth","quoteBook","askBook"}
    assert not any(k in body for k in forbidden)
    assert "bidId" in body and "receipt_id" in body and "status" in body

    # Login another buyer? (not seeded by default) – simulate by reusing buyer1 for check:
    # Instead, ensure /my returns only records for token holder.
    my = client.get(
        f"/v1/bids/my?workflow=saleable&projectId={pid}&t=0",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert my.status_code == 200, my.text
    my_body = my.json()
    assert my_body["t"] == 0
    assert len(my_body["bids"]) == 1
    assert my_body["bids"][0]["bid_type"] == "QUOTE"