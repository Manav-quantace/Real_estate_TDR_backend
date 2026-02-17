import os, uuid, pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import create_app
from app.db.base import Base
from app.db.session import get_db
from app.models.project import Project


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL to run DB tests.")
def test_subsidized_valuer_storage_and_readonly_after_publish():
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

    # Seed subsidized project (not published)
    db = TestingSessionLocal()
    pid = uuid.uuid4()
    db.add(Project(
        id=pid,
        workflow="subsidized",
        title="MHADA Redevelopment X",
        status="draft",
        is_published=False,
        metadata_json={"kind":"subsidized","scheme_type":"MHADA","project_city":"Mumbai","project_zone":"Z1","valuation_status":"not_submitted"},
    ))
    db.commit()
    db.close()

    # Login as authority/auditor (must be permitted)
    tok = client.post("/v1/auth/login", json={"workflow":"subsidized","username":"auth1","password":"pass123"}).json()["access_token"]

    # Submit valuation (pre-publish) OK
    r = client.post(
        "/v1/subsidized/valuer",
        headers={"Authorization": f"Bearer {tok}"},
        json={"workflow":"subsidized","projectId":str(pid),"valuationInr":123456789.0,"status":"submitted"},
    )
    assert r.status_code == 200, r.text

    # Publish project (authority) using Part 20 publish endpoint
    rp = client.post(f"/v1/projects/{pid}/publish?workflow=subsidized", headers={"Authorization": f"Bearer {tok}"})
    assert rp.status_code == 200, rp.text
    assert rp.json()["isPublished"] is True

    # Submit valuation after publish => rejected
    r2 = client.post(
        "/v1/subsidized/valuer",
        headers={"Authorization": f"Bearer {tok}"},
        json={"workflow":"subsidized","projectId":str(pid),"valuationInr":999.0,"status":"submitted"},
    )
    assert r2.status_code == 409, r2.text

    # Retrieve latest
    rg = client.get(
        f"/v1/subsidized/valuer?workflow=subsidized&projectId={pid}",
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert rg.status_code == 200, rg.text
    body = rg.json()
    assert body["latest"]["valuationInr"] == "123456789.00"
    assert body["latest"]["status"] == "submitted"
