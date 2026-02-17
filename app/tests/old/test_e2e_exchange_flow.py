import uuid
from fastapi.testclient import TestClient
from app.main import create_app


def test_full_exchange_lifecycle():
    app = create_app()
    client = TestClient(app)

    # Login authority
    auth = client.post(
        "/v1/auth/login",
        json={"workflow": "clearland", "username": "auth1", "password": "pass123"},
    ).json()["access_token"]

    # Create project
    pr = client.post(
        "/v1/projects?workflow=clearland",
        headers={"Authorization": f"Bearer {auth}"},
        json={
            "workflow": "clearland",
            "title": "E2E Project",
            "metadata": {
                "kind": "clearland",
                "city": "Mumbai",
                "zone": "Z1",
                "parcel_area_sq_m": 1000,
                "parcel_size_band": "L",
                "parcel_status": "available",
            },
        },
    ).json()
    pid = pr["projectId"]

    # Publish
    client.post(
        f"/v1/projects/{pid}/publish?workflow=clearland",
        headers={"Authorization": f"Bearer {auth}"},
    )

    # Open round
    client.post(
        "/v1/rounds/open",
        headers={"Authorization": f"Bearer {auth}"},
        json={"workflow": "clearland", "projectId": pid, "t": 0},
    )

    # Buyer submits quote
    buyer = client.post(
        "/v1/auth/login",
        json={"workflow": "clearland", "username": "buyerA", "password": "pass123"},
    ).json()["access_token"]

    qb = client.post(
        f"/v1/bids/quote?workflow=clearland&projectId={pid}&t=0",
        headers={"Authorization": f"Bearer {buyer}", "Idempotency-Key": "q1"},
        json={
            "workflow": "clearland",
            "projectId": pid,
            "t": 0,
            "qbundle_inr": "2000.00",
        },
    )
    assert qb.status_code == 200

    # Developer submits ask
    dev = client.post(
        "/v1/auth/login",
        json={"workflow": "clearland", "username": "dev1", "password": "pass123"},
    ).json()["access_token"]

    ab = client.post(
        f"/v1/bids/ask?workflow=clearland&projectId={pid}&t=0",
        headers={"Authorization": f"Bearer {dev}", "Idempotency-Key": "a1"},
        json={
            "workflow": "clearland",
            "projectId": pid,
            "t": 0,
            "dcu_units": 10,
            "ask_price_per_unit_inr": 150,
        },
    )
    assert ab.status_code == 200

    # Close + lock
    client.post(
        "/v1/rounds/close",
        headers={"Authorization": f"Bearer {auth}"},
        json={"workflow": "clearland", "projectId": pid, "t": 0},
    )
    client.post(
        "/v1/rounds/lock",
        headers={"Authorization": f"Bearer {auth}"},
        json={"workflow": "clearland", "projectId": pid, "t": 0},
    )

    # Matching
    m = client.get(
        f"/v1/matching/result?workflow=clearland&projectId={pid}&t=0",
        headers={"Authorization": f"Bearer {auth}"},
    )
    assert m.status_code == 200

    # Settlement (Vickrey)
    s = client.get(
        f"/v1/settlement/result?workflow=clearland&projectId={pid}&t=0",
        headers={"Authorization": f"Bearer {auth}"},
    )
    assert s.status_code == 200

    # Simulate default → penalty
    d = client.post(
        f"/v1/events/developer/default?workflow=clearland&projectId={pid}",
        headers={"Authorization": f"Bearer {auth}"},
        json={"workflow": "clearland", "projectId": pid, "t": 0, "reason": "test"},
    )
    assert d.status_code == 200

    # Penalty
    p = client.get(
        f"/v1/events/penalty?workflow=clearland&projectId={pid}&t=0",
        headers={"Authorization": f"Bearer {auth}"},
    )
    assert p.status_code in (200, 404)

    # Compensatory
    c = client.get(
        f"/v1/events/compensatory?workflow=clearland&projectId={pid}&t=0",
        headers={"Authorization": f"Bearer {auth}"},
    )
    assert c.status_code in (200, 404)

    # Contract
    contracts = client.get(
        f"/v1/contracts/byProject?workflow=clearland&projectId={pid}",
        headers={"Authorization": f"Bearer {auth}"},
    )
    assert contracts.status_code == 200

    # Audit
    audit = client.get(
        f"/v1/ledger/audit?workflow=clearland&projectId={pid}",
        headers={"Authorization": f"Bearer {auth}"},
    )
    assert audit.status_code == 200
