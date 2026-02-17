from fastapi import APIRouter

from app.api.v1.health import router as health_router

# ⚠️ LEGACY (DISABLED WRITE ROUTES — MUST LOAD FIRST)
from app.api.v1.bids import router as bids_router

# CANONICAL APIs
from app.api.v1.bids_quote import router as bids_quote_router
from app.api.v1.bids_ask import router as bids_ask_router
from app.api.v1.preferences import router as preferences_router

from app.api.v1.matching import router as matching_router
from app.api.v1.settlement import router as settlement_router
from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.params import router as params_router
from app.api.v1.charges import router as charges_router
from app.api.v1.rounds import router as rounds_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.events import router as events_router
from app.api.v1.compensatory import router as compensatory_router
from app.api.v1.dev_compensatory import router as dev_comp_router
from app.api.v1.contracts import router as contracts_router

# ✅ FIXED: DISTINCT NAMES
from app.api.v1.ledger import router as ledger_router
from app.api.v1.ledger_audit import router as ledger_audit_router

from app.api.v1.projects import router as projects_router
from app.api.v1.slum_portals import router as slum_portals_router
from app.api.v1.slum_enroll import router as slum_enroll_router
from app.api.v1.subsidized_valuer import router as subsidized_valuer_router
from app.api.v1.export import router as export_router
from app.api.v1.saleable import router as saleable_router
from app.api.v1.developer_ask import router as developer_ask_router
from app.api.v1.participants import router as participants_router
from app.api.v1.admin.projects import router as admin_projects_router
from app.api.v1.authority.settlement_diagnostics import (
    router as settlement_diagnostics_router
)
from app.api.v1.slum_rounds import router as slum_rounds_router
from app.api.v1.slum_consents import router as slum_consents_router
from app.api.v1.slum_documents import router as slum_documents_router
from app.api.v1.slum_portal_participants import router as slum_portal_participants_router
from app.api.v1.bids_my import router as bids_my_router
from app.api.v1.slum_participants import router as slum_participants_router
from app.api.v1.unit_inventory import router as unit_inventory_router
from app.api.v1.government_charges import router as charges_router
from app.api.v1.clearland_phase import router as clearland_phase_router
from app.api.v1.clearland_memberships import router as clearland_memberships_router


v1_router = APIRouter()

# ------------------------------------------------------------------
# SYSTEM / CORE
# ------------------------------------------------------------------
v1_router.include_router(health_router, tags=["health"])
v1_router.include_router(auth_router, tags=["auth"])
v1_router.include_router(audit_router, tags=["audit"])

# ------------------------------------------------------------------
# ⚠️ LEGACY BIDS (DISABLED — LOAD FIRST)
# ------------------------------------------------------------------
v1_router.include_router(bids_router, tags=["bids-legacy"])

# ------------------------------------------------------------------
# MARKET OPS
# ------------------------------------------------------------------
v1_router.include_router(bids_quote_router, tags=["bids"])
v1_router.include_router(bids_ask_router, tags=["bids"])
v1_router.include_router(preferences_router, tags=["preferences"])
v1_router.include_router(rounds_router, tags=["rounds"])
v1_router.include_router(matching_router, tags=["matching"])
v1_router.include_router(settlement_router, tags=["settlement"])
v1_router.include_router(bids_my_router, tags=["bids-my"])
v1_router.include_router(slum_participants_router, tags=["slum-participants"])

# ------------------------------------------------------------------
# PARAMETERS / FEEDBACK
# ------------------------------------------------------------------
v1_router.include_router(params_router, tags=["params"])
v1_router.include_router(charges_router, tags=["charges"])
v1_router.include_router(feedback_router, tags=["feedback"])

# ------------------------------------------------------------------
# EVENTS / CONTRACTS / LEDGER
# ------------------------------------------------------------------
v1_router.include_router(events_router, tags=["events"])
v1_router.include_router(compensatory_router, tags=["events"])
v1_router.include_router(dev_comp_router, tags=["events"])
v1_router.include_router(contracts_router, tags=["contracts"])

# ✅ LEDGER (SOURCE OF TRUTH)
v1_router.include_router(ledger_router, tags=["ledger"])
v1_router.include_router(ledger_audit_router, tags=["ledger-audit"])

# ------------------------------------------------------------------
# PROJECTS / WORKFLOWS
# ------------------------------------------------------------------
v1_router.include_router(projects_router, tags=["projects"])
v1_router.include_router(saleable_router, tags=["saleable"])
v1_router.include_router(developer_ask_router, tags=["developer_ask"])
v1_router.include_router(clearland_phase_router, tags=["clearland"])
v1_router.include_router(clearland_memberships_router, tags=["clearland"])

# ------------------------------------------------------------------
# SLUM / SUBSIDIZED
# ------------------------------------------------------------------
v1_router.include_router(slum_portals_router, tags=["slum"])
v1_router.include_router(slum_enroll_router, tags=["slum"])
v1_router.include_router(slum_rounds_router, tags=["slum"])
v1_router.include_router(slum_consents_router, tags=["slum"])
v1_router.include_router(slum_documents_router, tags=["slum"])
v1_router.include_router(slum_portal_participants_router, tags=["slum"])
v1_router.include_router(subsidized_valuer_router, tags=["subsidized"])

# ------------------------------------------------------------------
# ADMIN
# ------------------------------------------------------------------
v1_router.include_router(participants_router, tags=["participants"])
v1_router.include_router(admin_projects_router, tags=["admin"])
v1_router.include_router(export_router, tags=["export"])

# ------------------------------------------------------------------
# AUTHORITY
# ------------------------------------------------------------------
v1_router.include_router(settlement_diagnostics_router, tags=["authority"])
v1_router.include_router(unit_inventory_router, tags=["inventory"])
v1_router.include_router(charges_router, tags=["government_charges"])
