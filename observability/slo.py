from __future__ import annotations

from typing import Any


def calculate_slo(target: float, bad_events: int, total_events: int) -> dict[str, Any]:
    if not 0 < target < 1:
        raise ValueError("target must be between 0 and 1 (exclusive)")
    if bad_events < 0 or total_events < 0 or bad_events > total_events:
        raise ValueError("invalid event counts")
    allowed_bad_rate = 1.0 - target
    if total_events == 0:
        return {
            "target": target,
            "actual_bad_rate": 0.0,
            "allowed_bad_rate": allowed_bad_rate,
            "burn_rate": 0.0,
            "remaining_error_budget_fraction": 1.0,
            "breached": False,
        }
    actual_bad_rate = bad_events / total_events
    burn_rate = actual_bad_rate / allowed_bad_rate
    consumed_fraction = min(1.0, actual_bad_rate / allowed_bad_rate)
    return {
        "target": target,
        "actual_bad_rate": actual_bad_rate,
        "allowed_bad_rate": allowed_bad_rate,
        "burn_rate": burn_rate,
        "remaining_error_budget_fraction": max(0.0, 1.0 - consumed_fraction),
        "breached": bool(actual_bad_rate > allowed_bad_rate),
    }


def evaluate_multiwindow_burn(
    *,
    short_window_burn: float,
    long_window_burn: float,
    critical_threshold: float = 14.4,
    warning_threshold: float = 6.0,
    policy: str = "sre_multiwindow",
) -> dict[str, Any]:
    """Google SRE Multi-Window Multi-Burn-Rate alerting policy.

    Distinguishes sustained fast burn (which pages on-call engineers) from
    transient short spikes (which do not page, avoiding alert fatigue).

    Rules:
    - Sustained Fast Burn: BOTH short and long windows exceed critical threshold -> page=True, severity='critical'
    - Sustained Moderate Burn: BOTH short and long windows exceed warning threshold -> page=False, severity='warning'
    - Transient Spike: short window high, but long window low -> page=False, severity='warning' (no page)
    - Normal: burn rate within allowed limits -> page=False, severity='info'
    """
    short_b = float(short_window_burn)
    long_b = float(long_window_burn)

    if short_b >= critical_threshold and long_b >= warning_threshold:
        return {
            "page": True,
            "severity": "critical",
            "reason": f"sustained_fast_burn(short={short_b:.1f}>={critical_threshold}, long={long_b:.1f}>={warning_threshold})",
            "short_window_burn": short_b,
            "long_window_burn": long_b,
            "action": "page_oncall",
        }
    elif short_b >= warning_threshold and long_b >= warning_threshold:
        return {
            "page": False,
            "severity": "warning",
            "reason": f"sustained_moderate_burn(short={short_b:.1f}>={warning_threshold}, long={long_b:.1f}>={warning_threshold})",
            "short_window_burn": short_b,
            "long_window_burn": long_b,
            "action": "create_ticket",
        }
    elif short_b >= warning_threshold and long_b < warning_threshold:
        return {
            "page": False,
            "severity": "warning",
            "reason": f"transient_spike(short={short_b:.1f}>={warning_threshold}, long={long_b:.1f}<{warning_threshold}); suppressed_paging",
            "short_window_burn": short_b,
            "long_window_burn": long_b,
            "action": "suppress_alert",
        }
    elif long_b >= warning_threshold:
        return {
            "page": False,
            "severity": "warning",
            "reason": f"slow_burn_detected(long={long_b:.1f}>={warning_threshold})",
            "short_window_burn": short_b,
            "long_window_burn": long_b,
            "action": "investigate_backlog",
        }
    else:
        return {
            "page": False,
            "severity": "info",
            "reason": f"normal_burn_rate(short={short_b:.1f}, long={long_b:.1f})",
            "short_window_burn": short_b,
            "long_window_burn": long_b,
            "action": "none",
        }

