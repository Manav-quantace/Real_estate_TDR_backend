import os, uuid, pytest
from fastapi.testclient import TestClient

from app.main import create_app


FORBIDDEN_KEYS = {
    "orderbook", "ask_ladder", "bid_ladder", "price_ladder", "all_bids", "bids", "asks", "quotes"
}

def contains_forbidden_shape(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            lk = str(k).lower()
            if lk in FORBIDDEN_KEYS or "orderbook" in lk or "ladder" in lk:
                return True
            if contains_forbidden_shape(v):
                return True
    if isinstance(obj, list):
        # lists are allowed in general, but not if they look like bid lists
        # We'll detect list of dicts with typical bid fields
        if obj and isinstance(obj[0], dict):
            sample_keys = set(obj[0].keys())
            if {"bidId", "participantId"}.issubset(sample_keys):
                return True
        for x in obj:
            if contains_forbidden_shape(x):
                return True
    return False


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL to run integration DB tests.")
def test_no_orderbook_routes_in_api():
    app = create_app()
    routes = [getattr(r, "path", "") for r in app.router.routes]
    banned = [p for p in routes if "orderbook" in p.lower() or "bids/all" in p.lower()]
    assert not banned, f"Forbidden routes exist: {banned}"


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL to run integration DB tests.")
def test_bid_submit_receipt_has_no_leaks():
    app = create_app()
    client = TestClient(app)

    # Assume your auth login returns token
    tok_a = client.post("/v1/auth/login", json={"workflow":"clearland","username":"buyerA","password":"pass123"}).json()["access_token"]
    tok_b = client.post("/v1/auth/login", json={"workflow":"clearland","username":"buyerB","password":"pass123"}).json()["access_token"]

    # Create a project as authority and open round etc. (depends on your earlier parts)
    tok_auth = client.post("/v1/auth/login", json={"workflow":"clearland","username":"auth1","password":"pass123"}).json()["access_token"]
    pr = client.post("/v1/projects?workflow=clearland", headers={"Authorization": f"Bearer {tok_auth}"}, json={
        "workflow":"clearland","title":"P","metadata":{"kind":"clearland","city":"Mumbai","zone":"W1","parcel_area_sq_m":100,"parcel_size_band":"S","parcel_status":"available"}
    }).json()
    pid = pr["projectId"]

    # Open round (authority)
    client.post("/v1/rounds/open", headers={"Authorization": f"Bearer {tok_auth}"}, json={"workflow":"clearland","projectId":pid,"t":0})

    # Buyer A submits a quote
    r = client.post(
        f"/v1/bids/quote?workflow=clearland&projectId={pid}&t=0",
        headers={"Authorization": f"Bearer {tok_a}", "Idempotency-Key":"idem-1"},
        json={"workflow":"clearland","projectId":pid,"t":0,"qbundle_inr":"1000.00"},
    )
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert "bidId" in body
    assert not contains_forbidden_shape(body)

    # Buyer B tries to fetch "my bids" - must not include buyer A
    rb = client.get(
        f"/v1/bids/my?workflow=clearland&projectId={pid}&t=0",
        headers={"Authorization": f"Bearer {tok_b}"},
    )
    assert rb.status_code == 200, rb.text
    bbody = rb.json()
    # Ensure it doesn't contain buyerA
    assert "buyerA" not in str(bbody), "Leak: other participant appears in my-bids response"


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL to run integration DB tests.")
def test_idempotency_replay_and_conflict():
    app = create_app()
    client = TestClient(app)

    tok_auth = client.post("/v1/auth/login", json={"workflow":"clearland","username":"auth1","password":"pass123"}).json()["access_token"]
    tok_a = client.post("/v1/auth/login", json={"workflow":"clearland","username":"buyerA","password":"pass123"}).json()["access_token"]

    pr = client.post("/v1/projects?workflow=clearland", headers={"Authorization": f"Bearer {tok_auth}"}, json={
        "workflow":"clearland","title":"P2","metadata":{"kind":"clearland","city":"Mumbai","zone":"W1","parcel_area_sq_m":100,"parcel_size_band":"S","parcel_status":"available"}
    }).json()
    pid = pr["projectId"]
    client.post("/v1/rounds/open", headers={"Authorization": f"Bearer {tok_auth}"}, json={"workflow":"clearland","projectId":pid,"t":0})

    idem = "idem-same"
    payload = {"workflow":"clearland","projectId":pid,"t":0,"qbundle_inr":"1111.00"}

    r1 = client.post(
        f"/v1/bids/quote?workflow=clearland&projectId={pid}&t=0",
        headers={"Authorization": f"Bearer {tok_a}", "Idempotency-Key": idem},
        json=payload,
    )
    assert r1.status_code in (200, 201), r1.text
    b1 = r1.json()

    # Replay identical should return same response (bidId stable)
    r2 = client.post(
        f"/v1/bids/quote?workflow=clearland&projectId={pid}&t=0",
        headers={"Authorization": f"Bearer {tok_a}", "Idempotency-Key": idem},
        json=payload,
    )
    assert r2.status_code == r1.status_code
    assert r2.json() == b1

    # Conflict: same key, different payload => 409
    r3 = client.post(
        f"/v1/bids/quote?workflow=clearland&projectId={pid}&t=0",
        headers={"Authorization": f"Bearer {tok_a}", "Idempotency-Key": idem},
        json={"workflow":"clearland","projectId":pid,"t":0,"qbundle_inr":"2222.00"},
    )
    assert r3.status_code == 409, r3.text


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL to run integration DB tests.")
def test_rate_limit_blocks_spam():
    app = create_app()
    client = TestClient(app)

    tok_auth = client.post("/v1/auth/login", json={"workflow":"clearland","username":"auth1","password":"pass123"}).json()["access_token"]
    tok_a = client.post("/v1/auth/login", json={"workflow":"clearland","username":"buyerA","password":"pass123"}).json()["access_token"]

    pr = client.post("/v1/projects?workflow=clearland", headers={"Authorization": f"Bearer {tok_auth}"}, json={
        "workflow":"clearland","title":"P3","metadata":{"kind":"clearland","city":"Mumbai","zone":"W1","parcel_area_sq_m":100,"parcel_size_band":"S","parcel_status":"available"}
    }).json()
    pid = pr["projectId"]
    client.post("/v1/rounds/open", headers={"Authorization": f"Bearer {tok_auth}"}, json={"workflow":"clearland","projectId":pid,"t":0})

    # submit > 10 quickly => expect 429 at some point
    got_429 = False
    for i in range(15):
        r = client.post(
            f"/v1/bids/quote?workflow=clearland&projectId={pid}&t=0",
            headers={"Authorization": f"Bearer {tok_a}", "Idempotency-Key": f"idem-{i}"},
            json={"workflow":"clearland","projectId":pid,"t":0,"qbundle_inr":str(1000+i)},
        )
        if r.status_code == 429:
            got_429 = True
            break
    assert got_429, "Expected rate limit (429) under spam submissions."