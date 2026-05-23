"""Booking Intelligence Extensions.

Adds:
  - Tiffin Bookings   (collection: tiffin_bookings)
  - Catering Orders   (collection: catering_orders)
  - Event/Celebration (collection: event_bookings)
  - Menu Master       (collection: menu_master) — hybrid pick-from-master OR custom
  - Today PDF for the EXISTING table bookings collection
  - Per-booking printable PDFs for tiffin / catering / event

Existing /api/bookings routes are NOT touched. Everything lives under
/api/bookings/ext to avoid path collisions.
"""

from __future__ import annotations

import io
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from server import db  # type: ignore
from routes.booking_intelligence import check_booking_access  # reuse auth

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/bookings/ext", tags=["Booking Extensions"])


def _is_accounts_read_only(session: dict) -> bool:
    roles = session.get("roles") or {}
    return bool(roles.get("accounting") or roles.get("accounts"))


def _can_write(session: dict) -> bool:
    """Manager / Admin / SA / Operations can write. Accounts is read-only."""
    if session.get("is_admin") or session.get("is_super_admin"):
        return True
    roles = session.get("roles") or {}
    return bool(roles.get("mgt") or roles.get("operations") or roles.get("ops"))


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class _BaseReq(BaseModel):
    token: str


class TiffinCreate(_BaseReq):
    customer_name: str
    phone: str
    email: Optional[str] = ""
    center: str
    customer_code: Optional[str] = ""
    start_date: str        # YYYY-MM-DD
    end_date: str          # YYYY-MM-DD
    meal_type: str         # 'Lunch' | 'Dinner' | 'Both'
    selected_days: List[str] = []
    selected_items: List[Dict[str, Any]] = []   # [{name, qty, rate, amount}]
    delivery_mode: str = "Delivery"             # 'Delivery' | 'Pickup'
    delivery_time: Optional[str] = ""
    delivery_address: Optional[str] = ""
    subtotal: float = 0
    gst: float = 0
    total: float = 0
    notes: Optional[str] = ""
    payment_status: str = "Pending"
    booking_status: str = "Confirmed"
    assigned_staff: Optional[str] = ""


class CateringCreate(_BaseReq):
    customer_name: str
    phone: str
    email: Optional[str] = ""
    center: str
    billing_address: Optional[str] = ""
    delivery_address: Optional[str] = ""
    order_date: str
    event_date: str
    event_time: Optional[str] = ""
    guest_count: int = 0
    occasion: Optional[str] = ""
    package_name: Optional[str] = ""
    per_person_rate: float = 0
    menu_categories: Dict[str, List[Dict[str, Any]]] = {}   # {Starters:[...], Main Course:[...], ...}
    beverages: List[Dict[str, Any]] = []
    add_ons: List[Dict[str, Any]] = []
    crockery: Optional[str] = ""
    staffing: Optional[str] = ""
    transport_charges: float = 0
    subtotal: float = 0
    gst: float = 0
    total: float = 0
    advance_paid: float = 0
    balance_due: float = 0
    confirmation_status: str = "Quote"   # Quote / Confirmed / Cancelled
    payment_status: str = "Pending"
    assigned_coordinator: Optional[str] = ""
    quote_notes: Optional[str] = ""
    remarks: Optional[str] = ""


class EventCreate(_BaseReq):
    enquiry_id: Optional[str] = ""
    customer_name: str
    phone: str
    email: Optional[str] = ""
    center: str
    event_type: str
    event_date: str
    time_slot: Optional[str] = ""
    guest_count: int = 0
    package_name: Optional[str] = ""
    dal_selection: Optional[str] = ""
    menu_categories: Dict[str, List[Dict[str, Any]]] = {}
    decoration: Optional[str] = ""
    special_rules: Optional[str] = ""
    estimated_total: float = 0
    gst: float = 0
    final_total: float = 0
    advance_paid: float = 0
    balance_due: float = 0
    confirmation_status: str = "Quote"
    payment_status: str = "Pending"
    quotation_link: Optional[str] = ""
    assigned_manager: Optional[str] = ""


class ListReq(_BaseReq):
    centers: List[str] = []
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    status: Optional[str] = None
    search: Optional[str] = None


class IdReq(_BaseReq):
    id: str


