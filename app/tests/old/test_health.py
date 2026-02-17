from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_workflow_guard_blocks_missing_scope():
    # bids endpoint requires workflow & projectId
    r = client.post("/v1/bids/quote", json={})
    assert r.status_code == 400

    r2 = client.post("/v1/bids/quote?workflow=saleable&projectId=PRJ-1", json={})
    assert r2.status_code == 200

