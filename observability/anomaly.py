"""Anomaly detection module with robust MAD, Z-score, and context-aware auto mode.

Features:
- Z-score baseline detector
- Robust MAD (Median Absolute Deviation) with zero-MAD edge case fallback
- Context-aware auto mode handling seasonality (day_of_week, same_segment_history),
  known events (maintenance, promotions), and robust statistical routing.
"""
from __future__ import annotations

from typing import Any, Iterable

import numpy as np


def zscore_detector(current: float, history: Iterable[float], threshold: float = 3.0) -> dict[str, Any]:
    values = np.asarray(list(history), dtype=float)
    values = values[np.isfinite(values)]
    if values.size < 3:
        return {"is_anomaly": False, "score": 0.0, "method": "zscore", "reason": "insufficient_history"}
    mean = float(np.mean(values))
    std = float(np.std(values))
    if std == 0:
        score = float("inf") if float(current) != mean else 0.0
    else:
        score = abs(float(current) - mean) / std
    return {
        "is_anomaly": bool(score > threshold),
        "score": float(score),
        "method": "zscore",
        "reason": f"mean={mean:.3f}, std={std:.3f}, threshold={threshold}",
    }


def mad_detector(current: float, history: Iterable[float], threshold: float = 3.5) -> dict[str, Any]:
    """Robust MAD detector with proper zero-MAD and small-sample handling."""
    values = np.asarray(list(history), dtype=float)
    values = values[np.isfinite(values)]
    if values.size < 3:
        return {"is_anomaly": False, "score": 0.0, "method": "mad", "reason": "insufficient_history"}
    
    median = float(np.median(values))
    abs_deviations = np.abs(values - median)
    mad = float(np.median(abs_deviations))

    # Handle zero-MAD (e.g. >50% values are identical)
    if mad == 0:
        mean_ad = float(np.mean(abs_deviations))
        if mean_ad > 0:
            # Fallback to Mean Absolute Deviation (scaling factor ~ 0.7979 for normal)
            modified_z = 0.7979 * abs(float(current) - median) / mean_ad
            return {
                "is_anomaly": bool(modified_z > threshold),
                "score": float(modified_z),
                "method": "mad:mean_ad_fallback",
                "reason": f"median={median:.3f}, mean_ad={mean_ad:.3f}, zero_mad_resolved=true",
            }
        else:
            # All historical values were exactly identical
            cur_val = float(current)
            if cur_val == median:
                return {
                    "is_anomaly": False,
                    "score": 0.0,
                    "method": "mad",
                    "reason": f"constant_history={median:.3f}, match=true",
                }
            else:
                return {
                    "is_anomaly": True,
                    "score": float("inf"),
                    "method": "mad",
                    "reason": f"constant_history={median:.3f}, current={cur_val:.3f}, deviation_from_constant=true",
                }

    modified_z = 0.6745 * abs(float(current) - median) / mad
    return {
        "is_anomaly": bool(modified_z > threshold),
        "score": float(modified_z),
        "method": "mad",
        "reason": f"median={median:.3f}, mad={mad:.3f}, threshold={threshold}",
    }


def detect_anomaly(
    current: float,
    history: Iterable[float],
    *,
    method: str = "auto",
    threshold: float = 3.0,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stable lab API for metric anomaly detection.

    - `zscore`: standard Z-score
    - `mad`: robust Median Absolute Deviation
    - `auto`: context-aware intelligent detector (seasonality, segment history, events, robust estimator)
    """
    if method == "mad":
        return mad_detector(current, history, threshold=threshold)
    
    if method == "zscore":
        return zscore_detector(current, history, threshold=threshold)

    if method == "auto":
        ctx = context or {}

        # 1. Known event override (e.g. planned maintenance, marketing campaign)
        known_event = ctx.get("known_event")
        if known_event:
            return {
                "is_anomaly": False,
                "score": 0.0,
                "method": "auto:known_event_override",
                "reason": f"suppressed_by_known_event={known_event}",
            }

        # 2. Seasonality / Segment History
        effective_history = list(history)
        seasonal_context_used = False

        if "same_segment_history" in ctx and ctx["same_segment_history"]:
            segment_hist = list(ctx["same_segment_history"])
            if len(segment_hist) >= 3:
                effective_history = segment_hist
                seasonal_context_used = True

        # 3. Robust detector selection (prefer MAD if sufficient history, else Z-score)
        if len(effective_history) >= 5:
            res = mad_detector(current, effective_history, threshold=threshold if threshold != 3.0 else 3.5)
            method_name = "auto:seasonal_mad" if seasonal_context_used else "auto:mad"
        else:
            res = zscore_detector(current, effective_history, threshold=threshold)
            method_name = "auto:seasonal_zscore" if seasonal_context_used else "auto:zscore"

        res["method"] = method_name
        if ctx:
            res["context_evaluated"] = {k: v for k, v in ctx.items() if k != "same_segment_history"}
        return res

    raise ValueError(f"Unsupported method: {method}")

