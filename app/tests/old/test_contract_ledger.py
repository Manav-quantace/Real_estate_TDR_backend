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
def test_contract_generation_and_ledger():
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

    db = TestingSessionLocal()
    pid = uuid.uuid4()
    db.add(Project(id=pid, workflow="clearland", title="Contract Test", metadata_json={}))
    db.commit()

    # Locked round
    rnd = Round(workflow="clearland", project_id=pid, t=0, state="locked", is_open=False, is_locked=True)
    db.add(rnd); db.commit(); db.refresh(rnd)

    # Locked ask and 2 quotes to allow settlement to compute (Part 14)
    db.add(AskBid(workflow="clearland", project_id=pid, round_id=rnd.id, t=0, participant_id="devA",
                  state="locked", payload_json={}, total_ask_inr="800.00", signature_hash="ASKHASH"))
    db.add(QuoteBid(workflow="clearland", project_id=pid, round_id=rnd.id, t=0, participant_id="buyerA",
                    state="locked", payload_json={"qbundle_inr":"950.00"}, signature_hash="QHASH1"))
    db.add(QuoteBid(workflow="clearland", project_id=pid, round_id=rnd.id, t=0, participant_id="buyerB",
                    state="locked", payload_json={"qbundle_inr":"900.00"}, signature_hash="QHASH2"))
    db.commit()
    db.close()

    # Listing should create contract (idempotent) if settlement is settled
    r = client.get(f"/v1/contracts/byProject?workflow=clearland&projectId={pid}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["workflow"] == "clearland"
    assert body["projectId"] == str(pid)
    assert len(body["contracts"]) >= 1
    c = body["contracts"][0]
    assert c["version"] == 1
    assert c["contractHash"]
    assert c["ownershipDetails"]["project_id"] == str(pid)

    # GET by contract id
    cid = c["contractId"]
    r2 = client.get(f"/v1/contracts/{cid}")
    assert r2.status_code == 200
    c2 = r2.json()
    assert c2["contractId"] == cid
    assert c2["contractHash"] == c["contractHash"]
