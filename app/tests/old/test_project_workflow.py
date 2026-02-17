import os, uuid, pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import create_app
from app.db.base import Base
from app.db.session import get_db


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL to run DB tests."
)
def test_projects_crud_and_saleable_readonly_after_publish():
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

    # Login as OWNER_SOCIETY for saleable
    tok_owner = client.post(
        "/v1/auth/login",
        json={"workflow": "saleable", "username": "owner1", "password": "pass123"},
    ).json()["access_token"]

    saleable_payload = {
        "workflow": "saleable",
        "title": "Society Redevelopment A",
        "metadata": {
            "kind": "saleable",
            "owner_type": "cooperative_society",
            "society_name": "ABC CHS",
            "owner_name": None,
            "consent_state": "consented",
            "bidding_window_start_iso": "2026-01-01T10:00:00Z",
            "bidding_window_end_iso": "2026-01-10T10:00:00Z",
            "property_city": "Mumbai",
            "property_zone": "Kandivali",
            "property_address": "B-706 ...",
            "builtup_area_sqft": 10000.0,
        },
    }

    r = client.post(
        "/v1/projects?workflow=saleable",
        json=saleable_payload,
        headers={"Authorization": f"Bearer {tok_owner}"},
    )
    assert r.status_code == 200, r.text
    p = r.json()
    pid = p["projectId"]

    # Publish
    rp = client.post(
        f"/v1/projects/{pid}/publish?workflow=saleable",
        headers={"Authorization": f"Bearer {tok_owner}"},
    )
    assert rp.status_code == 200, rp.text
    assert rp.json()["isPublished"] is True

    # Attempt to change immutable saleable metadata after publish -> reject
    patch = {
        "metadata": {
            **saleable_payload["metadata"],
            "property_zone": "Borivali",  # immutable field change
        }
    }
    rbad = client.patch(
        f"/v1/projects/{pid}?workflow=saleable",
        json=patch,
        headers={"Authorization": f"Bearer {tok_owner}"},
    )
    assert rbad.status_code == 409, rbad.text


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL to run DB tests."
)
def test_clearland_list_filters():
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

    tok_auth = client.post(
        "/v1/auth/login",
        json={"workflow": "clearland", "username": "auth1", "password": "pass123"},
    ).json()["access_token"]

    def mk(title, city, zone, band, status):
        return {
            "workflow": "clearland",
            "title": title,
            "metadata": {
                "kind": "clearland",
                "city": city,
                "zone": zone,
                "parcel_area_sq_m": 500.0,
                "parcel_size_band": band,
                "parcel_status": status,
            },
        }

    client.post(
        "/v1/projects?workflow=clearland",
        json=mk("P1", "Mumbai", "W1", "M", "available"),
        headers={"Authorization": f"Bearer {tok_auth}"},
    )
    client.post(
        "/v1/projects?workflow=clearland",
        json=mk("P2", "Mumbai", "W2", "L", "reserved"),
        headers={"Authorization": f"Bearer {tok_auth}"},
    )
    client.post(
        "/v1/projects?workflow=clearland",
        json=mk("P3", "Pune", "Z1", "M", "available"),
        headers={"Authorization": f"Bearer {tok_auth}"},
    )

    r = client.get(
        "/v1/projects?workflow=clearland&city=Mumbai&parcel_size_band=M",
        headers={"Authorization": f"Bearer {tok_auth}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["workflow"] == "clearland"
    assert len(body["projects"]) == 1
    assert body["projects"][0]["metadata"]["city"] == "Mumbai"
    assert body["projects"][0]["metadata"]["parcel_size_band"] == "M"
