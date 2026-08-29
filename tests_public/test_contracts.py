from pathlib import Path
import pandas as pd

from student_api import validate_orders

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "orders_contract.yaml"


def healthy_df():
    return pd.DataFrame([
        {
            "order_id": 1,
            "customer_id": "C1",
            "amount": 10.0,
            "currency": "USD",
            "status": "completed",
            "created_at": "2026-08-28T10:00:00Z",
            "updated_at": "2026-08-28T10:05:00Z",
        },
        {
            "order_id": 2,
            "customer_id": "C2",
            "amount": 20.0,
            "currency": "USD",
            "status": "pending",
            "created_at": "2026-08-28T10:01:00Z",
            "updated_at": "2026-08-28T10:06:00Z",
        },
    ])


def failed(issues):
    return [i for i in issues if not i["passed"]]


def test_healthy_contract_passes_starter_checks():
    assert not failed(validate_orders(healthy_df(), CONTRACT))


def test_duplicate_order_id_is_detected():
    df = healthy_df()
    df.loc[1, "order_id"] = 1
    issues = failed(validate_orders(df, CONTRACT))
    assert any(i["check"] == "unique" and i["column"] == "order_id" for i in issues)


def test_invalid_currency_is_detected():
    df = healthy_df()
    df.loc[0, "currency"] = "BTC"
    issues = failed(validate_orders(df, CONTRACT))
    assert any(i["check"] == "accepted_values" and i["column"] == "currency" for i in issues)


def test_type_drift_is_detected():
    df = healthy_df()
    # Insert invalid string into integer column (convert to object first to prevent pandas dtype error)
    df["order_id"] = df["order_id"].astype(object)
    df.loc[0, "order_id"] = "not_an_integer"
    issues = failed(validate_orders(df, CONTRACT))
    assert any(i["check"] == "type" and i["column"] == "order_id" for i in issues)



def test_freshness_delay_is_detected():
    df = healthy_df()
    # Reference time is 2 hours later than updated_at (contract max delay is 30 mins)
    issues = failed(validate_orders(df, CONTRACT, reference_time="2026-08-28T12:05:00Z"))
    assert any(i["check"] == "freshness" and i["column"] == "updated_at" for i in issues)

