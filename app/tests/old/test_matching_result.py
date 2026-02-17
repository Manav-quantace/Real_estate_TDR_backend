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
def test_matching_min_ask_max_quote_only_after_lock():
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

    # Setup: project + round t=0
    db = TestingSessionLocal()
    pid = uuid.uuid4()
    db.add(Project(id=pid, workflow="clearland", title="Match Test", metadata_json={}))
    db.commit()

    rnd = Round(workflow="clearland", project_id=pid, t=0, state="submitted", is_open=False, is_locked=False)
    db.add(rnd)
    db.commit()
    db.refresh(rnd)

    # Insert locked bids ONLY after we lock round; but for test we set bid state locked while round unlocked to ensure endpoint blocks.
    db.add(AskBid(
        workflow="clearland", project_id=pid, round_id=rnd.id, t=0, participant_id="devA",
        state="locked", payload_json={}, total_ask_inr="900.00"
    ))
    db.add(AskBid(
        workflow="clearland", project_id=pid, round_id=rnd.id, t=0, participant_id="devB",
        state="locked", payload_json={}, total_ask_inr="800.00"
    ))
    db.add(QuoteBid(
        workflow="clearland", project_id=pid, round_id=rnd.id, t=0, participant_id="buyerA",
        state="locked", payload_json={"qbundle_inr":"850.00"}
    ))
    db.add(QuoteBid(
        workflow="clearland", project_id=pid, round_id=rnd.id, t=0, participant_id="buyerB",
        state="locked", payload_json={"qbundle_inr":"950.00"}
    ))
    db.commit()

    # Not locked -> 409
    r = client.get(f"/v1/matching/result?workflow=clearland&projectId={pid}&t=0")
    assert r.status_code == 409

    # Now lock round
    rnd.is_locked = True
    rnd.state = "locked"
    db.add(rnd)
    db.commit()
    db.close()

    # Locked -> compute
    r2 = client.get(f"/v1/matching/result?workflow=clearland&projectId={pid}&t=0")
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["min_ask_total_inr"] == "800.00"
    assert body["max_quote_inr"] == "950.00"
    assert body["matched"] is True

    # Second call returns stored result (idempotent)
    r3 = client.get(f"/v1/matching/result?workflow=clearland&projectId={pid}&t=0")
    assert r3.status_code == 200
    assert r3.json()["computed_at_iso"] == body["computed_at_iso"]