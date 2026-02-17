import os
import uuid
import pytest
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import create_app
from app.db.base import Base
from app.db.session import get_db

from app.models.project import Project
from app.models.round import Round
from app.models.government_charge import GovernmentCharge


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL to run DB tests."
)
def test_gc_gcu_recalc_creates_history_and_audit():
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

    # Create project + round
    db = TestingSessionLocal()
    pid = uuid.uuid4()
    p = Project(id=pid, workflow="saleable", title="Charge Test", metadata_json={})
    db.add(p)
    db.commit()

    r0 = Round(workflow="saleable", project_id=pid, t=0, state="draft")
    db.add(r0)
    db.commit()
    db.refresh(r0)

    # Create GC and GCU with weights/inputs
    gc = GovernmentCharge(
        workflow="saleable",
        project_id=pid,
        round_id=r0.id,
        charge_type="GC",
        weights_json={"alpha": "1", "beta": "2", "gamma": "3"},
        inputs_json={"EC": "10", "MC": "5", "HD": "1"},
    )
    gcu = GovernmentCharge(
        workflow="saleable",
        project_id=pid,
        round_id=r0.id,
        charge_type="GCU",
        weights_json={"alpha": "1", "beta": "1", "gamma": "2"},
        inputs_json={
            "IC_series": [{"t": 0, "IC": "100"}, {"t": 1, "IC": "100"}],
            "r": "0.1",
            "LUOS": "10",
        },
    )
    db.add_all([gc, gcu])
    db.commit()
    db.close()

    # login as authority to recalc
    auth = client.post(
        "/v1/auth/login",
        json={"workflow": "saleable", "username": "auth1", "password": "pass123"},
    )
    assert auth.status_code == 200
    token = auth.json()["access_token"]

    # recalc GC
    resp_gc = client.get(
        f"/v1/charges/gc?workflow=saleable&projectId={pid}&t=0&recalc=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_gc.status_code == 200, resp_gc.text
    # expected GC = 1*10 + 2*5 + 3*1 = 10 + 10 + 3 = 23
    assert Decimal(resp_gc.json()["value_inr"]) == Decimal("23.00")

    # recalc GCU
    resp_gcu = client.get(
        f"/v1/charges/gcu?workflow=saleable&projectId={pid}&t=0&recalc=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_gcu.status_code == 200, resp_gcu.text
    # value exists, components PVIC/EC should be stored in inputs now
    assert resp_gcu.json()["inputs"].get("PVIC") is not None
    assert resp_gcu.json()["inputs"].get("EC") is not None

    # non-authority cannot recalc
    buyer = client.post(
        "/v1/auth/login",
        json={"workflow": "saleable", "username": "buyer1", "password": "pass123"},
    )
    assert buyer.status_code == 200
    buyer_token = buyer.json()["access_token"]
    denied = client.get(
        f"/v1/charges/gc?workflow=saleable&projectId={pid}&t=0&recalc=true",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert denied.status_code == 403
