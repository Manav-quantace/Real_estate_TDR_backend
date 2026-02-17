from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def login(workflow: str, username: str, password: str) -> str:
    r = client.post("/v1/auth/login", json={"workflow": workflow, "username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_buyer_can_submit_quote_but_not_ask():
    token = login("saleable", "buyer1", "pass123")

    r = client.post("/v1/bids/quote?workflow=saleable&projectId=PRJ-1", json={"qbundle": 123}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200

    r2 = client.post("/v1/bids/ask?workflow=saleable&projectId=PRJ-1", json={"dcu_units": 10, "ask_price": 5}, headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 403


def test_developer_ask_is_dcu_only_no_tdr_fields():
    token = login("clearland", "dev1", "pass123")

    ok = client.post(
        "/v1/bids/ask?workflow=clearland&projectId=PRJ-CL-1",
        json={"dcu_units": 100, "ask_price_per_unit": 50000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ok.status_code == 200

    bad = client.post(
        "/v1/bids/ask?workflow=clearland&projectId=PRJ-CL-1",
        json={"dcu_units": 100, "ask_price_per_unit": 50000, "tdru": 10},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert bad.status_code == 403


def test_slum_dweller_only_preferences():
    token = login("slum", "slumdw1", "pass123")

    ok = client.post(
        "/v1/bids/preferences?workflow=slum&projectId=PRJ-SL-1",
        json={"rehab_option": "A", "consent": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ok.status_code == 200

    bad = client.post(
        "/v1/bids/quote?workflow=slum&projectId=PRJ-SL-1",
        json={"qbundle": 999},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert bad.status_code == 403