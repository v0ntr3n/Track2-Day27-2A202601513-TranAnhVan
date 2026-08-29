# AI Agent Decision Log

## Decision 1: Robust MAD with Zero-MAD Fallback & Seasonal Segment Context
- **Hypothesis:** Naive Z-score detectors fail during weekend volume drops (causing false positives) and when historical outages inflate variance. Furthermore, standard MAD fails when >50% of history is constant (MAD=0).
- **Prompt / Request to Agent:** Implement a context-aware `auto` anomaly detector combining MAD with mean absolute deviation fallback for zero-MAD, plus weekday/segmentation routing.
- **Agent Proposal:** Enhanced `mad_detector` with Mean AD fallback when MAD=0, and made `detect_anomaly(..., method="auto")` dynamically route to `same_segment_history` when seasonal context is provided, while suppressing alerts for `known_event`.
- **Evidence / Test:** `test_mad_anomaly_detection_with_zero_mad`, `test_auto_detector_uses_segment_context`, and `test_auto_detector_suppresses_known_event` in `tests_public/test_anomaly.py`.
- **Accept / Reject / Revise:** **Accept**.
- **Why:** Successfully distinguishes expected weekend drops from real 75% drop incidents without false alarms.

## Decision 2: SCD Type 2 Active Customer Deduplication in dbt Marts
- **Hypothesis:** Joining `stg_orders` with `stg_customers` where customers have multiple active SCD2 rows causes 1-to-many join fan-out, inflating completed order count and total revenue.
- **Prompt / Request to Agent:** Construct a dbt unit test that exposes the revenue inflation defect and refactor `fct_daily_revenue.sql` to protect against it.
- **Agent Proposal:** Added `unit_tests.yml` with `duplicate_active_customer_does_not_inflate_revenue` test and updated `fct_daily_revenue.sql` using `select distinct customer_id from stg_customers where is_active = true`.
- **Evidence / Test:** `dbt build` runs 2 unit tests and 11 data tests successfully.
- **Accept / Reject / Revise:** **Accept**.
- **Why:** Guarantees idempotency and metric accuracy on financial marts even if upstream dimension tracking has dirty data.

## Decision 3: Google SRE Multi-Window Multi-Burn-Rate Alerting
- **Hypothesis:** Single-window burn rate alerts either page on short transient spikes (causing alert fatigue) or detect sustained outages too slowly.
- **Prompt / Request to Agent:** Implement `evaluate_multiwindow_burn` matching Google SRE standards with dual-window (1h short, 6h long) burn rate thresholds.
- **Agent Proposal:** Designed logic where paging (`page=True, severity="critical"`) requires BOTH short-window burn >= 14.4 AND long-window burn >= 6.0. If short window is high but long window is low, it is categorized as a transient spike and paging is suppressed.
- **Evidence / Test:** `test_sustained_fast_burn_pages_oncall` and `test_transient_spike_does_not_page` in `tests_public/test_slo.py`.
- **Accept / Reject / Revise:** **Accept**.
- **Why:** Aligns with Google SRE best practices and provides actionable, high-signal alerts.

## Decision 4: Transitive BFS Column Lineage Traversal
- **Hypothesis:** Direct-child column mapping fails to compute the blast radius for deep multi-hop transformations (A -> B -> C).
- **Prompt / Request to Agent:** Implement full transitive graph traversal with cycle safety in `get_column_downstream`.
- **Agent Proposal:** Used BFS queue with a `seen` set to traverse arbitrary multi-hop column dependencies without infinite recursion.
- **Evidence / Test:** `test_transitive_column_downstream` in `tests_public/test_lineage.py`.
- **Accept / Reject / Revise:** **Accept**.
- **Why:** Enables full end-to-end impact analysis from raw columns to executive dashboard tiles.

