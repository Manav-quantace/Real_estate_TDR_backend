# app/services/projects_service.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from app.models.subsidized_economic_model import SubsidizedEconomicModel
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.models.project import Project


SALEABLE_IMMUTABLE_KEYS = {
    # all saleable metadata becomes read-only after publish (strict)
    "owner_type",
    "society_name",
    "owner_name",
    "consent_state",
    "bidding_window_start_iso",
    "bidding_window_end_iso",
    "property_city",
    "property_zone",
    "property_address",
    "builtup_area_sqft",
}


def _compute_book_values(lu_open, pvic, alpha, beta, gamma):
    ec = (gamma or 0) * lu_open
    gci = (alpha or 0) * (pvic or 0)
    gce = (beta or 0) * ec
    gcu = gci + gce
    return ec, gci, gce, gcu


class ProjectsService:
    def create(
        self, db: Session, *, workflow: str, title: str, metadata: Dict[str, Any]
    ) -> Project:
        p = Project(
            workflow=workflow,
            title=title,
            status="draft",
            is_published=False,
            published_at=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            metadata_json=metadata,
        )
        db.add(p)
        db.commit()
        db.refresh(p)

        if workflow == "subsidized":
            em = metadata["economic_model"]

            policy = em["POLICY"]
            lu_total = policy["LU"]["total"]
            lu_open = policy["LU"]["open_space"]
            pvic = policy["PVIC"]
            alpha = policy["WEIGHTS"]["alpha"]
            beta = policy["WEIGHTS"]["beta"]
            gamma = policy["WEIGHTS"]["gamma"]

            ec, gci, gce, gcu = _compute_book_values(lu_open, pvic, alpha, beta, gamma)

            model = SubsidizedEconomicModel(
                project_id=p.id,
                version=1,
                lu_total=lu_total,
                lu_open_space=lu_open,
                pvic=pvic,
                alpha=alpha,
                beta=beta,
                gamma=gamma,
                ec=ec,
                gci=gci,
                gce=gce,
                gcu=gcu,
                computed_at=datetime.now(timezone.utc),
            )
            db.add(model)
            db.commit()

        return p

    def get(
        self, db: Session, *, workflow: str, project_id: uuid.UUID
    ) -> Optional[Project]:
        return db.execute(
            select(Project).where(
                Project.workflow == workflow, Project.id == project_id
            )
        ).scalar_one_or_none()

    def list(
        self,
        db: Session,
        *,
        workflow: str,
        filters: Dict[str, Any],
        limit: int = 200,
    ) -> List[Project]:
        stmt = select(Project).where(Project.workflow == workflow)

        # Workflow-specific filter support (only for list; no policy inference)
        if workflow == "clearland":
            if filters.get("city"):
                stmt = stmt.where(
                    Project.metadata_json["city"].astext == str(filters["city"])
                )
            if filters.get("zone"):
                stmt = stmt.where(
                    Project.metadata_json["zone"].astext == str(filters["zone"])
                )
            if filters.get("parcel_size_band"):
                stmt = stmt.where(
                    Project.metadata_json["parcel_size_band"].astext
                    == str(filters["parcel_size_band"])
                )
            if filters.get("status"):
                stmt = stmt.where(
                    Project.metadata_json["parcel_status"].astext
                    == str(filters["status"])
                )
        elif workflow in {"slum", "subsidized", "saleable"}:
            # generic city/zone if present in metadata
            if filters.get("city"):
                # slum/subsidized use project_city; saleable uses property_city
                city_key = "property_city" if workflow == "saleable" else "project_city"
                stmt = stmt.where(
                    Project.metadata_json[city_key].astext == str(filters["city"])
                )
            if filters.get("zone"):
                zone_key = "property_zone" if workflow == "saleable" else "project_zone"
                stmt = stmt.where(
                    Project.metadata_json[zone_key].astext == str(filters["zone"])
                )

        stmt = stmt.limit(limit)
        return db.execute(stmt).scalars().all()

    def patch(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
        title: Optional[str],
        status: Optional[str],
        metadata: Optional[Dict[str, Any]],
    ) -> Project:
        p = self.get(db, workflow=workflow, project_id=project_id)
        if not p:
            raise ValueError("Project not found.")

        # Enforce read-only-after-publish for saleable metadata
        if p.is_published and workflow == "saleable" and metadata is not None:
            # Compare keys: deny if any immutable differs
            for k in SALEABLE_IMMUTABLE_KEYS:
                old = (p.metadata_json or {}).get(k)
                new = (metadata or {}).get(k)
                if new is not None and new != old:
                    raise ValueError(
                        f"Saleable project metadata is read-only after publish; attempted change: {k}"
                    )

        # For all workflows: allow title/status updates; allow metadata update only pre-publish
        if metadata is not None:
            if p.is_published and workflow != "saleable":
                # Keep strict: metadata is also read-only after publish for govt workflows unless you later loosen it.
                raise ValueError("Project metadata is read-only after publish.")
            p.metadata_json = metadata

        if title is not None:
            p.title = title
        if status is not None:
            p.status = status

        p.updated_at = datetime.now(timezone.utc)
        db.add(p)
        db.commit()
        db.refresh(p)
        return p

    def publish(self, db: Session, *, workflow: str, project_id: uuid.UUID) -> Project:
        p = self.get(db, workflow=workflow, project_id=project_id)
        if not p:
            raise ValueError("Project not found.")

        if workflow == "subsidized":
            row = (
                db.query(SubsidizedEconomicModel)
                .filter_by(project_id=project_id)
                .order_by(SubsidizedEconomicModel.version.desc())
                .first()
            )
            if not row:
                raise ValueError("No economic model found for subsidized project.")
            row.is_published_version = True
            db.add(row)

        if p.is_published:
            return p
        p.is_published = True
        p.published_at = datetime.now(timezone.utc)
        p.status = "published"
        p.updated_at = datetime.now(timezone.utc)
        db.add(p)
        db.commit()
        db.refresh(p)
        return p
