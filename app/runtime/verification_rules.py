from __future__ import annotations

from typing import Any, Dict, List

from app.tools.contracts import VerificationReport


def _present_str(x: Any) -> bool:
    return isinstance(x, str) and x.strip() != ""


def _present_num(x: Any) -> bool:
    return isinstance(x, (int, float))


def _get_fields(extracted: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(extracted, dict):
        return {}
    fields = extracted.get("fields")
    return fields if isinstance(fields, dict) else {}


def verify(domain: str, schema_id: str, source_text: str, extracted: Dict[str, Any]) -> VerificationReport:
    """
    Deterministic verification (no LLM).
    Produces PASS/WARN/FAIL based on domain-specific checks.
    """
    fields = _get_fields(extracted)

    checks: List[Dict[str, Any]] = []
    hard_fail = False
    soft_fail = False

    def add_check(name: str, passed: bool, severity: str, details: Dict[str, Any] | None = None) -> None:
        nonlocal hard_fail, soft_fail
        checks.append({"name": name, "pass": passed, "severity": severity, "details": details or {}})
        if not passed:
            if severity == "HARD":
                hard_fail = True
            else:
                soft_fail = True

    # Universal checks
    add_check(
        "has_fields",
        passed=bool(fields),
        severity="HARD",
        details={"keys": list(fields.keys())[:20]},
    )

    # Domain-specific checks (MVP)
    if domain == "finance":
        # Expect invoice-like fields if we route to finance.* (later we can tighten routing)
        add_check("vendor_present", _present_str(fields.get("vendor")), "SOFT")
        add_check("total_present", _present_num(fields.get("total")) or _present_str(fields.get("total")), "SOFT")
        add_check("currency_present", _present_str(fields.get("currency")), "SOFT")

    elif domain == "legal":
        add_check("parties_present", bool(fields.get("parties")), "SOFT")
        add_check("effective_date_present", _present_str(fields.get("effective_date")), "SOFT")
        add_check("governing_law_present", _present_str(fields.get("governing_law")), "SOFT")

    else:
        # general: keep minimal
        add_check("non_empty_example_or_summary", bool(fields), "SOFT")

    if hard_fail:
        verdict = "FAIL"
    elif soft_fail:
        verdict = "WARN"
    else:
        verdict = "PASS"

    return VerificationReport(verdict=verdict, checks=checks)