class TodayPdfReq(_BaseReq):
    center: Optional[str] = None    # if blank → all accessible
    date: Optional[str] = None      # YYYY-MM-DD; default = today


# ---------------------------------------------------------------------------
# Menu Master
# ---------------------------------------------------------------------------

class MenuItem(BaseModel):
    name: str
    category: str
    default_rate: float = 0
    is_active: bool = True


class MenuItemReq(_BaseReq):
    item: MenuItem


@router.post("/menu/list")
async def menu_list(req: _BaseReq):
    await check_booking_access(req.token)
    items = await db.menu_master.find({"is_active": True}, {"_id": 0}).sort("category", 1).to_list(5000)
    by_cat: Dict[str, List[dict]] = {}
    for it in items:
        by_cat.setdefault(it.get("category") or "Other", []).append(it)
    return {"by_category": by_cat, "items": items}


@router.post("/menu/upsert")
async def menu_upsert(req: MenuItemReq):
    session = await check_booking_access(req.token)
    if not _can_write(session):
        raise HTTPException(403, "Not permitted")
    name = req.item.name.strip()
    if not name:
        raise HTTPException(400, "Item name required")
    doc = req.item.dict()
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.menu_master.update_one({"name": name, "category": req.item.category}, {"$set": doc}, upsert=True)
    return {"success": True}


@router.post("/menu/delete")
async def menu_delete(req: IdReq):
    session = await check_booking_access(req.token)
    if not _can_write(session):
        raise HTTPException(403, "Not permitted")
    # `id` here is the item name|category combo
    name, _, category = req.id.partition("|")
    await db.menu_master.delete_one({"name": name, "category": category})
    return {"success": True}


# ---------------------------------------------------------------------------
# Generic CRUD factory (shared by tiffin / catering / event)
# ---------------------------------------------------------------------------

COLLECTION_OF = {
    "tiffin": "tiffin_bookings",
    "catering": "catering_orders",
    "event": "event_bookings",
}
DATE_FIELD = {
    "tiffin": "start_date",
    "catering": "event_date",
    "event": "event_date",
}


def _new_id(prefix: str) -> str:
    return f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


async def _create(kind: str, payload: dict, session: dict) -> dict:
    if not _can_write(session):
        raise HTTPException(403, "Not permitted")
    col = db[COLLECTION_OF[kind]]
    doc = {k: v for k, v in payload.items() if k != "token"}
    doc["id"] = _new_id(kind.upper())
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    doc["created_by"] = session.get("managerName") or ""
    await col.insert_one(doc)
    doc.pop("_id", None)
    return doc


async def _list(kind: str, req: ListReq, session: dict) -> dict:
    col = db[COLLECTION_OF[kind]]
    q: Dict[str, Any] = {}
    if req.centers:
        q["center"] = {"$in": req.centers}
    date_field = DATE_FIELD[kind]
    if req.from_date or req.to_date:
        rng: Dict[str, Any] = {}
        if req.from_date: rng["$gte"] = req.from_date
        if req.to_date:   rng["$lte"] = req.to_date
        q[date_field] = rng
    if req.status:
        q["$or"] = [{"booking_status": req.status}, {"confirmation_status": req.status}, {"payment_status": req.status}]
    if req.search:
        q["$or"] = (q.get("$or") or []) + [
            {"customer_name": {"$regex": req.search, "$options": "i"}},
            {"phone": {"$regex": req.search, "$options": "i"}},
            {"id": {"$regex": req.search, "$options": "i"}},
        ]
    rows = await col.find(q, {"_id": 0}).sort([(date_field, -1)]).to_list(5000)
    return {"rows": rows}


