"""Regression test for the Financial Health module — confirms every
section is computed and structurally well-formed for a real center."""
import asyncio
import os

import pytest
import requests

API_URL = os.environ.get("BACKEND_LOCAL_URL", "http://localhost:8001")


def _token() -> str:
    """Pull a valid super-admin token from MongoDB without going through OTP."""
    from motor.motor_asyncio import AsyncIOMotorClient
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]

    async def _go():
        s = await db.sessions.find_one({}, sort=[("createdAt", -1)])
        cli.close()
        return s.get("token") if s else None

    return asyncio.get_event_loop().run_until_complete(_go())


@pytest.fixture(scope="module")
def token():
    t = _token()
    if not t:
        pytest.skip("no admin session available")
    return t


def test_center_health_full_sections(token):
    r = requests.post(
        f"{API_URL}/api/financial-health/center",
        json={"token": token, "center": "PB-HSR",
              "period": {"type": "month", "month": "2025-04"}},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ["summary", "prime_cost", "food_cost", "labor_cost",
              "contribution_margin", "orders_per_labor_hour",
              "expense_leakage", "alerts", "recommendations",
              "period", "prev_period"]:
        assert k in d, f"missing section: {k}"
    s = d["summary"]
    for k in ["total_sales", "total_expenses", "food_cost", "labor_cost",
              "food_cost_pct", "labor_cost_pct", "prime_cost",
              "prime_cost_pct", "gross_profit", "net_profit",
              "net_profit_pct", "health_score", "status", "status_color",
              "sales_delta_pct"]:
        assert k in s, f"missing summary.{k}"
    assert 0 <= s["health_score"] <= 100
    assert s["status_color"] in {"green", "yellow", "red"}


def test_period_kinds_all_parseable(token):
    bodies = [
        {"type": "month", "month": "2025-04"},
        {"type": "quarter", "quarter": "2025-Q2"},
        {"type": "fy", "fy": "FY26"},
        {"type": "custom", "from_date": "2025-04-01", "to_date": "2025-04-30"},
    ]
    for body in bodies:
        r = requests.post(
            f"{API_URL}/api/financial-health/center",
            json={"token": token, "center": "PB-HSR", "period": body},
            timeout=20,
        )
        assert r.status_code == 200, f"{body} → {r.status_code}: {r.text[:300]}"
        d = r.json()
        assert "summary" in d
        assert d["period"]["from"] <= d["period"]["to"]


def test_australia_food_cost_target_is_30(token):
    r = requests.post(
        f"{API_URL}/api/financial-health/center",
        json={"token": token, "center": "PB-PERTH",
              "period": {"type": "month", "month": "2025-04"}},
        timeout=20,
    )
    assert r.status_code == 200
    d = r.json()
    assert d["country"] == "Australia"
    assert d["food_cost"]["target_pct"] == 30.0


def test_portfolio_ranks_centers(token):
    r = requests.post(
        f"{API_URL}/api/financial-health/portfolio",
        json={"token": token, "period": {"type": "month", "month": "2025-04"}},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert "rows" in d and isinstance(d["rows"], list)
    assert "rankings" in d
    for k in ["best_performing", "worst_performing", "highest_food_cost",
              "highest_labor_cost", "highest_profit", "lowest_profit"]:
        assert k in d["rankings"]
    # PB-MGT (HQ) excluded
    centers = {r["center"] for r in d["rows"]}
    assert "PB-MGT" not in centers
