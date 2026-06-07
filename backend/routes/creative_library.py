"""Unified Creative Studio Library — admin-friendly oversight & lifecycle
management for all 4 creative deliverables produced by the Studio:

   • Memory Box      → collection `memory_boxes`, id=`box_id`
   • Ad              → collection `ad_creations` (kind != 'invitation'), id=`ad_id`
   • Invitation      → collection `ad_creations` (kind == 'invitation'), id=`ad_id`
   • Video           → collection `marketing_videos`, id=`video_id`

Provides:
   • Combined list with rich filters (type, center, status, date, manager)
   • Soft-delete (managers → own center; admin/super-admin → any center)
   • Restore (admin/super-admin only)
   • Bulk operations (multi-select)
   • Bulk ZIP download of assets (admin/super-admin only)
   • A daily-purge helper that hard-deletes anything soft-deleted > 30 days ago

Routes are mounted under /api/creative-library so the existing per-creative
endpoints stay untouched. The frontend gets one place to learn the schema.
"""
from __future__ import annotations

import io
import logging
import os
import zipfile
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from routes.center_accounts import check_access
from server import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/creative-library", tags=["creative-library"])

PURGE_AFTER_DAYS = 30


# ---------------------------------------------------------------------------
# Type registry — single source of truth for the 4 creative types
# ---------------------------------------------------------------------------
TYPE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "memory_box": {
        "label": "Memory Box",
        "coll": "memory_boxes",
        "id_field": "box_id",
        "title_field": "guest_name",
        "asset_paths": ["asset_pdf", "asset_png", "asset_mp4", "asset_html"],
        "extra_match": {},
    },
    "ad": {
        "label": "Ad",
        "coll": "ad_creations",
        "id_field": "ad_id",
        "title_field": "headline",
        "asset_paths": ["asset_path"],
        "extra_match": {"kind": {"$ne": "invitation"}},
    },
    "invitation": {
        "label": "Invitation",
        "coll": "ad_creations",
        "id_field": "ad_id",
        "title_field": "headline",
        "asset_paths": ["asset_path"],
        "extra_match": {"kind": "invitation"},
    },
    "video": {
        "label": "Video",
        "coll": "marketing_videos",
        "id_field": "video_id",
        "title_field": "headline",
        "asset_paths": ["asset_path"],
        "extra_match": {},
    },
}


def _is_admin(session: dict) -> bool:
    return bool(session.get("is_super_admin") or session.get("is_admin"))


def _own_center(session: dict) -> str:
    return (session.get("center") or "").upper()


def _ensure_type(t: str) -> Dict[str, Any]:
    if t not in TYPE_REGISTRY:
        raise HTTPException(400, f"Unknown creative type: {t}")
    return TYPE_REGISTRY[t]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ListReq(BaseModel):
    token: str
    types: Optional[List[str]] = None     # subset of TYPE_REGISTRY keys; None=all
    center: Optional[str] = None
    manager: Optional[str] = None          # substring match on created_by / guest_name
    from_date: Optional[str] = None        # ISO 'YYYY-MM-DD'
    to_date: Optional[str] = None
    status: str = "active"                 # 'active' | 'deleted' | 'all'
    limit: int = 200


class TargetItem(BaseModel):
    type: str
    id: str


class BulkReq(BaseModel):
    token: str
    items: List[TargetItem]


class SingleReq(BaseModel):
    token: str
    type: str
    id: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _strip_assets_projection(asset_paths: List[str]) -> Dict[str, int]:
    """Project-out the asset_* fields from list reads (they're paths, useless to UI)."""
    return {"_id": 0, **{f: 0 for f in asset_paths}}


def _shape_row(row: dict, t_key: str, reg: dict) -> dict:
    """Normalise a raw DB row into the unified Library row shape."""
    return {
        "type": t_key,
        "type_label": reg["label"],
        "id": row.get(reg["id_field"]) or row.get("_id") or "",
        "center": row.get("center") or "",
        "center_name": row.get("center_name") or "",
        "title": row.get(reg["title_field"]) or "(untitled)",
        "created_by": row.get("created_by") or "Unknown",
        "created_at": row.get("created_at") or "",
        "status": row.get("status") or "active",
        "deleted_at": row.get("deleted_at"),
        "deleted_by": row.get("deleted_by"),
        # Type-specific extras the UI can render conditionally
        "extra": {
            "guest_name": row.get("guest_name"),
            "event_date": row.get("event_date"),
            "occasion": row.get("occasion"),
            "kind": row.get("kind"),
            "festival_theme": row.get("festival_theme"),
            "headline": row.get("headline"),
            "subline": row.get("subline"),
            "language": row.get("language"),
            "mobile": row.get("mobile"),
        },
    }


