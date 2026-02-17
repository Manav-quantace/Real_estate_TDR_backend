# app/core/clearland_phase_graph.py
from app.core.clearland_phases import ClearlandPhaseType

ALLOWED_PHASE_TRANSITIONS = {
    None: {ClearlandPhaseType.INIT},

    ClearlandPhaseType.INIT: {
        ClearlandPhaseType.DEVELOPER_ASK_OPEN,
    },

    ClearlandPhaseType.DEVELOPER_ASK_OPEN: {
        ClearlandPhaseType.BUYER_BIDDING_OPEN,
    },

    ClearlandPhaseType.BUYER_BIDDING_OPEN: {
        ClearlandPhaseType.PREFERENCES_COLLECTED,
    },

    ClearlandPhaseType.PREFERENCES_COLLECTED: {
        ClearlandPhaseType.LOCKED,
    },

    ClearlandPhaseType.LOCKED: {
        ClearlandPhaseType.SETTLED,
    },

    ClearlandPhaseType.SETTLED: {
        ClearlandPhaseType.CLOSED,
    },

    ClearlandPhaseType.CLOSED: set(),
}