async def _get(kind: str, _id: str) -> dict:
    col = db[COLLECTION_OF[kind]]
    doc = await col.find_one({"id": _id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, f"{kind} not found")
    return doc


async def _update(kind: str, _id: str, payload: dict, session: dict) -> dict:
    if not _can_write(session):
        raise HTTPException(403, "Not permitted")
    col = db[COLLECTION_OF[kind]]
    update = {k: v for k, v in payload.items() if k not in ("token", "id", "_id", "created_at")}
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    update["updated_by"] = session.get("managerName") or ""
    res = await col.update_one({"id": _id}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(404, f"{kind} not found")
    return await _get(kind, _id)


async def _delete(kind: str, _id: str, session: dict) -> dict:
    if not _can_write(session):
        raise HTTPException(403, "Not permitted")
    col = db[COLLECTION_OF[kind]]
    res = await col.delete_one({"id": _id})
    return {"success": res.deleted_count > 0}


# ---------------------------------------------------------------------------
# Endpoints — Tiffin
# ---------------------------------------------------------------------------

@router.post("/tiffin/create")
async def tiffin_create(req: TiffinCreate):
    session = await check_booking_access(req.token)
    return await _create("tiffin", req.dict(), session)


@router.post("/tiffin/list")
async def tiffin_list(req: ListReq):
    await check_booking_access(req.token)
    return await _list("tiffin", req, {})


@router.post("/tiffin/update/{tid}")
async def tiffin_update(tid: str, req: dict):
    session = await check_booking_access(req.get("token"))
    return await _update("tiffin", tid, req, session)


@router.post("/tiffin/delete/{tid}")
async def tiffin_delete(tid: str, req: _BaseReq):
    session = await check_booking_access(req.token)
    return await _delete("tiffin", tid, session)


# ---------------------------------------------------------------------------
# Endpoints — Catering
# ---------------------------------------------------------------------------

@router.post("/catering/create")
async def catering_create(req: CateringCreate):
    session = await check_booking_access(req.token)
    return await _create("catering", req.dict(), session)


@router.post("/catering/list")
async def catering_list(req: ListReq):
    await check_booking_access(req.token)
    return await _list("catering", req, {})


@router.post("/catering/update/{cid}")
async def catering_update(cid: str, req: dict):
    session = await check_booking_access(req.get("token"))
    return await _update("catering", cid, req, session)


@router.post("/catering/delete/{cid}")
async def catering_delete(cid: str, req: _BaseReq):
    session = await check_booking_access(req.token)
    return await _delete("catering", cid, session)


# ---------------------------------------------------------------------------
# Endpoints — Event
# ---------------------------------------------------------------------------

@router.post("/event/create")
async def event_create(req: EventCreate):
    session = await check_booking_access(req.token)
    return await _create("event", req.dict(), session)


@router.post("/event/list")
async def event_list(req: ListReq):
    await check_booking_access(req.token)
    return await _list("event", req, {})


@router.post("/event/update/{eid}")
async def event_update(eid: str, req: dict):
    session = await check_booking_access(req.get("token"))
    return await _update("event", eid, req, session)


@router.post("/event/delete/{eid}")
async def event_delete(eid: str, req: _BaseReq):
    session = await check_booking_access(req.token)
    return await _delete("event", eid, session)


# ---------------------------------------------------------------------------
# Dashboard consolidation
# ---------------------------------------------------------------------------

@router.post("/dashboard")
async def consolidated_dashboard(req: ListReq):
    """Counts + revenue rolled up across all 4 booking types for a period."""
    await check_booking_access(req.token)
    q_table: Dict[str, Any] = {}
    if req.from_date or req.to_date:
        rng = {}
        if req.from_date: rng["$gte"] = req.from_date
        if req.to_date:   rng["$lte"] = req.to_date
        q_table["date"] = rng
    if req.centers:
        q_table["center"] = {"$in": req.centers}

    table_count = await db.bookings.count_documents(q_table)

    async def _counts(kind: str) -> Dict[str, Any]:
        col = db[COLLECTION_OF[kind]]
        date_field = DATE_FIELD[kind]
        q: Dict[str, Any] = {}
        if req.from_date or req.to_date:
            rng = {}
            if req.from_date: rng["$gte"] = req.from_date
            if req.to_date:   rng["$lte"] = req.to_date
            q[date_field] = rng
        if req.centers:
            q["center"] = {"$in": req.centers}
        cnt = await col.count_documents(q)
        amt_field = {"tiffin": "total", "catering": "total", "event": "final_total"}[kind]
        pipeline = [{"$match": q}, {"$group": {"_id": None, "sum": {"$sum": f"${amt_field}"}}}]
        total = 0
        async for d in col.aggregate(pipeline):
            total = d.get("sum", 0)
        return {"count": cnt, "amount": round(float(total or 0), 2)}

    return {
        "tables": {"count": table_count},
        "tiffin": await _counts("tiffin"),
        "catering": await _counts("catering"),
        "event": await _counts("event"),
    }


# ---------------------------------------------------------------------------
# PDFs
# ---------------------------------------------------------------------------

def _pdf_header(story, styles, title: str, subtitle: str = ""):
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph, Spacer
    h1 = ParagraphStyle("h1", parent=styles["Title"], fontSize=16, textColor=colors.HexColor("#5C0000"))
    story.append(Paragraph(f"<b>{title}</b>", h1))
    if subtitle:
        story.append(Paragraph(subtitle, styles["BodyText"]))
    story.append(Spacer(1, 8))


@router.post("/today-table-pdf")
async def today_table_pdf(req: TodayPdfReq):
    """Printable PDF of today's table bookings (center summary header + table)."""
    session = await check_booking_access(req.token)
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    date_str = req.date or datetime.now().strftime("%Y-%m-%d")
    q: Dict[str, Any] = {"date": date_str}
    if req.center:
        q["center"] = req.center
    rows = await db.bookings.find(q, {"_id": 0}).sort([("time_slot", 1)]).to_list(2000)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=0.4 * inch, rightMargin=0.4 * inch,
                            topMargin=0.5 * inch, bottomMargin=0.5 * inch,
                            title=f"Table Bookings {date_str}")
    styles = getSampleStyleSheet()
    story: List = []

    title = f"Table Bookings — {date_str}"
    subtitle = f"Center: <b>{req.center or 'All Accessible'}</b> · Total bookings: <b>{len(rows)}</b> · "
    subtitle += f"Total guests: <b>{sum(int(r.get('num_guests') or 0) for r in rows)}</b>"
    _pdf_header(story, styles, title, subtitle)

    head = ["Time", "Guest", "Contact", "Guests", "Occasion", "Table", "Status", "Notes"]
    data = [head]
    for r in rows:
        data.append([
            r.get("time_slot", ""),
            r.get("guest_name", "")[:24],
            r.get("phone", ""),
            str(r.get("num_guests") or ""),
            (r.get("celebration_type") or r.get("guest_type") or "")[:18],
            (r.get("table_allotted") or "")[:18],
            (r.get("status") or "")[:14],
            (r.get("remarks") or r.get("special_request") or "")[:30],
        ])
    if len(data) == 1:
        data.append(["—", "No bookings", "", "", "", "", "", ""])
    t = Table(data, repeatRows=1, colWidths=[1.1*inch, 1.9*inch, 1.3*inch, 0.6*inch, 1.3*inch, 1.1*inch, 1.0*inch, 1.9*inch])
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 10),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fde68a")),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        f"Generated by Purnabramha IntraPB · {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · {session.get('managerName','')}",
        styles["BodyText"]))

    doc.build(story)
    return StreamingResponse(io.BytesIO(buf.getvalue()), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="table_bookings_{date_str}.pdf"'})


def _build_single_pdf(kind: str, doc: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    buf = io.BytesIO()
    pdf = SimpleDocTemplate(buf, pagesize=A4, leftMargin=0.5*inch, rightMargin=0.5*inch,
                            topMargin=0.5*inch, bottomMargin=0.5*inch, title=doc.get("id", kind))
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=10, leading=13)
    story: List = []
    title_map = {"tiffin": "Tiffin Booking", "catering": "Catering Order", "event": "Event / Celebration Booking"}
    _pdf_header(story, styles, f"{title_map[kind]}  ·  {doc.get('id','')}",
                f"Center: <b>{doc.get('center','')}</b> &nbsp;·&nbsp; Created: {doc.get('created_at','')[:10]}")

    # Common customer block
    cust = [
        ["Customer", doc.get("customer_name", "")],
        ["Phone", doc.get("phone", "")],
        ["Email", doc.get("email", "") or "—"],
    ]
    if kind == "tiffin":
        cust += [
            ["Customer Code", doc.get("customer_code", "") or "—"],
            ["Period", f"{doc.get('start_date','')} → {doc.get('end_date','')}"],
            ["Meal", doc.get("meal_type", "")],
            ["Days", ", ".join(doc.get("selected_days") or []) or "—"],
            ["Mode", doc.get("delivery_mode", "")],
            ["Delivery Time", doc.get("delivery_time", "") or "—"],
            ["Delivery Address", doc.get("delivery_address", "") or "—"],
        ]
    elif kind == "catering":
        cust += [
            ["Order Date", doc.get("order_date", "")],
            ["Event Date / Time", f"{doc.get('event_date','')} {doc.get('event_time','')}"],
            ["Occasion", doc.get("occasion", "") or "—"],
            ["Guest Count", str(doc.get("guest_count", "")) or "—"],
            ["Package", doc.get("package_name", "") or "—"],
            ["Per-Person Rate", f"{doc.get('per_person_rate', 0):,.2f}"],
            ["Billing Address", doc.get("billing_address", "") or "—"],
            ["Delivery Address", doc.get("delivery_address", "") or "—"],
        ]
    else:  # event
        cust += [
            ["Enquiry ID", doc.get("enquiry_id", "") or "—"],
            ["Event Type", doc.get("event_type", "")],
            ["Event Date / Slot", f"{doc.get('event_date','')} {doc.get('time_slot','')}"],
            ["Guest Count", str(doc.get("guest_count", "")) or "—"],
            ["Package", doc.get("package_name", "") or "—"],
            ["Dal Selection", doc.get("dal_selection", "") or "—"],
            ["Decoration", doc.get("decoration", "") or "—"],
            ["Special Rules", doc.get("special_rules", "") or "—"],
        ]
    t = Table(cust, colWidths=[1.8*inch, 5.2*inch])
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9.5),
        ("FONT", (1, 0), (1, -1), "Helvetica", 9.5),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#fef3c7")),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t); story.append(Spacer(1, 10))

    # Menu / line items
    def _line_table(title: str, rows: List[Dict[str, Any]]):
        if not rows:
            return
        story.append(Paragraph(f"<b>{title}</b>", body))
        d = [["Item", "Qty", "Rate", "Amount"]]
        for r in rows:
            d.append([r.get("name", ""), str(r.get("qty", "")) or "—",
                      f"{float(r.get('rate', 0) or 0):,.2f}",
                      f"{float(r.get('amount', 0) or 0):,.2f}"])
        tbl = Table(d, repeatRows=1, colWidths=[3.6*inch, 0.8*inch, 1.3*inch, 1.3*inch])
        tbl.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9.5),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fde68a")),
            ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
        ]))
        story.append(tbl); story.append(Spacer(1, 6))

    if kind == "tiffin":
        _line_table("Selected Items", doc.get("selected_items") or [])
    else:
        cats = doc.get("menu_categories") or {}
        for cat, items in cats.items():
            if items:
                _line_table(cat, items)
        if kind == "catering":
            _line_table("Beverages", doc.get("beverages") or [])
            _line_table("Add-ons", doc.get("add_ons") or [])

    # Totals
    if kind == "tiffin":
        totals = [["Subtotal", f"{doc.get('subtotal',0):,.2f}"], ["GST", f"{doc.get('gst',0):,.2f}"],
                  ["Total", f"{doc.get('total',0):,.2f}"]]
    elif kind == "catering":
        totals = [["Transport", f"{doc.get('transport_charges',0):,.2f}"], ["Subtotal", f"{doc.get('subtotal',0):,.2f}"],
                  ["GST", f"{doc.get('gst',0):,.2f}"], ["Total", f"{doc.get('total',0):,.2f}"],
                  ["Advance Paid", f"{doc.get('advance_paid',0):,.2f}"], ["Balance Due", f"{doc.get('balance_due',0):,.2f}"]]
    else:
        totals = [["Estimated Total", f"{doc.get('estimated_total',0):,.2f}"], ["GST", f"{doc.get('gst',0):,.2f}"],
                  ["Final Total", f"{doc.get('final_total',0):,.2f}"],
                  ["Advance Paid", f"{doc.get('advance_paid',0):,.2f}"], ["Balance Due", f"{doc.get('balance_due',0):,.2f}"]]
    tot = Table(totals, colWidths=[5.2*inch, 1.8*inch])
    tot.setStyle(TableStyle([
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 10),
        ("FONT", (1, 0), (1, -1), "Helvetica", 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#dcfce7")),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(tot); story.append(Spacer(1, 10))

    notes_field = {"tiffin": "notes", "catering": "remarks", "event": "special_rules"}[kind]
    notes = doc.get(notes_field) or doc.get("quote_notes") or ""
    if notes:
        story.append(Paragraph(f"<b>Notes</b>", body))
        story.append(Paragraph(notes, body))

    pdf.build(story)
    return buf.getvalue()


@router.post("/{kind}/pdf/{rid}")
async def per_booking_pdf(kind: str, rid: str, req: _BaseReq):
    if kind not in COLLECTION_OF:
        raise HTTPException(404, "Unknown kind")
    await check_booking_access(req.token)
    doc = await _get(kind, rid)
    data = _build_single_pdf(kind, doc)
    return StreamingResponse(io.BytesIO(data), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{kind}_{rid}.pdf"'})


class SendQuoteReq(_BaseReq):
    to_email: Optional[str] = None     # override; falls back to doc.email
    cc: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None


@router.post("/{kind}/send-quote/{rid}")
async def send_quote(kind: str, rid: str, req: SendQuoteReq):
    """One-click quote → customer. Generates PDF and emails via configured SMTP.
    Stamps quote_sent_at/quote_sent_to on the doc and logs to booking_quote_sends.
    """
    if kind not in COLLECTION_OF:
        raise HTTPException(404, "Unknown kind")
    session = await check_booking_access(req.token)
    if not _can_write(session):
        raise HTTPException(403, "Not permitted")
    doc = await _get(kind, rid)

    to_email = (req.to_email or doc.get("email") or "").strip()
    if not to_email or "@" not in to_email:
        raise HTTPException(400, "Customer email missing — add an email on the booking or pass to_email.")

    # SMTP config from server CFG
    from server import CFG  # type: ignore
    email_cfg = (CFG or {}).get("email", {}) or {}
    if not email_cfg.get("enabled") or not email_cfg.get("smtp_user") or not email_cfg.get("smtp_pass"):
        raise HTTPException(503, "SMTP not configured on the server. Configure email.smtp_user/smtp_pass first.")

    title_map = {"tiffin": "Tiffin Booking", "catering": "Catering Quote", "event": "Event Quote"}
    label = title_map[kind]
    default_subject = f"{label} — {doc.get('id','')} · Purnabramha"
    default_body = (
        f"Dear {doc.get('customer_name','Customer')},\n\n"
        f"Please find attached the {label.lower()} ({doc.get('id','')}) prepared by our team at Purnabramha "
        f"({doc.get('center','')}).\n\n"
        f"Feel free to reach out for any clarification or to confirm.\n\n"
        "Warm regards,\nPurnabramha Team"
    )
    subject = req.subject or default_subject
    body = req.body or default_body

    pdf_bytes = _build_single_pdf(kind, doc)

    smtp_host = email_cfg.get("smtp_host", "smtp.gmail.com")
    smtp_port = int(email_cfg.get("smtp_port", 587))
    smtp_user = email_cfg["smtp_user"]
    smtp_pass = email_cfg["smtp_pass"]
    from_name = email_cfg.get("from_name", "Purnabramha Team")
    from_email = email_cfg.get("from_email", smtp_user)

    try:
        import smtplib
        from email.message import EmailMessage
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = to_email
        if req.cc:
            msg["Cc"] = req.cc
        msg.set_content(body)
        msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf",
                           filename=f"{kind}_{rid}.pdf")
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            rcpts = [to_email] + ([req.cc] if req.cc else [])
            server.send_message(msg, to_addrs=rcpts)
    except Exception as e:
        logger.error(f"send_quote SMTP failed: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to send email: {e}")

    sent_at = datetime.now(timezone.utc).isoformat()
    sent_by = session.get("managerName") or session.get("mobile") or "Unknown"
    await db[COLLECTION_OF[kind]].update_one(
        {"id": rid},
        {"$set": {"quote_sent_at": sent_at, "quote_sent_to": to_email, "quote_sent_by": sent_by}},
    )
    await db.booking_quote_sends.insert_one({
        "send_id": uuid.uuid4().hex,
        "kind": kind, "booking_id": rid,
        "to_email": to_email, "cc": req.cc,
        "subject": subject, "sent_by": sent_by, "sent_at": sent_at,
        "size_bytes": len(pdf_bytes),
    })
    return {"success": True, "to": to_email, "cc": req.cc, "subject": subject,
            "sent_at": sent_at, "size_kb": round(len(pdf_bytes) / 1024.0, 1)}