async def _gather_one_type(t_key: str, reg: dict, base_q: dict,
                           limit: int) -> List[dict]:
    q = {**reg["extra_match"], **base_q}
    proj = _strip_assets_projection(reg["asset_paths"])
    cur = db[reg["coll"]].find(q, proj).sort("created_at", -1).limit(limit)
    rows = await cur.to_list(limit)
    return [_shape_row(r, t_key, reg) for r in rows]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.post("/list")
async def list_creatives(req: ListReq):
    """Cross-type list. Managers see only their own center & active items.
    Admins/Super-Admins see everything; can request status='deleted' or 'all'."""
    session = await check_access(req.token)
    admin = _is_admin(session)

    # Status filter
    if req.status == "deleted":
        status_q = {"status": "deleted"}
    elif req.status == "all":
        status_q = {}
    else:
        status_q = {"status": {"$ne": "deleted"}}

    base_q: Dict[str, Any] = dict(status_q)

    # Center scope
    if req.center:
        # If a non-admin passes a center, force it to their own
        if not admin and req.center.upper() != _own_center(session):
            raise HTTPException(403, "You can only view your own center")
        base_q["center"] = req.center.upper()
    elif not admin:
        own = _own_center(session)
        if own:
            base_q["center"] = own

    # Non-admins can never see soft-deleted rows
    if not admin and "status" in base_q and base_q["status"] != {"$ne": "deleted"}:
        base_q["status"] = {"$ne": "deleted"}

    # Date range
    if req.from_date or req.to_date:
        d = {}
        if req.from_date:
            d["$gte"] = req.from_date
        if req.to_date:
            # inclusive upper bound via dictionary-order comparison on ISO strings
            d["$lte"] = req.to_date + "T23:59:59Z"
        base_q["created_at"] = d

    # Manager substring (created_by OR guest_name)
    if req.manager:
        base_q["$or"] = [
            {"created_by": {"$regex": req.manager, "$options": "i"}},
            {"guest_name": {"$regex": req.manager, "$options": "i"}},
            {"headline": {"$regex": req.manager, "$options": "i"}},
        ]

    types = req.types or list(TYPE_REGISTRY.keys())
    items: List[dict] = []
    counts: Dict[str, int] = {}
    for t in types:
        if t not in TYPE_REGISTRY:
            continue
        reg = TYPE_REGISTRY[t]
        rows = await _gather_one_type(t, reg, base_q, req.limit)
        counts[t] = len(rows)
        items.extend(rows)

    # Sort merged result newest-first
    items.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    items = items[: req.limit]

    return {
        "items": items,
        "counts": counts,
        "total": len(items),
        "is_admin": admin,
    }


async def _check_can_modify(session: dict, t_key: str, item_id: str) -> dict:
    """Raise HTTPException unless session may modify this creative.
    Returns the loaded row (without ObjectId)."""
    reg = _ensure_type(t_key)
    row = await db[reg["coll"]].find_one(
        {reg["id_field"]: item_id, **reg["extra_match"]}, {"_id": 0}
    )
    if not row:
        raise HTTPException(404, f"{reg['label']} {item_id} not found")
    if not _is_admin(session):
        own = _own_center(session)
        if (row.get("center") or "").upper() != own:
            raise HTTPException(403, "You can only modify your own center's creatives")
    return row


async def _do_soft_delete(session: dict, t_key: str, item_id: str) -> bool:
    reg = _ensure_type(t_key)
    await _check_can_modify(session, t_key, item_id)
    res = await db[reg["coll"]].update_one(
        {reg["id_field"]: item_id, **reg["extra_match"]},
        {"$set": {
            "status": "deleted",
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "deleted_by": session.get("managerName") or session.get("mobile") or "Unknown",
        }}
    )
    return res.modified_count > 0


async def _do_restore(session: dict, t_key: str, item_id: str) -> bool:
    if not _is_admin(session):
        raise HTTPException(403, "Only admins can restore deleted creatives")
    reg = _ensure_type(t_key)
    res = await db[reg["coll"]].update_one(
        {reg["id_field"]: item_id, **reg["extra_match"]},
        {"$set": {"status": "active"},
         "$unset": {"deleted_at": "", "deleted_by": ""}}
    )
    return res.modified_count > 0


@router.post("/delete")
async def delete_one(req: SingleReq):
    session = await check_access(req.token)
    ok = await _do_soft_delete(session, req.type, req.id)
    return {"success": ok, "id": req.id, "type": req.type}


@router.post("/restore")
async def restore_one(req: SingleReq):
    session = await check_access(req.token)
    ok = await _do_restore(session, req.type, req.id)
    return {"success": ok, "id": req.id, "type": req.type}


