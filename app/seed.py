import uuid
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.project import Project
from app.models.round import Round
from app.models.unit_inventory import UnitInventory
from app.models.government_charge import GovernmentCharge

def seed():
    db: Session = SessionLocal()

    workflows = {
        "clearland": {"kind": "clearland"},
        "saleable": {"kind": "saleable"},
        "subsidized": {"kind": "subsidized"},
        "slum": {"kind": "slum"},
    }

    for wf, md in workflows.items():
        pid = uuid.uuid4()

        project = Project(
            id=pid,
            workflow=wf,
            title=f"Seed Project {wf}",
            metadata_json=md,
            is_published=True,
        )
        db.add(project)
        db.commit()

        round0 = Round(
            workflow=wf,
            project_id=pid,
            t=0,
            state="open",
            is_open=True,
            is_locked=False,
        )
        db.add(round0)
        db.commit()

        inv = UnitInventory(
            workflow=wf,
            project_id=pid,
            t=0,
            lu_units=100,
            tdru_units=50,
            pru_units=20,
            dcu_units=30,
        )
        db.add(inv)

        gc = GovernmentCharge(
            workflow=wf,
            project_id=pid,
            t=0,
            gc_value_inr=1000,
            gcu_value_inr=1500,
        )
        db.add(gc)

        db.commit()

    db.close()

if __name__ == "__main__":
    seed()