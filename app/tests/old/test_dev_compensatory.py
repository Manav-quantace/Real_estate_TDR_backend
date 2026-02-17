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
def test_developer_two_tier_compensatory_transfer():
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

    # Setup project + locked round
    db = TestingSessionLocal()
    pid = uuid.uuid4()
    db.add(Project(id=pid, workflow="clearland", title="DevComp Test", metadata_json={}))
    db.commit()

    rnd = Round(workflow="clearland", project_id=pid, t=0, state="locked", is_open=False, is_locked=True)
    db.add(rnd)
    db.commit()
    db.refresh(rnd)

    # Asks (winner will be min ask: 800), next eligible min is 820
    # Winner includes compensatory fields
    db.add(AskBid(
        workflow="clearland", project_id=pid, round_id=rnd.id, t=0, participant_id="devW",
        state="locked", payload_json={}, total_ask_inr="800.00",
        comp_dcu_units="10.0000", comp_ask_price_per_unit_inr="60000.00",
        signature_hash="ASKW"
    ))
    db.add(AskBid(
        workflow="clearland", project_id=pid, round_id=rnd.id, t=0, participant_id="devN",
        state="locked", payload_json={}, total_ask_inr="820.00",
        signature_hash="ASKN"
    ))
    db.add(AskBid(
        workflow="clearland", project_id=pid, round_id=rnd.id, t=0, participant_id="devX",
        state="locked", payload_json={}, total_ask_inr="900.00",
        signature_hash="ASKX"
    ))

    # Quotes needed so settlement can exist (matching+settlement will run)
    db.add(QuoteBid(workflow="clearland", project_id=pid, round_id=rnd.id, t=0, participant_id="buyerA",
                    state="locked", payload_json={"qbundle_inr":"950.00"}))
    db.add(QuoteBid(workflow="clearland", project_id=pid, round_id=rnd.id, t=0, participant_id="buyerB",
                    state="locked", payload_json={"qbundle_inr":"900.00"}))
    db.commit()
    db.close()

    # Authority declares developer default
    auth_token = client.post("/v1/auth/login", json={"workflow":"clearland","username":"auth1","password":"pass123"}).json()["access_token"]

    d = client.post(
        f"/v1/events/developer/default?workflow=clearland&projectId={pid}",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"workflow":"clearland","projectId":str(pid),"t":0,"reason":"dev_default"},
    )
    assert d.status_code == 200, d.text

    # Compute developer compensatory transfer
    r = client.get(
        f"/v1/events/developer/compensatory?workflow=clearland&projectId={pid}&t=0",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] in {"computed", "no_transfer_no_eligible_developers"}

    # If computed: new winner is the next min ask = 820 (devN)
    if body["status"] == "computed":
        assert body["new_min_ask_total_inr"] == "820.00"
        assert body["comp_dcu_units"] == "10.0000"
        assert body["comp_ask_price_per_unit_inr"] == "60000.00"