@router.post("/bulk-delete")
async def bulk_delete(req: BulkReq):
    session = await check_access(req.token)
    out = []
    for it in req.items:
        try:
            ok = await _do_soft_delete(session, it.type, it.id)
            out.append({"id": it.id, "type": it.type, "success": ok})
        except HTTPException as e:
            out.append({"id": it.id, "type": it.type, "success": False,
                        "error": e.detail})
    return {"results": out, "total": len(out),
            "deleted": sum(1 for r in out if r["success"])}


@router.post("/bulk-restore")
async def bulk_restore(req: BulkReq):
    session = await check_access(req.token)
    if not _is_admin(session):
        raise HTTPException(403, "Only admins can restore creatives")
    out = []
    for it in req.items:
        try:
            ok = await _do_restore(session, it.type, it.id)
            out.append({"id": it.id, "type": it.type, "success": ok})
        except HTTPException as e:
            out.append({"id": it.id, "type": it.type, "success": False,
                        "error": e.detail})
    return {"results": out, "total": len(out),
            "restored": sum(1 for r in out if r["success"])}


@router.post("/bulk-download")
async def bulk_download(req: BulkReq):
    """Build an on-the-fly ZIP containing every requested creative's asset(s).
    Admin/Super-Admin only."""
    session = await check_access(req.token)
    if not _is_admin(session):
        raise HTTPException(403, "Only admins can bulk download")
    if not req.items:
        raise HTTPException(400, "No items selected")
    if len(req.items) > 100:
        raise HTTPException(400, "Bulk limit is 100 items per archive")

    buf = io.BytesIO()
    used_names = set()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for it in req.items:
            reg = TYPE_REGISTRY.get(it.type)
            if not reg:
                continue
            row = await db[reg["coll"]].find_one(
                {reg["id_field"]: it.id, **reg["extra_match"]}, {"_id": 0}
            )
            if not row:
                continue
            for path_field in reg["asset_paths"]:
                p = row.get(path_field)
                if not p or not os.path.exists(p):
                    continue
                # Build a friendly arcname
                center = (row.get("center") or "NA").upper()
                created_at = (row.get("created_at") or "")[:10]
                title = (row.get(reg["title_field"]) or it.id)
                # Sanitise
                safe_title = "".join(c if c.isalnum() or c in "._- " else "_"
                                     for c in str(title))[:40].strip().replace(" ", "_") or it.id
                ext = os.path.splitext(p)[1] or ".bin"
                base = f"{center}/{reg['label']}/{created_at}_{safe_title}_{it.id[:8]}{ext}"
                # Ensure unique within ZIP
                arcname = base
                i = 1
                while arcname in used_names:
                    arcname = base.replace(ext, f"_{i}{ext}")
                    i += 1
                used_names.add(arcname)
                try:
                    zf.write(p, arcname)
                except Exception as e:
                    logger.warning(f"creative-library bulk-download skipped {p}: {e}")
                    continue

    buf.seek(0)
    fname = f"creative_library_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.zip"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


class TypesReq(BaseModel):
    token: str


@router.post("/types")
async def list_types(req: TypesReq):
    """Return the registry so the UI can render type tabs/filters dynamically."""
    await check_access(req.token)
    return {"types": [
        {"key": k, "label": v["label"]} for k, v in TYPE_REGISTRY.items()
    ]}


# ---------------------------------------------------------------------------
# Auto-purge helper — call once on startup; idempotent.
# ---------------------------------------------------------------------------
async def auto_purge_soft_deleted() -> Dict[str, int]:
    """Hard-delete soft-deleted rows older than PURGE_AFTER_DAYS, and unlink
    their disk assets. Designed to be called once per backend restart."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=PURGE_AFTER_DAYS)).isoformat()
    summary: Dict[str, int] = {}
    for t_key, reg in TYPE_REGISTRY.items():
        coll = db[reg["coll"]]
        # Find candidates first so we can unlink files
        q = {"status": "deleted", "deleted_at": {"$lt": cutoff}, **reg["extra_match"]}
        candidates = await coll.find(q, {"_id": 0}).to_list(2000)
        if not candidates:
            summary[t_key] = 0
            continue
        # Unlink assets best-effort
        for row in candidates:
            for path_field in reg["asset_paths"]:
                p = row.get(path_field)
                if p and isinstance(p, str) and os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception as e:
                        logger.warning(f"auto_purge: could not remove {p}: {e}")
        # Remove rows
        res = await coll.delete_many(q)
        summary[t_key] = res.deleted_count
        logger.info(f"auto_purge {t_key}: removed {res.deleted_count} row(s)")
    return summary
