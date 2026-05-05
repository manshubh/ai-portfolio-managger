"""my-philosophy — deterministic §9.3 pass/fail + §9.2 PF/15 graded ladder.

Owns only the threshold pass/fail table and the PF/15 sub-score. F/35, BS/20,
V/20, N/10 stay Phase 4 LLM judgments (investigation §2, SPEC §10.5).

No LLM, no network, no wall-clock — byte-equal stdout on byte-equal input.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, NoReturn

import yaml

EXIT_OK = 0
EXIT_BAD_INPUT = 1
EXIT_INTERNAL = 2

# (metric_name, fund_key, yaml_threshold_key, op)
# op ∈ {">=", "<=", "boolean"}.
NON_FINANCIAL_CHECKS: list[tuple[str, str, str, str]] = [
    ("roe",          "roe_pct",             "roe_min",             ">="),
    ("roce",         "roce_pct",            "roce_min",            ">="),
    ("de",           "de_ratio",            "de_max",              "<="),
    ("promoter",     "promoter_pct",        "promoter_min",        ">="),
    ("pledge",       "pledge_pct",          "pledge_max",          "<="),
    ("rev_cagr_3y",  "revenue_cagr_3y_pct", "revenue_cagr_3y_min", ">="),
    ("pat_cagr_3y",  "pat_cagr_3y_pct",     "profit_cagr_3y_min",  ">="),
    ("fcf_positive", "fcf_positive",        "fcf_positive",        "boolean"),
    ("mcap_cr",      "mcap_cr",             "mcap_min_cr",         ">="),
]

BANKING_NBFC_CHECKS: list[tuple[str, str, str, str]] = [
    ("roa",           "roa_pct",         "roa_min",           ">="),
    ("roe",           "roe_pct",         "roe_min",           ">="),
    ("nnpa",          "nnpa_pct",        "nnpa_max",          "<="),
    ("car",           "car_pct",         "car_min",           ">="),
    ("casa",          "casa_pct",        "casa_min",          ">="),
    ("nim",           "nim_pct",         "nim_min",           ">="),
    ("profit_growth", "pat_cagr_3y_pct", "profit_growth_min", ">="),
    ("promoter",      "promoter_pct",    "promoter_min",      ">="),
    ("pledge",        "pledge_pct",      "pledge_max",        "<="),
    ("mcap_cr",       "mcap_cr",         "mcap_min_cr",       ">="),
]

CHECKS_BY_SCHEME = {
    "non_financial": NON_FINANCIAL_CHECKS,
    "banking_nbfc":  BANKING_NBFC_CHECKS,
}


def _die_bad_input(kind: str, message: str) -> NoReturn:
    print(json.dumps({"error": kind, "message": message}), file=sys.stderr)
    sys.exit(EXIT_BAD_INPUT)


def load_philosophy(path: str) -> dict[str, Any]:
    """Parse the YAML front-matter from a philosophy.md file (§7.6)."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        _die_bad_input("philosophy_read_error", f"{path}: {exc}")

    if not text.startswith("---\n"):
        _die_bad_input(
            "philosophy_frontmatter_missing",
            f"{path}: expected YAML front-matter starting with '---' on line 1",
        )
    end = text.find("\n---", 4)
    if end == -1:
        _die_bad_input(
            "philosophy_frontmatter_unterminated",
            f"{path}: expected closing '---' delimiter",
        )
    try:
        data = yaml.safe_load(text[4:end])
    except yaml.YAMLError as exc:
        _die_bad_input("philosophy_yaml_error", f"{path}: {exc}")
    if not isinstance(data, dict):
        _die_bad_input(
            "philosophy_frontmatter_shape",
            f"{path}: YAML front-matter must be a mapping",
        )
    return data


def load_metrics(path: str) -> dict[str, Any]:
    try:
        with Path(path).open(encoding="utf-8") as fp:
            data = json.load(fp)
    except OSError as exc:
        _die_bad_input("metrics_read_error", f"{path}: {exc}")
    except json.JSONDecodeError as exc:
        _die_bad_input("metrics_json_error", f"{path}: {exc}")
    if not isinstance(data, dict):
        _die_bad_input("metrics_shape", f"{path}: expected JSON object at root")
    return data


def _compare(value: Any, threshold: Any, op: str) -> bool:
    if op == ">=":
        return value >= threshold
    if op == "<=":
        return value <= threshold
    if op == "boolean":
        # fcf_positive-style: required state (True/False) must match observed.
        return bool(value) == bool(threshold)
    raise ValueError(f"unknown op: {op!r}")


