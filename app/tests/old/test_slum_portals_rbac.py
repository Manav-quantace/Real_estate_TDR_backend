import os, uuid, pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import create_app
from app.db.base import Base
from app.db.session import get_db
from app.models.project import Project


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL to run DB tests.")
def test_slum_portals_membership_and_rbac():
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

    # Seed slum project
    db = TestingSessionLocal()
    pid = uuid.uuid4()
    db.add(Project(
        id=pid,
        workflow="slum",
        title="Slum Project 1",
        metadata_json={
            "kind": "slum",
            "portal_slum_dweller_enabled": True,
            "portal_slum_land_developer_enabled": True,
            "portal_affordable_housing_dev_enabled": True,
            "government_land_type": "road",
            "jurisdiction_body": "State",
            "project_city": "Mumbai",
            "project_zone": "Zone-1",
        }
    ))
    db.commit()
    db.close()

    # Login authority and enroll memberships
    tok_auth = client.post("/v1/auth/login", json={"workflow":"slum","username":"auth1","password":"pass123"}).json()["access_token"]

    client.post("/v1/slum/enroll", headers={"Authorization": f"Bearer {tok_auth}"}, json={
        "workflow": "slum",
        "projectId": str(pid),
        "participantId": "dweller-1",
        "portalType": "SLUM_DWELLER"
    })
    client.post("/v1/slum/enroll", headers={"Authorization": f"Bearer {tok_auth}"}, json={
        "workflow": "slum",
        "projectId": str(pid),
        "participantId": "dev-1",
        "portalType": "SLUM_LAND_DEVELOPER"
    })
    client.post("/v1/slum/enroll", headers={"Authorization": f"Bearer {tok_auth}"}, json={
        "workflow": "slum",
        "projectId": str(pid),
        "participantId": "ah-1",
        "portalType": "AFFORDABLE_HOUSING_DEV"
    })

    # Login dweller and check portal status shows member=true for SLUM_DWELLER
    tok_dw = client.post("/v1/auth/login", json={"workflow":"slum","username":"dweller-1","password":"pass123"}).json()["access_token"]
    r = client.get(f"/v1/slum/portals?workflow=slum&projectId={pid}", headers={"Authorization": f"Bearer {tok_dw}"})
    assert r.status_code == 200
    portals = {p["portalType"]: p for p in r.json()["portals"]}
    assert portals["SLUM_DWELLER"]["member"] is True
    assert portals["SLUM_LAND_DEVELOPER"]["member"] is False
    assert portals["AFFORDABLE_HOUSING_DEV"]["member"] is False

    # A developer not enrolled should not show member=true
    tok_dev = client.post("/v1/auth/login", json={"workflow":"slum","username":"dev-1","password":"pass123"}).json()["access_token"]
    r2 = client.get(f"/v1/slum/portals?workflow=slum&projectId={pid}", headers={"Authorization": f"Bearer {tok_dev}"})
    assert r2.status_code == 200
    portals2 = {p["portalType"]: p for p in r2.json()["portals"]}
    assert portals2["SLUM_LAND_DEVELOPER"]["member"] is True