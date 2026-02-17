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
def test_penalty_bmax_minus_bsecond():
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

    # Setup project + locked round + locked bids sufficient for settlement
    db = TestingSessionLocal()
    pid = uuid.uuid4()
    db.add(Project(id=pid, workflow="clearland", title="Penalty Test", metadata_json={}))
    db.commit()

    rnd = Round(workflow="clearland", project_id=pid, t=0, state="locked", is_open=False, is_locked=True)
    db.add(rnd)
    db.commit()
    db.refresh(rnd)

    # Ask total 800
    db.add(AskBid(workflow="clearland", project_id=pid, round_id=rnd.id, t=0, participant_id="devA",
                  state="locked", payload_json={}, total_ask_inr="800.00", signature_hash="ASKHASH"))

    # Quotes: bmax=950, second=900
    db.add(QuoteBid(workflow="clearland", project_id=pid, round_id=rnd.id, t=0, participant_id="buyerA",
                    state="locked", payload_json={"qbundle_inr":"950.00"}, signature_hash="QHASH1"))
    db.add(QuoteBid(workflow="clearland", project_id=pid, round_id=rnd.id, t=0, participant_id="buyerB",
                    state="locked", payload_json={"qbundle_inr":"900.00"}, signature_hash="QHASH2"))
    db.commit()
    db.close()

    # Authority declares default (explicit, auditable)
    auth_token = client.post("/v1/auth/login", json={"workflow":"clearland","username":"auth1","password":"pass123"}).json()["access_token"]
    d = client.post(
        f"/v1/events/default?workflow=clearland&projectId={pid}",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"workflow":"clearland","projectId":str(pid),"t":0,"reason":"winner_failed_to_pay"},
    )
    assert d.status_code == 200, d.text

    # Get penalty (computed deterministically)
    p = client.get(f"/v1/events/penalty?workflow=clearland&projectId={pid}&t=0")
    assert p.status_code == 200, p.text
    body = p.json()
    assert body["bmax_inr"] == "950.00"
    assert body["bsecond_inr"] == "900.00"
    assert body["penalty_inr"] == "50.00"  # exact bmax - bsecond
    assert body["enforcement_status"] == "pending"

