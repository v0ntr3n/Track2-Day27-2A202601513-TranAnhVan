"""Distribution drift detection module.

Combines:
- Kolmogorov-Smirnov (KS) two-sample test for non-parametric distribution shape comparison
- Robust moment shifts (mean ratio, variance shift, quantile drift)
"""
from __future__ import annotations

from typing import Any, Iterable

import numpy as np

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


def detect_distribution_shift(
    current_values: Iterable[float],
    baseline_values: Iterable[float],
    *,
    ratio_threshold: float = 3.0,
    ks_alpha: float = 0.01,
) -> dict[str, Any]:
    """Detects distribution drift between baseline and current values."""
    cur = np.asarray(list(current_values), dtype=float)
    base = np.asarray(list(baseline_values), dtype=float)
    cur = cur[np.isfinite(cur)]
    base = base[np.isfinite(base)]

    if cur.size == 0 or base.size == 0:
        return {"is_anomaly": False, "score": 0.0, "method": "distribution_shift", "reason": "empty_input"}

    cur_mean = float(np.mean(cur))
    base_mean = float(np.mean(base))

    # 1. Mean Ratio Score
    if base_mean == 0:
        mean_score = float("inf") if cur_mean != 0 else 1.0
    else:
        mean_score = max(abs(cur_mean / base_mean), abs(base_mean / cur_mean)) if cur_mean != 0 else float("inf")

    # 2. Kolmogorov-Smirnov (KS) Test for distribution shape
    ks_stat = 0.0
    p_val = 1.0
    is_ks_shift = False
    if SCIPY_AVAILABLE and cur.size >= 4 and base.size >= 4:
        ks_res = stats.ks_2samp(cur, base)
        ks_stat = float(ks_res.statistic)
        p_val = float(ks_res.pvalue)
        is_ks_shift = bool(p_val < ks_alpha)

    # 3. Variance / Spread Shift
    cur_std = float(np.std(cur))
    base_std = float(np.std(base))
    is_variance_shift = False
    if cur_std > 0 and base_std > 0:
        variance_ratio = max(cur_std / base_std, base_std / cur_std)
        if variance_ratio > 5.0 and cur.size >= 5 and base.size >= 5:
            is_variance_shift = True

    is_anomaly = bool(mean_score >= ratio_threshold or is_ks_shift or is_variance_shift)
    score = float(mean_score if np.isfinite(mean_score) else (100.0 if is_anomaly else 0.0))

    reasons = [f"baseline_mean={base_mean:.3f}, current_mean={cur_mean:.3f}, mean_ratio={mean_score:.2f}"]
    if SCIPY_AVAILABLE and cur.size >= 4 and base.size >= 4:
        reasons.append(f"ks_stat={ks_stat:.3f}, p_value={p_val:.4f}")
    if is_variance_shift:
        reasons.append(f"variance_shift_detected(cur_std={cur_std:.2f}, base_std={base_std:.2f})")

    return {
        "is_anomaly": is_anomaly,
        "score": score,
        "method": "ks_and_moments" if (SCIPY_AVAILABLE and cur.size >= 4) else "mean_ratio",
        "reason": "; ".join(reasons),
        "ks_statistic": ks_stat,
        "p_value": p_val,
    }

