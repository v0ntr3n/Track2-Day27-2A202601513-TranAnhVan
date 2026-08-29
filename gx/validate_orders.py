#!/usr/bin/env python3
"""Great Expectations Core 1.21 pipeline.

Implements:
- Ephemeral GX Data Context & Pandas Data Source
- ExpectationSuite with critical & warning expectations matching orders_contract.yaml
- ValidationDefinition binding data asset & suite
- Checkpoint execution & action handling
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    import great_expectations as gx
except ImportError as exc:
    raise SystemExit("great_expectations is not installed. Run: pip install -r requirements.txt") from exc


def build_and_run_gx_checkpoint(df: pd.DataFrame) -> dict[str, Any]:
    context = gx.get_context(mode="ephemeral")

    # 1. Connect Data Source & Asset
    data_source = context.data_sources.add_pandas("orders_pandas_source")
    asset = data_source.add_dataframe_asset(name="orders_df_asset")
    batch_definition = asset.add_batch_definition_whole_dataframe("orders_batch_def")

    # 2. Build Expectation Suite
    suite = gx.ExpectationSuite(name="orders_contracts_suite")
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="order_id", severity="critical"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(column="order_id", severity="critical"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="customer_id", severity="critical"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(column="amount", min_value=0, severity="critical"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeInSet(column="currency", value_set=["USD", "VND"], severity="critical"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeInSet(column="status", value_set=["pending", "completed", "refunded", "cancelled"], severity="warning"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="created_at", severity="critical"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="updated_at", severity="critical"))
    context.suites.add(suite)

    # 3. Create Validation Definition
    validation_definition = gx.ValidationDefinition(
        data=batch_definition,
        suite=suite,
        name="orders_validation_def",
    )
    context.validation_definitions.add(validation_definition)

    # 4. Create Checkpoint
    checkpoint = gx.Checkpoint(
        name="orders_checkpoint",
        validation_definitions=[validation_definition],
    )
    context.checkpoints.add(checkpoint)

    # 5. Execute Checkpoint
    checkpoint_result = checkpoint.run(batch_parameters={"dataframe": df})
    success = bool(checkpoint_result.success)

    return {
        "success": success,
        "checkpoint_name": checkpoint.name,
        "suite_name": suite.name,
        "result": checkpoint_result,
    }


def main() -> None:
    orders_path = ROOT / "data" / "incoming" / "orders.csv"
    if not orders_path.exists():
        print(f"Data file not found at {orders_path}")
        return
    df = pd.read_csv(orders_path)
    res = build_and_run_gx_checkpoint(df)
    print(f"Great Expectations Checkpoint '{res['checkpoint_name']}' with Suite '{res['suite_name']}':")
    print(f"Overall Status: {'PASS' if res['success'] else 'FAIL'}")


if __name__ == "__main__":
    main()

