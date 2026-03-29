# =======================================
# Commission Tracking Routes
# Platform, Payment Mode & GST Commissions
# =======================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/commissions", tags=["Commission Tracking"])

db = None
verify_token = None
verify_token_async_func = None

def set_db(database):
    global db
    db = database

def set_verify_token(func):
    global verify_token
    verify_token = func

def set_verify_token_async(func):
    global verify_token_async_func
    verify_token_async_func = func

async def get_session(token: str):
    if verify_token_async_func:
        session = await verify_token_async_func(token)
        if session:
            return session
    return verify_token(token)

def check_admin(session):
    return session and (session.get("is_super_admin") or session.get("is_admin"))

# =======================================
# PYDANTIC MODELS
# =======================================

class PlatformCommission(BaseModel):
    platform: str          # SWIGGY, ZOMATO, DIRECT, MAGICPIN etc.
    commission_pct: float  # e.g. 25.0 for 25%
    gst_on_commission_pct: float = 18.0  # GST on commission (default 18%)
    is_active: bool = True

class PaymentModeCommission(BaseModel):
    payment_mode: str      # CARD, UPI, CASH, BANK TRANSFER
    commission_pct: float  # e.g. 2.0 for 2%
    is_active: bool = True

class CommissionConfigSave(BaseModel):
    token: str
    center: str
    platforms: List[PlatformCommission]
    payment_modes: List[PaymentModeCommission]

class CommissionConfigGet(BaseModel):
    token: str
    center: str

class CommissionDashboardReq(BaseModel):
    token: str
    center: Optional[str] = None
    month: Optional[str] = None  # YYYY-MM
    start_date: Optional[str] = None
    end_date: Optional[str] = None

# =======================================
# CONFIG ENDPOINTS
# =======================================

