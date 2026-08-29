# Incident Report: Multi-Vector Data Reliability Outage (Game Day)

## Severity
**P1 (Critical Impact to CEO Dashboard and Customer AI Agent)**

## Summary
The automated data ingestion pipeline continued reporting `SUCCESS` status despite three concurrent silent data corruption failures:
1. **Duplicate Primary Keys & Join Fan-Out:** Duplicate order IDs and duplicate active customer SCD2 records caused inflated revenue metrics in marts and CEO dashboards.
2. **Partial Ingestion Volume Drop:** Upstream ETL dropped 75% of incoming order rows, evading static null/schema checks.
3. **Stale AI Knowledge Base:** Knowledge Base documentation timestamps were lagged by >3 hours, violating the 60-minute freshness SLO and leading to AI Support agents serving obsolete refund policies.

## Detection
- **Contract Signal:** `orders_contract.yaml` unique constraint check failed on `order_id` (severity=critical).
- **Statistical Signal:** Context-aware MAD anomaly detector triggered on `row_count` drop (score=5.53 > 3.5 threshold).
- **Freshness & SLO Signal:** `kb_documents` freshness validator triggered with 180 min delay (threshold=60 min); SLO error budget breached with 4.0x burn rate.
- **First Observed Time:** 2026-08-29 22:16:00 UTC.

## Root Cause
1. **Upstream Ingestion Idempotency Failure:** Upstream retry logic re-appended batch data without upsert/merge logic, producing duplicate `order_id` values.
2. **Customer SCD Type 2 Fan-out:** `fct_daily_revenue.sql` joined against `stg_customers` without active-record deduplication, multiplying revenue when multiple active versions existed per customer.
3. **KB Sync Pipeline Lag:** Upstream document indexing job stalled silently without health checks or publish freshness assertions.

## Evidence
1. `validate_dataframe(orders, contract)` reported `unique` check failure on `order_id` with duplicate rows detected.
2. `detect_metric(150, history, method="auto")` returned `is_anomaly=True` with `method="auto:mad"`.
3. `fct_daily_revenue` dbt unit test `duplicate_active_customer_does_not_inflate_revenue` failed prior to join deduplication fix.
4. `validate_dataframe(kb_df, kb_contract)` caught freshness breach exceeding `max_delay_minutes: 60`.

## Blast Radius

```text
raw_orders (data/incoming/orders.csv)
  └── stg_orders
        └── fct_daily_revenue
              └── ceo_revenue_dashboard (Streamlit & Executive KPIs)

raw_customers (data/incoming/customers.csv)
  └── stg_customers
        └── fct_daily_revenue

kb_documents (data/incoming/kb_documents.jsonl)
  └── active_kb_index
        └── support_ai_agent (Customer Refund & Policy Bot)
```

## Mitigation
1. **Contract Blocker:** Enforced `enforce_action(issues) == 'block'` in ingestion entry points to quarantine batches containing duplicate PKs or type drift.
2. **dbt Join Protection:** Updated `fct_daily_revenue.sql` with `select distinct customer_id from stg_customers where is_active = true` and distinct counts.
3. **Multi-Window SLO Alerting:** Implemented Google SRE multi-window burn rate evaluation to immediately page on-call engineers when sustained fast burn occurs.

## Recovery
- Re-synchronized clean baseline seeds via `make reset`.
- Executed full transformation and data test suite via `make dbt`.
- Re-validated Great Expectations checkpoint suite via `make gx`.

## Verification
- [x] Contract healthy: 0 failed checks on valid incoming orders.
- [x] dbt tests healthy: 18/18 models, seeds, generic tests, and unit tests passing.
- [x] Anomaly returned to expected range: Seasonal MAD baseline calibrated.
- [x] SLO healthy / budget understood: Error budget calculation and multi-window burn rate active.
- [x] Downstream output verified: `fct_daily_revenue` correctly sums completed order revenues.

## Prevention / Action Items
| Action | Owner | Deadline | Why |
|---|---|---|---|
| Enforce strict contract gate in CI/CD before data lake ingestion | Data Platform | 2026-09-05 | Prevent silent schema/type drift |
| Deploy dbt native unit tests for all join-heavy marts | Analytics Eng | 2026-09-08 | Prevent SCD2 fan-out revenue inflation |
| Configure PagerDuty alerting on SRE multi-window burn rate | SRE Team | 2026-09-10 | Eliminate alert fatigue from transient spikes |
| Add KB document freshness heartbeat check in Support RAG service | AI Platform | 2026-09-12 | Ensure AI agents never serve stale policies |

