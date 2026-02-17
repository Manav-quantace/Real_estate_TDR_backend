from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, Tuple


def _d(x: Any) -> Decimal:
    if x is None:
        raise ValueError("Missing required numeric input.")
    try:
        return Decimal(str(x))
    except (InvalidOperation, TypeError):
        raise ValueError(f"Invalid numeric input: {x}")


def compute_gc(weights: Dict[str, Any], inputs: Dict[str, Any]) -> Decimal:
    """
    GC = α·EC + β·MC + γ·HD
    We expect weights: alpha, beta, gamma
    inputs: EC, MC, HD
    """
    alpha = _d(weights.get("alpha"))
    beta = _d(weights.get("beta"))
    gamma = _d(weights.get("gamma"))

    ec = _d(inputs.get("EC"))
    mc = _d(inputs.get("MC"))
    hd = _d(inputs.get("HD"))

    return (alpha * ec) + (beta * mc) + (gamma * hd)


def compute_pvic(ic_series: Iterable[Dict[str, Any]], r: Any) -> Decimal:
    """
    PVIC = Σ ICt/(1+r)^t
    ic_series: list of {"t": int, "IC": number}
    r: number
    """
    rr = _d(r)
    one_plus_r = Decimal("1") + rr
    if one_plus_r <= 0:
        raise ValueError("Invalid r: (1+r) must be positive.")

    total = Decimal("0")
    for row in ic_series:
        tt = int(row.get("t", 0))
        ic = _d(row.get("IC"))
        total += ic / (one_plus_r ** Decimal(tt))
    return total


def compute_gcu(weights: Dict[str, Any], inputs: Dict[str, Any]) -> Tuple[Decimal, Decimal, Decimal]:
    """
    GCU = α·PVIC + β·EC
    PVIC = Σ ICt/(1+r)^t
    EC = γ·LUOS

    Expect weights: alpha, beta, gamma
    inputs: IC_series (list), r, LUOS
    """
    alpha = _d(weights.get("alpha"))
    beta = _d(weights.get("beta"))
    gamma = _d(weights.get("gamma"))

    ic_series = inputs.get("IC_series")
    if not isinstance(ic_series, list) or len(ic_series) == 0:
        raise ValueError("inputs.IC_series must be a non-empty list.")

    r = inputs.get("r")
    luos = _d(inputs.get("LUOS"))

    pvic = compute_pvic(ic_series, r)
    ec = gamma * luos
    gcu = (alpha * pvic) + (beta * ec)

    return gcu, pvic, ec
