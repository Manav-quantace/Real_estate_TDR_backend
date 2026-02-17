import os, uuid, pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import create_app
from app.db.base import Base
from app.db.session import get_db

from app.models.project import Project
from app.models.round import Round
from app.models.ask_bid import AskBid
from app.models.quote_bid import QuoteBid


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL to run DB tests.")
def test_vickrey_settlement_second_price_and_redaction():
    engine = create_engine(os.environ["TEST_DATABASE_URL"], future=True)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    app = create_app()
    def override_get_db():
        db = TestingSessionLocal()
        try: yield db
        finally: db.close()
    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)

    # Setup: project + round
    db = TestingSessionLocal()
    pid = uuid.uuid4()
    db.add(Project(id=pid, workflow="clearland", title="Settlement Test", metadata_json={}))
    db.commit()

    rnd = Round(workflow="clearland", project_id=pid, t=0, state="locked", is_open=False, is_locked=True)
    db.add(rnd)
    db.commit()
    db.refresh(rnd)

    # Locked bids: asks
    db.add(AskBid(workflow="clearland", project_id=pid, round_id=rnd.id, t=0, participant_id="devA",
                  state="locked", payload_json={}, total_ask_inr="800.00", signature_hash="ASKHASH1"))
    # Locked quotes: winner 950, second 900
    q1 = QuoteBid(workflow="clearland", project_id=pid, round_id=rnd.id, t=0, participant_id="buyerA",
                  state="locked", payload_json={"qbundle_inr":"950.00"}, signature_hash="QHASH1")
    q2 = QuoteBid(workflow="clearland", project_id=pid, round_id=rnd.id, t=0, participant_id="buyerB",
                  state="locked", payload_json={"qbundle_inr":"900.00"}, signature_hash="QHASH2")
    db.add(q1); db.add(q2)
    db.commit()
    db.close()

    # Non-authority call (buyer token)
    buyer_token = client.post("/v1/auth/login", json={"workflow":"clearland","username":"buyer1","password":"pass123"}).json()["access_token"]
    r = client.get(f"/v1/settlement/result?workflow=clearland&projectId={pid}&t=0", headers={"Authorization": f"Bearer {buyer_token}"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["second_price_inr"] == "900.00"
    # Redaction expected for non-authority (format contains REDACTED if not owner)
    assert body["winner_quote_bid_id"] is None or "REDACTED" in body["winner_quote_bid_id"]

    # Authority sees full
    auth_token = client.post("/v1/auth/login", json={"workflow":"clearland","username":"auth1","password":"pass123"}).json()["access_token"]
    r2 = client.get(f"/v1/settlement/result?workflow=clearland&projectId={pid}&t=0", headers={"Authorization": f"Bearer {auth_token}"})
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["second_price_inr"] == "900.00"
    assert body2["receipt"].get("vickrey_rule")