def _build_check_row(
    metric: str,
    fund_key: str,
    yaml_key: str,
    op: str,
    fund: dict[str, Any],
    base_thresholds: dict[str, Any],
    exception_overrides: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    """Return (row_dict, effective_pass)."""
    if fund_key not in fund:
        _die_bad_input(
            "metrics_missing_field",
            f"fund.{fund_key} is required for metric {metric!r}",
        )
    if yaml_key not in base_thresholds:
        _die_bad_input(
            "philosophy_missing_threshold",
            f"threshold {yaml_key!r} missing from philosophy YAML",
        )

    value = fund[fund_key]
    base_threshold = base_thresholds[yaml_key]
    base_pass = _compare(value, base_threshold, op)

    row: dict[str, Any] = {"metric": metric, "value": value}
    if op == "boolean":
        row["pass"] = base_pass
    else:
        row["threshold"] = base_threshold
        row["op"] = op
        row["pass"] = base_pass

    effective_pass = base_pass

    # `exempt: true` (stock_exchanges) short-circuits the promoter rule entirely:
    # the entity is structurally promoter-less, so the threshold doesn't apply.
    if (exception_overrides.get("exempt") is True
            and yaml_key == "promoter_min"):
        row["exception"] = exception_overrides["__name__"]
        row["exempt"] = True
        if not base_pass:
            row["pass_with_exception"] = True
        effective_pass = True
    elif yaml_key in exception_overrides:
        eff_threshold = exception_overrides[yaml_key]
        eff_pass = _compare(value, eff_threshold, op)
        row["exception"] = exception_overrides["__name__"]
        row["effective_threshold"] = eff_threshold
        if eff_pass != base_pass:
            row["pass_with_exception"] = eff_pass
        effective_pass = eff_pass

    return row, effective_pass


def _resolve_sector_exception(
    philosophy: dict[str, Any],
    exception_name: str | None,
) -> dict[str, Any]:
    """Return exception overrides map (includes __name__, possibly 'exempt').

    Keys other than `__name__`, `exempt`, and `applies_to` are threshold overrides
    matching YAML threshold keys (e.g. `promoter_min`).
    """
    if exception_name is None:
        return {}
    table = philosophy.get("sector_exceptions") or {}
    if exception_name not in table:
        _die_bad_input(
            "unknown_sector_exception",
            f"sector_exceptions.{exception_name} not defined in philosophy YAML",
        )
    entry = dict(table[exception_name] or {})
    entry["__name__"] = exception_name
    return entry


def check_thresholds(
    philosophy: dict[str, Any],
    metrics: dict[str, Any],
    scheme: str,
    sector_exception: str | None,
) -> dict[str, Any]:
    """Produce the §9.3 pass/fail payload."""
    if scheme not in CHECKS_BY_SCHEME:
        _die_bad_input("unknown_scheme", f"unknown scheme: {scheme!r}")
    if "ticker" not in metrics:
        _die_bad_input("metrics_missing_field", "metrics.ticker is required")
    fund = metrics.get("fund")
    if not isinstance(fund, dict):
        _die_bad_input("metrics_missing_field", "metrics.fund must be an object")

    base_thresholds = (philosophy.get("thresholds") or {}).get(scheme)
    if not isinstance(base_thresholds, dict):
        _die_bad_input(
            "philosophy_missing_scheme",
            f"philosophy.thresholds.{scheme} must be a mapping",
        )

    exception_overrides = _resolve_sector_exception(philosophy, sector_exception)
    exempt = bool(exception_overrides.get("exempt"))

    checks: list[dict[str, Any]] = []
    pass_count = 0
    fail_count = 0

    for metric, fund_key, yaml_key, op in CHECKS_BY_SCHEME[scheme]:
        row, effective_pass = _build_check_row(
            metric, fund_key, yaml_key, op, fund, base_thresholds, exception_overrides,
        )
        checks.append(row)
        if effective_pass:
            pass_count += 1
        else:
            fail_count += 1

    dealbreakers = _detect_dealbreakers(fund, metrics, exempt)

    if dealbreakers:
        pf = 0
    elif fail_count == 0:
        pf = 15
    elif fail_count <= 2:
        pf = 8
    else:
        pf = 0

    return {
        "ticker":                 metrics["ticker"],
        "market":                 philosophy.get("market"),
        "scheme":                 scheme,
        "checks":                 checks,
        "pass_count":             pass_count,
        "fail_count":             fail_count,
        "dealbreakers_triggered": dealbreakers,
        "philosophy_fit_graded":  pf,
    }


def _detect_dealbreakers(
    fund: dict[str, Any],
    metrics: dict[str, Any],
    exempt: bool,
) -> list[str]:
    triggered: list[str] = []
    if fund.get("promoter_pct") == 0 and not exempt:
        triggered.append("zero_promoter")
    if metrics.get("governance_red_flag", False):
        triggered.append("governance_red_flag")
    if metrics.get("user_thesis_exit", False):
        triggered.append("user_thesis_exit")
    return triggered


def persona_my_philosophy(
    philosophy: dict[str, Any],
    metrics: dict[str, Any],
    scheme: str,
    sector_exception: str | None,
) -> dict[str, Any]:
    """my-philosophy persona wrapper around the PF/15 sub-score."""
    result = check_thresholds(philosophy, metrics, scheme, sector_exception)
    pf = result["philosophy_fit_graded"]

    if pf == 15:
        signal, confidence = "bullish", 1.0
    elif pf == 8:
        signal, confidence = "neutral", 0.5
    else:
        signal, confidence = "bearish", 1.0

    detail = _format_persona_detail(result)

    return {
        "ticker":         metrics["ticker"],
        "persona":        "my-philosophy",
        "sub_scores":     {"philosophy_fit": pf},
        "weighted_score": pf,
        "max_score":      15,
        "signal":         signal,
        "confidence":     confidence,
        "details":        {"philosophy_fit": detail},
    }


def _format_persona_detail(result: dict[str, Any]) -> str:
    fails = [c["metric"] for c in result["checks"]
             if (c.get("pass_with_exception") if "pass_with_exception" in c else c["pass"]) is False]
    db = result["dealbreakers_triggered"]
    parts = []
    if fails:
        parts.append(f"{len(fails)} non-dealbreaker fail(s) ({', '.join(fails)})")
    else:
        parts.append("0 fails")
    parts.append(f"{len(db)} dealbreaker(s) triggered" + (f" ({', '.join(db)})" if db else ""))
    return "; ".join(parts) + "."