@router.post("/config/save")
async def save_commission_config(req: CommissionConfigSave):
    """Save commission configuration for a center"""
    session = await get_session(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    if not check_admin(session):
        raise HTTPException(403, "Admin access required")

    center = req.center.upper().strip()
    now = datetime.now(timezone.utc).isoformat()

    doc = {
        "center": center,
        "platforms": [p.dict() for p in req.platforms],
        "payment_modes": [pm.dict() for pm in req.payment_modes],
        "updated_by": session.get("managerName", "Admin"),
        "updated_at": now,
    }

    await db.commission_config.update_one(
        {"center": center},
        {"$set": doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )

    logger.info(f"Commission config saved for {center} by {session.get('managerName')}")
    return {"success": True, "message": f"Commission config saved for {center}"}


@router.post("/config/get")
async def get_commission_config(req: CommissionConfigGet):
    """Get commission configuration for a center"""
    session = await get_session(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")

    center = req.center.upper().strip()
    config = await db.commission_config.find_one({"center": center}, {"_id": 0})

    if not config:
        # Return default template
        config = {
            "center": center,
            "platforms": [
                {"platform": "SWIGGY", "commission_pct": 25.0, "gst_on_commission_pct": 18.0, "is_active": True},
                {"platform": "ZOMATO", "commission_pct": 22.0, "gst_on_commission_pct": 18.0, "is_active": True},
                {"platform": "MAGICPIN", "commission_pct": 15.0, "gst_on_commission_pct": 18.0, "is_active": True},
                {"platform": "DIRECT", "commission_pct": 0.0, "gst_on_commission_pct": 0.0, "is_active": True},
            ],
            "payment_modes": [
                {"payment_mode": "CARD", "commission_pct": 2.0, "is_active": True},
                {"payment_mode": "UPI", "commission_pct": 0.0, "is_active": True},
                {"payment_mode": "CASH", "commission_pct": 0.0, "is_active": True},
                {"payment_mode": "BANK TRANSFER", "commission_pct": 0.0, "is_active": True},
            ],
        }

    return {"success": True, "config": config}


@router.get("/config/all")
async def get_all_commission_configs():
    """Get all center commission configs (public for MIS integration)"""
    configs = await db.commission_config.find({}, {"_id": 0}).to_list(100)
    return {"configs": configs}


# =======================================
# CALCULATION ENGINE
# =======================================

async def calculate_commissions_for_period(center: str, start_date: str, end_date: str):
    """Core calculation: compute commissions from daily_sales data and config.
    
    daily_sales schema per record:
      - total_sale: total daily sale
      - swiggy: Swiggy platform amount
      - zomato: Zomato platform amount  
      - card_idfc: Card payment amount
      - bharat_pay: UPI/Bharat Pay amount
      - online_other: Other online payments
      - total_cash_sale: Cash sale amount
      - total_online_sale: Total online
    """
    config = await db.commission_config.find_one({"center": center}, {"_id": 0})

    # Build lookup maps from config (or use defaults)
    platform_rates = {}
    payment_rates = {}
    if config:
        for p in config.get("platforms", []):
            if p.get("is_active", True):
                platform_rates[p["platform"].upper()] = {
                    "commission_pct": p["commission_pct"],
                    "gst_pct": p.get("gst_on_commission_pct", 18.0),
                }
        for pm in config.get("payment_modes", []):
            if pm.get("is_active", True):
                payment_rates[pm["payment_mode"].upper()] = pm["commission_pct"]
    else:
        # Default rates when no config saved
        platform_rates = {
            "SWIGGY": {"commission_pct": 25.0, "gst_pct": 18.0},
            "ZOMATO": {"commission_pct": 22.0, "gst_pct": 18.0},
        }
        payment_rates = {"CARD": 2.0}

    # Fetch daily_sales for the period
    sales = await db.daily_sales.find(
        {"center": center, "date": {"$gte": start_date, "$lte": end_date}},
        {"_id": 0},
    ).to_list(5000)

    total_sales = 0.0
    total_platform_commission = 0.0
    total_gst_on_commission = 0.0
    total_payment_commission = 0.0
    platform_breakdown = {}
    payment_breakdown = {}
    daily_data = {}

    # Map daily_sales fields to platform/payment names
    PLATFORM_FIELD_MAP = {
        "swiggy": "SWIGGY",
        "zomato": "ZOMATO",
    }
    PAYMENT_FIELD_MAP = {
        "card_idfc": "CARD",
        "bharat_pay": "UPI",
        "total_cash_sale": "CASH",
        "online_other": "OTHER ONLINE",
    }

    for sale in sales:
        date = sale.get("date", "")
        day_total = float(sale.get("total_sale", 0) or 0)
        total_sales += day_total

        day_platform_comm = 0.0
        day_gst = 0.0
        day_payment_comm = 0.0

        # Platform commissions (Swiggy, Zomato amounts)
        for field, platform_name in PLATFORM_FIELD_MAP.items():
            amount = float(sale.get(field, 0) or 0)
            if amount > 0:
                rate_info = platform_rates.get(platform_name, {"commission_pct": 0, "gst_pct": 0})
                p_comm = amount * rate_info["commission_pct"] / 100
                p_gst = p_comm * rate_info["gst_pct"] / 100
                total_platform_commission += p_comm
                total_gst_on_commission += p_gst
                day_platform_comm += p_comm
                day_gst += p_gst

                if platform_name not in platform_breakdown:
                    platform_breakdown[platform_name] = {"sales": 0, "commission": 0, "gst": 0}
                platform_breakdown[platform_name]["sales"] += amount
                platform_breakdown[platform_name]["commission"] += p_comm
                platform_breakdown[platform_name]["gst"] += p_gst

        # Direct sales (total minus platform sales)
        platform_total = sum(float(sale.get(f, 0) or 0) for f in PLATFORM_FIELD_MAP)
        direct_sales = max(0, day_total - platform_total)
        if direct_sales > 0:
            if "DIRECT" not in platform_breakdown:
                platform_breakdown["DIRECT"] = {"sales": 0, "commission": 0, "gst": 0}
            platform_breakdown["DIRECT"]["sales"] += direct_sales

        # Payment mode commissions (Card, UPI, etc.)
        for field, mode_name in PAYMENT_FIELD_MAP.items():
            amount = float(sale.get(field, 0) or 0)
            if amount > 0:
                pm_rate = payment_rates.get(mode_name, 0)
                pm_comm = amount * pm_rate / 100
                total_payment_commission += pm_comm
                day_payment_comm += pm_comm

                if mode_name not in payment_breakdown:
                    payment_breakdown[mode_name] = {"sales": 0, "commission": 0}
                payment_breakdown[mode_name]["sales"] += amount
                payment_breakdown[mode_name]["commission"] += pm_comm

        # Daily totals
        if date:
            daily_data[date] = {
                "sales": day_total,
                "platform_commission": day_platform_comm,
                "gst": day_gst,
                "payment_commission": day_payment_comm,
            }

    total_commission = total_platform_commission + total_gst_on_commission + total_payment_commission
    net_revenue = total_sales - total_commission

    return {
        "center": center,
        "period": {"start": start_date, "end": end_date},
        "total_sales": round(total_sales, 2),
        "platform_commission": round(total_platform_commission, 2),
        "gst_on_commission": round(total_gst_on_commission, 2),
        "payment_commission": round(total_payment_commission, 2),
        "total_commission": round(total_commission, 2),
        "net_revenue": round(net_revenue, 2),
        "platform_breakdown": {
            k: {kk: round(vv, 2) for kk, vv in v.items()}
            for k, v in platform_breakdown.items()
        },
        "payment_breakdown": {
            k: {kk: round(vv, 2) for kk, vv in v.items()}
            for k, v in payment_breakdown.items()
        },
        "daily": [
            {"date": d, **{k: round(v, 2) for k, v in vals.items()}}
            for d, vals in sorted(daily_data.items())
        ],
    }


# =======================================
# DASHBOARD ENDPOINTS
# =======================================

@router.post("/dashboard")
async def commission_dashboard(req: CommissionDashboardReq):
    """Get commission dashboard: center-wise or single center"""
    session = await get_session(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")

    # Determine date range
    import calendar as cal
    if req.month:
        year, month = map(int, req.month.split("-"))
        dim = cal.monthrange(year, month)[1]
        start_date = f"{req.month}-01"
        end_date = f"{req.month}-{dim:02d}"
    elif req.start_date and req.end_date:
        start_date = req.start_date
        end_date = req.end_date
    else:
        now = datetime.now(timezone.utc)
        month_str = now.strftime("%Y-%m")
        year, month = now.year, now.month
        dim = cal.monthrange(year, month)[1]
        start_date = f"{month_str}-01"
        end_date = f"{month_str}-{dim:02d}"

    if req.center:
        # Single center detail
        result = await calculate_commissions_for_period(req.center.upper(), start_date, end_date)
        return {"success": True, "data": result}

    # All centers
    centers = await db.centers.find(
        {"active": {"$ne": False}}, {"_id": 0, "code": 1, "name": 1}
    ).to_list(100)

    center_results = []
    grand_totals = {
        "total_sales": 0, "platform_commission": 0, "gst_on_commission": 0,
        "payment_commission": 0, "total_commission": 0, "net_revenue": 0,
    }

    for c in centers:
        code = c.get("code", "")
        if not code:
            continue
        result = await calculate_commissions_for_period(code, start_date, end_date)
        result["center_name"] = c.get("name", code)
        center_results.append(result)
        for key in grand_totals:
            grand_totals[key] += result.get(key, 0)

    # Round grand totals
    grand_totals = {k: round(v, 2) for k, v in grand_totals.items()}

    return {
        "success": True,
        "period": {"start": start_date, "end": end_date},
        "centers": center_results,
        "grand_totals": grand_totals,
    }


@router.post("/for-mis")
async def commissions_for_mis(req: CommissionDashboardReq):
    """Lightweight endpoint for MIS integration: returns total commission per center"""
    session = await get_session(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")

    import calendar as cal
    if req.month:
        year, month = map(int, req.month.split("-"))
        dim = cal.monthrange(year, month)[1]
        start_date = f"{req.month}-01"
        end_date = f"{req.month}-{dim:02d}"
    elif req.start_date and req.end_date:
        start_date = req.start_date
        end_date = req.end_date
    else:
        now = datetime.now(timezone.utc)
        month_str = now.strftime("%Y-%m")
        year, month = now.year, now.month
        dim = cal.monthrange(year, month)[1]
        start_date = f"{month_str}-01"
        end_date = f"{month_str}-{dim:02d}"

    centers = await db.centers.find(
        {"active": {"$ne": False}}, {"_id": 0, "code": 1}
    ).to_list(100)

    result = {}
    for c in centers:
        code = c.get("code", "")
        if not code:
            continue
        data = await calculate_commissions_for_period(code, start_date, end_date)
        result[code] = {
            "total_commission": data["total_commission"],
            "platform_commission": data["platform_commission"],
            "gst_on_commission": data["gst_on_commission"],
            "payment_commission": data["payment_commission"],
            "net_revenue": data["net_revenue"],
        }

    return {"success": True, "period": {"start": start_date, "end": end_date}, "commissions": result}
