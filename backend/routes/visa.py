"""Visa Helper / Global Mobility Module (Feb-2026).

Single-file backend covering the entire spec the user laid out:

  GET    /api/visa/countries                  — list seeded + custom countries
  POST   /api/visa/admin/country              — upsert country  (admin only)
  DELETE /api/visa/admin/country/{code}       — delete country  (admin only)

  GET    /api/visa/pathways                   — list pathways
  POST   /api/visa/admin/pathway              — upsert pathway  (admin only)
  DELETE /api/visa/admin/pathway/{id}         — delete pathway  (admin only)

  GET    /api/visa/letter-templates           — list templates
  POST   /api/visa/admin/letter-template      — upsert template (admin only)
  DELETE /api/visa/admin/letter-template/{id} — delete template (admin only)

  GET    /api/visa/entities                   — list entities
  POST   /api/visa/admin/entity               — upsert entity   (admin only)
  DELETE /api/visa/admin/entity/{id}          — delete entity   (admin only)

  GET    /api/visa/signatories                — list signatories
  POST   /api/visa/admin/signatory            — upsert signatory (admin only)
  DELETE /api/visa/admin/signatory/{id}       — delete signatory (admin only)

  POST   /api/visa/application                — create / update application
  GET    /api/visa/applications               — list applications (current user, or all for admin)
  GET    /api/visa/application/{id}           — get one application
  DELETE /api/visa/application/{id}           — delete application

  POST   /api/visa/application/{id}/generate-report  — generate Visa Readiness Report
  POST   /api/visa/application/{id}/generate-letters — generate letters via Emergent LLM
  GET    /api/visa/application/{id}/letter/{letter_id}/word  — download Word doc
  GET    /api/visa/application/{id}/report-pdf        — download report PDF
  GET    /api/visa/application/{id}/checklist-excel   — download checklist Excel
  GET    /api/visa/application/{id}/zip               — download ZIP of all letters
"""
from __future__ import annotations
import io
import logging
import os
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Body, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/visa", tags=["Visa Helper"])

_db = None
_verify_token = None
_verify_token_async = None


def set_db(db):
    global _db
    _db = db


def set_verify_token(fn):
    global _verify_token
    _verify_token = fn


def set_verify_token_async(fn):
    global _verify_token_async
    _verify_token_async = fn


async def _auth(token: str) -> dict:
    sess = None
    if _verify_token_async:
        sess = await _verify_token_async(token)
    if not sess and _verify_token:
        sess = _verify_token(token)
    if not sess:
        raise HTTPException(401, "Invalid or expired token")
    return sess


async def _require_admin(token: str) -> dict:
    """Spec: admin panel restricted to Super Admin + Founders only."""
    sess = await _auth(token)
    role = (sess.get("role") or "").lower()
    if role not in ("super_admin", "superadmin", "founder", "director", "admin"):
        raise HTTPException(403, "Admin access required (Super Admin / Founder only)")
    return sess


def _doc_id() -> str:
    return uuid.uuid4().hex


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strip_id(d: Optional[dict]) -> Optional[dict]:
    if not d:
        return d
    d.pop("_id", None)
    return d


# ─────────────────────────────────────────────────────────────────────────────
# Seed data — 6 priority countries with placeholder pathway info.
# Admins edit via the admin panel, so these are starter values only.
# ─────────────────────────────────────────────────────────────────────────────
_SEED_COUNTRIES = [
    {"code": "AU", "name": "Australia", "flag": "🇦🇺", "currency": "AUD",
     "common_pathway_ids": ["AU-186", "AU-482", "AU-188"],
     "notes": "Strong franchise / business presence pathway — 186 ENS, 482 TSS, 188 BIIP."},
    {"code": "US", "name": "USA", "flag": "🇺🇸", "currency": "USD",
     "common_pathway_ids": ["US-L1A", "US-E2", "US-EB5"],
     "notes": "L-1A intra-company transfer, E-2 investor, EB-5 immigrant investor."},
    {"code": "JP", "name": "Japan", "flag": "🇯🇵", "currency": "JPY",
     "common_pathway_ids": ["JP-BM", "JP-INTRA"],
     "notes": "Business Manager visa, Intra-Company Transferee."},
    {"code": "BE", "name": "Belgium / Brussels", "flag": "🇧🇪", "currency": "EUR",
     "common_pathway_ids": ["BE-SP", "BE-SE"],
     "notes": "Single Permit (work + residence), Self-employed professional card."},
    {"code": "EU", "name": "Europe (Schengen)", "flag": "🇪🇺", "currency": "EUR",
     "common_pathway_ids": ["EU-ICT", "EU-BLUE"],
     "notes": "ICT directive, EU Blue Card for highly skilled non-EU nationals."},
    {"code": "SG", "name": "Singapore", "flag": "🇸🇬", "currency": "SGD",
     "common_pathway_ids": ["SG-EP", "SG-EntrePass"],
     "notes": "Employment Pass for skilled professionals, EntrePass for entrepreneurs."},
]

_SEED_PATHWAYS = [
    {"id": "AU-186", "country_code": "AU", "name": "Subclass 186 ENS — Employer Nomination",
     "type": "Permanent", "min_age": 18, "max_age": 45, "english_required": True,
     "skill_level": "Skilled", "cost_aud": 4640, "duration_months": 6,
     "summary": "Permanent residence via employer nomination. Strong fit for franchise operators with 3+ years experience."},
    {"id": "AU-482", "country_code": "AU", "name": "Subclass 482 TSS — Temporary Skill Shortage",
     "type": "Temporary", "min_age": 18, "max_age": 60, "english_required": True,
     "skill_level": "Skilled", "cost_aud": 3115, "duration_months": 4,
     "summary": "Sponsor-driven temporary work visa, 2-4 year stay, pathway to 186."},
    {"id": "AU-188", "country_code": "AU", "name": "Subclass 188 BIIP — Business Innovation & Investment",
     "type": "Provisional", "min_age": 18, "max_age": 55, "english_required": True,
     "skill_level": "Business", "cost_aud": 9710, "duration_months": 9,
     "summary": "For business owners with significant net worth + business turnover. Investor stream."},
    {"id": "US-L1A", "country_code": "US", "name": "L-1A Intra-Company Transferee (Executive/Manager)",
     "type": "Temporary", "min_age": 18, "max_age": 99, "english_required": False,
     "skill_level": "Executive", "cost_usd": 1885, "duration_months": 4,
     "summary": "Transfer of senior executive from foreign company to US affiliate. 7-year max stay."},
    {"id": "US-E2", "country_code": "US", "name": "E-2 Treaty Investor",
     "type": "Temporary", "english_required": False,
     "cost_usd": 3000, "duration_months": 5,
     "summary": "For nationals of treaty countries (India is NOT a treaty country — applicant must hold treaty passport)."},
    {"id": "US-EB5", "country_code": "US", "name": "EB-5 Immigrant Investor",
     "type": "Permanent", "english_required": False,
     "cost_usd": 11160, "duration_months": 18,
     "summary": "$800,000+ investment in US business creating 10 jobs. Permanent green card."},
    {"id": "JP-BM", "country_code": "JP", "name": "Business Manager Visa",
     "type": "Temporary", "english_required": False,
     "cost_jpy": 4000, "duration_months": 5,
     "summary": "For directors managing a Japan-based subsidiary; minimum 5M JPY capital or 2 employees."},
    {"id": "JP-INTRA", "country_code": "JP", "name": "Intra-Company Transferee",
     "type": "Temporary",
     "cost_jpy": 4000, "duration_months": 3,
     "summary": "Transfer from foreign branch to Japan branch; 1 year+ employment with parent."},
    {"id": "BE-SP", "country_code": "BE", "name": "Single Permit (Work + Residence)",
     "type": "Temporary",
     "cost_eur": 200, "duration_months": 4,
     "summary": "Combined work + residence for non-EU professionals; salary threshold applies."},
    {"id": "BE-SE", "country_code": "BE", "name": "Self-Employed Professional Card",
     "type": "Temporary",
     "cost_eur": 350, "duration_months": 6,
     "summary": "For entrepreneurs setting up own business in Belgium."},
    {"id": "EU-ICT", "country_code": "EU", "name": "ICT Directive (Intra-Corporate Transferee)",
     "type": "Temporary",
     "cost_eur": 150, "duration_months": 4,
     "summary": "EU-wide directive for managers/specialists transferred within multinational."},
    {"id": "EU-BLUE", "country_code": "EU", "name": "EU Blue Card",
     "type": "Temporary",
     "cost_eur": 140, "duration_months": 3,
     "summary": "For highly skilled non-EU professionals; salary 1.5× national average."},
    {"id": "SG-EP", "country_code": "SG", "name": "Employment Pass",
     "type": "Temporary",
     "cost_sgd": 225, "duration_months": 2,
     "summary": "Skilled professional pass, monthly salary ≥ SGD 5,000 + COMPASS points."},
    {"id": "SG-EntrePass", "country_code": "SG", "name": "EntrePass",
     "type": "Temporary",
     "cost_sgd": 175, "duration_months": 3,
     "summary": "For foreign entrepreneurs starting/operating a Singapore-registered business."},
]

_DEFAULT_LETTER_TYPES = [
    ("employment_offer", "Employment Offer Letter", "Offer of Employment & Salary Details", "Confirm employment terms to immigration"),
    ("employment_agreement", "Employment Agreement Summary", "Summary of Employment Contract", "Provide quick reference to full agreement"),
    ("position_description", "Position Description", "Role, Responsibilities & Reporting", "Detail the proposed role to visa officer"),
    ("business_justification", "Business Justification Letter", "Business Need for the Role", "Justify why the proposed role is needed"),
    ("expansion_plan", "Expansion Plan Letter", "International Expansion Strategy", "Show genuine business expansion plan"),
    ("franchise_support", "Franchise Support Letter", "Franchise Network Support Confirmation", "Confirm support from franchise network"),
    ("salary_justification", "Salary Justification Letter", "Salary Benchmark & Market Justification", "Justify proposed salary vs market"),
    ("director_resolution", "Director Appointment Resolution", "Board Resolution — Director Appointment", "Board approval of appointment"),
    ("shareholding_confirmation", "Shareholding Confirmation", "Confirmation of Shareholding Interest", "Prove applicant's ownership stake"),
    ("org_chart", "Organisation Chart Summary", "Organisational Structure", "Visual + textual org chart"),
    ("experience_verification", "Experience Verification Letter", "Verification of Prior Work Experience", "Confirm years and nature of experience"),
    ("centre_setup", "Centre Setup Confirmation", "Confirmation of New Centre Setup", "Prove the centre/branch is being established"),
    ("international_experience", "International Expansion Experience Letter", "Track Record of International Expansion", "Demonstrate prior cross-border experience"),
    ("personal_statement", "Applicant Personal Statement", "Personal Statement of Intent", "Applicant's own narrative"),
    ("family_support", "Family / Spouse Support Note", "Family / Spouse Inclusion Note", "Supporting family in the application"),
]

_DEFAULT_ENTITIES = [
    {"id": "ENT-IN", "name": "Manaswini Foods Pvt. Ltd.",
     "country_code": "IN", "registration_number": "U15549MH2014PTC257421",
     "address": "Hinjewadi, Pune, Maharashtra, India",
     "is_parent": True, "notes": "Indian parent company."},
]

_DEFAULT_SIGNATORIES = [
    {"id": "SIG-JK", "name": "Jayanti Kathale", "role": "Founder & Managing Director",
     "entity_id": "ENT-IN", "email": "jayanti@purnabramha.com", "phone": ""},
    {"id": "SIG-SK", "name": "Sandeep Kathale", "role": "Director — Global Operations",
     "entity_id": "ENT-IN", "email": "sandeep@purnabramha.com", "phone": ""},
]


async def _ensure_seeds():
    """Idempotent seeding — runs once per backend restart if collection empty."""
    if _db is None:
        return
    if await _db.visa_countries.count_documents({}) == 0:
        await _db.visa_countries.insert_many(
            [{**c, "_seed": True, "created_at": _now_iso()} for c in _SEED_COUNTRIES]
        )
    if await _db.visa_pathways.count_documents({}) == 0:
        await _db.visa_pathways.insert_many(
            [{**p, "_seed": True, "created_at": _now_iso()} for p in _SEED_PATHWAYS]
        )
    if await _db.visa_letter_templates.count_documents({}) == 0:
        await _db.visa_letter_templates.insert_many([
            {"id": k, "name": n, "subject": s, "purpose": p,
             "body_template": f"[{n} — body will be AI-generated using applicant + company context]",
             "_seed": True, "created_at": _now_iso()}
            for (k, n, s, p) in _DEFAULT_LETTER_TYPES
        ])
    if await _db.visa_entities.count_documents({}) == 0:
        await _db.visa_entities.insert_many(
            [{**e, "_seed": True, "created_at": _now_iso()} for e in _DEFAULT_ENTITIES]
        )
    if await _db.visa_signatories.count_documents({}) == 0:
        await _db.visa_signatories.insert_many(
            [{**s, "_seed": True, "created_at": _now_iso()} for s in _DEFAULT_SIGNATORIES]
        )


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic request models
# ─────────────────────────────────────────────────────────────────────────────
class _TokenReq(BaseModel):
    token: str


class _ApplicationReq(BaseModel):
    token: str
    application_id: Optional[str] = None
    country_code: str
    applicant: Dict[str, Any] = Field(default_factory=dict)   # spec section 2
    business: Dict[str, Any] = Field(default_factory=dict)    # spec section 3
    status: str = "draft"   # draft | report_generated | letters_generated | submitted


class _GenerateLettersReq(BaseModel):
    token: str
    application_id: str
    letter_keys: Optional[List[str]] = None     # None == ALL
    scope: str = "all"                          # all | company | franchise | personal | resolutions


# ─────────────────────────────────────────────────────────────────────────────
# Read endpoints
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/countries")
async def list_countries(token: str = Query(...)):
    await _auth(token)
    await _ensure_seeds()
    docs = await _db.visa_countries.find({}, {"_id": 0}).sort("name", 1).to_list(None)
    return {"success": True, "countries": docs}


@router.get("/pathways")
async def list_pathways(token: str = Query(...), country_code: Optional[str] = Query(None)):
    await _auth(token)
    await _ensure_seeds()
    q = {"country_code": country_code} if country_code else {}
    docs = await _db.visa_pathways.find(q, {"_id": 0}).sort("name", 1).to_list(None)
    return {"success": True, "pathways": docs}


@router.get("/letter-templates")
async def list_letter_templates(token: str = Query(...)):
    await _auth(token)
    await _ensure_seeds()
    docs = await _db.visa_letter_templates.find({}, {"_id": 0}).sort("name", 1).to_list(None)
    return {"success": True, "templates": docs}


@router.get("/entities")
async def list_entities(token: str = Query(...)):
    await _auth(token)
    await _ensure_seeds()
    docs = await _db.visa_entities.find({}, {"_id": 0}).sort("name", 1).to_list(None)
    return {"success": True, "entities": docs}


@router.get("/signatories")
async def list_signatories(token: str = Query(...)):
    await _auth(token)
    await _ensure_seeds()
    docs = await _db.visa_signatories.find({}, {"_id": 0}).sort("name", 1).to_list(None)
    return {"success": True, "signatories": docs}


# ─────────────────────────────────────────────────────────────────────────────
# Admin CRUD (Super Admin / Founder only)
# ─────────────────────────────────────────────────────────────────────────────
async def _upsert(coll: str, doc: dict, id_field: str = "id") -> dict:
    if not doc.get(id_field):
        doc[id_field] = f"{coll[:3].upper()}-{_doc_id()[:8]}"
    doc.setdefault("created_at", _now_iso())
    doc["updated_at"] = _now_iso()
    await _db[coll].update_one({id_field: doc[id_field]}, {"$set": doc}, upsert=True)
    return _strip_id(await _db[coll].find_one({id_field: doc[id_field]}, {"_id": 0}))


@router.post("/admin/country")
async def upsert_country(data: dict = Body(...)):
    await _require_admin(data.get("token", ""))
    body = {k: v for k, v in data.items() if k != "token"}
    return {"success": True, "country": await _upsert("visa_countries", body, "code")}


@router.delete("/admin/country/{code}")
async def delete_country(code: str, token: str = Query(...)):
    await _require_admin(token)
    await _db.visa_countries.delete_one({"code": code})
    return {"success": True}


@router.post("/admin/pathway")
async def upsert_pathway(data: dict = Body(...)):
    await _require_admin(data.get("token", ""))
    body = {k: v for k, v in data.items() if k != "token"}
    return {"success": True, "pathway": await _upsert("visa_pathways", body, "id")}


@router.delete("/admin/pathway/{pid}")
async def delete_pathway(pid: str, token: str = Query(...)):
    await _require_admin(token)
    await _db.visa_pathways.delete_one({"id": pid})
    return {"success": True}


@router.post("/admin/letter-template")
async def upsert_letter_template(data: dict = Body(...)):
    await _require_admin(data.get("token", ""))
    body = {k: v for k, v in data.items() if k != "token"}
    return {"success": True, "template": await _upsert("visa_letter_templates", body, "id")}


@router.delete("/admin/letter-template/{tid}")
async def delete_letter_template(tid: str, token: str = Query(...)):
    await _require_admin(token)
    await _db.visa_letter_templates.delete_one({"id": tid})
    return {"success": True}


@router.post("/admin/entity")
async def upsert_entity(data: dict = Body(...)):
    await _require_admin(data.get("token", ""))
    body = {k: v for k, v in data.items() if k != "token"}
    return {"success": True, "entity": await _upsert("visa_entities", body, "id")}


@router.delete("/admin/entity/{eid}")
async def delete_entity(eid: str, token: str = Query(...)):
    await _require_admin(token)
    await _db.visa_entities.delete_one({"id": eid})
    return {"success": True}


@router.post("/admin/signatory")
async def upsert_signatory(data: dict = Body(...)):
    await _require_admin(data.get("token", ""))
    body = {k: v for k, v in data.items() if k != "token"}
    return {"success": True, "signatory": await _upsert("visa_signatories", body, "id")}


@router.delete("/admin/signatory/{sid}")
async def delete_signatory(sid: str, token: str = Query(...)):
    await _require_admin(token)
    await _db.visa_signatories.delete_one({"id": sid})
    return {"success": True}


# ─────────────────────────────────────────────────────────────────────────────
# Application — wizard answers + status
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/application")
async def upsert_application(req: _ApplicationReq):
    sess = await _auth(req.token)
    aid = req.application_id or f"VA-{_doc_id()[:10].upper()}"
    doc = {
        "application_id": aid,
        "country_code": req.country_code,
        "applicant": req.applicant or {},
        "business": req.business or {},
        "status": req.status,
        "owner_user": sess.get("mobile") or sess.get("email") or "unknown",
        "updated_at": _now_iso(),
    }
    existing = await _db.visa_applications.find_one({"application_id": aid}, {"_id": 0})
    if not existing:
        doc["created_at"] = _now_iso()
    await _db.visa_applications.update_one(
        {"application_id": aid}, {"$set": doc}, upsert=True
    )
    return {"success": True, "application_id": aid, "application": _strip_id(
        await _db.visa_applications.find_one({"application_id": aid}, {"_id": 0})
    )}


@router.get("/applications")
async def list_applications(token: str = Query(...)):
    sess = await _auth(token)
    role = (sess.get("role") or "").lower()
    q = {}
    if role not in ("super_admin", "superadmin", "founder", "director", "admin"):
        q["owner_user"] = sess.get("mobile") or sess.get("email") or "unknown"
    docs = await _db.visa_applications.find(q, {"_id": 0}).sort("updated_at", -1).to_list(None)
    return {"success": True, "applications": docs}


@router.get("/application/{aid}")
async def get_application(aid: str, token: str = Query(...)):
    await _auth(token)
    doc = await _db.visa_applications.find_one({"application_id": aid}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Application not found")
    return {"success": True, "application": doc}


@router.delete("/application/{aid}")
async def delete_application(aid: str, token: str = Query(...)):
    await _auth(token)
    await _db.visa_applications.delete_one({"application_id": aid})
    return {"success": True}


# ─────────────────────────────────────────────────────────────────────────────
# Visa Readiness Report — rule + LLM hybrid
# ─────────────────────────────────────────────────────────────────────────────
def _readiness_rules(country_code: str, applicant: dict, business: dict) -> dict:
    """Lightweight rule-based suitability scoring per spec section 4."""
    score = 0
    risks = []
    age = int(applicant.get("age") or 0)
    yoe = float(applicant.get("years_of_experience") or 0)

    # Age 
    if 25 <= age <= 45:
        score += 25
    elif 45 < age <= 55:
        score += 15
    elif age > 55:
        score += 5
        risks.append("Age >55 reduces eligibility for several work-visa subclasses.")
    else:
        score += 10

    # Experience
    if yoe >= 5:
        score += 25
    elif yoe >= 3:
        score += 15
    elif yoe >= 1:
        score += 5
    else:
        risks.append("Less than 1 year experience — most work pathways require 1-3 years minimum.")

    # English
    if applicant.get("english_test_status") in ("Passed", "Exempt"):
        score += 20
    elif applicant.get("english_test_status") == "Booked":
        score += 10
    else:
        risks.append("English test not yet passed — block for AU/SG/UK pathways.")

    # Business documents
    if business.get("franchise_letter_available"):
        score += 10
    else:
        risks.append("No existing franchise letter — significant gap for franchise-driven visa narratives.")
    if business.get("business_plan_available"):
        score += 10
    else:
        risks.append("Business plan missing — needed for investor / business-owner pathways.")
    if business.get("financial_proof_available"):
        score += 10
    else:
        risks.append("Financial proof missing — settlement/business funds need to be evidenced.")

    suitability = "Strong" if score >= 75 else "Medium" if score >= 45 else "Weak"
    return {"score": score, "suitability": suitability, "risks": risks}


@router.post("/application/{aid}/generate-report")
async def generate_report(aid: str, data: dict = Body(...)):
    await _auth(data.get("token", ""))
    app_doc = await _db.visa_applications.find_one({"application_id": aid}, {"_id": 0})
    if not app_doc:
        raise HTTPException(404, "Application not found")

    rules = _readiness_rules(app_doc["country_code"], app_doc.get("applicant") or {}, app_doc.get("business") or {})
    pathways = await _db.visa_pathways.find(
        {"country_code": app_doc["country_code"]}, {"_id": 0}
    ).to_list(None)
    age = int((app_doc.get("applicant") or {}).get("age") or 0)
    yoe = float((app_doc.get("applicant") or {}).get("years_of_experience") or 0)
    ranked = []
    for p in pathways:
        fit = 0
        if (p.get("min_age") or 0) <= age <= (p.get("max_age") or 99):
            fit += 20
        if yoe >= 3:
            fit += 20
        if p.get("type") == "Permanent" and rules["suitability"] == "Strong":
            fit += 20
        ranked.append({"pathway": p, "fit_score": fit})
    ranked.sort(key=lambda x: x["fit_score"], reverse=True)

    company_docs = [
        "Company registration certificate", "MoA / AoA", "Latest audited financials",
        "Tax filings (3 years)", "Board resolution authorising the appointment",
        "Letter of appointment / employment offer",
        "Position description (PD)", "Business plan / expansion plan",
        "Franchise network proof", "Organisation chart",
    ]
    applicant_docs = [
        "Passport (all pages)", "Educational certificates",
        "English test result (if applicable)", "Police clearance certificate",
        "Medical examination report", "CV / résumé",
        "Experience verification letters from prior employers",
        "Bank statements (6 months)", "Personal statement",
    ]
    family_docs = [
        "Marriage certificate (if spouse included)",
        "Birth certificates of children",
        "Spouse passport + English proof",
        "Police clearance for adults",
        "School / university letters for children",
    ] if (app_doc.get("applicant") or {}).get("family_included") else []

    cost_heads = [
        {"head": "Government visa fee", "estimate": "varies by pathway, see Pathway table"},
        {"head": "Skills assessment (if applicable)", "estimate": "₹15,000–₹50,000"},
        {"head": "Medical examination", "estimate": "₹6,000–₹12,000 per person"},
        {"head": "Police clearance", "estimate": "₹500 per certificate"},
        {"head": "Translation / notarisation", "estimate": "₹3,000–₹10,000"},
        {"head": "Immigration consultant / lawyer", "estimate": "₹50,000–₹3,00,000"},
        {"head": "Travel + relocation", "estimate": "case-by-case"},
    ]

    next_steps = [
        "Confirm preferred visa pathway with consultant",
        "Initiate skills assessment (if required)",
        "Book English / language test if not already passed",
        "Collect company-side documents (Section: Company docs)",
        "Draft and sign all required letters via the Letter Generation step",
        "Compile applicant + family documents",
        "Final review before lodgement",
    ]

    signatory_letters = await _signatory_letter_plan(app_doc)

    report = {
        "generated_at": _now_iso(),
        "suitability": rules["suitability"],
        "score": rules["score"],
        "risks": rules["risks"],
        "ranked_pathways": ranked,
        "documents_required": {
            "company": company_docs,
            "applicant": applicant_docs,
            "family": family_docs,
        },
        "cost_heads": cost_heads,
        "estimated_timeline": (
            ranked[0]["pathway"].get("duration_months") if ranked else 6
        ),
        "next_steps": next_steps,
        "signatory_letter_plan": signatory_letters,
        "disclaimer": (
            "This is an internal preparation tool. Final visa advice must be verified "
            "by a licensed immigration consultant / lawyer for the relevant country."
        ),
    }

    await _db.visa_applications.update_one(
        {"application_id": aid},
        {"$set": {"report": report, "status": "report_generated", "updated_at": _now_iso()}},
    )
    return {"success": True, "report": report}


async def _signatory_letter_plan(app_doc: dict) -> List[dict]:
    """Map every default letter type to a signatory + entity, per spec 6."""
    templates = await _db.visa_letter_templates.find({}, {"_id": 0}).to_list(None)
    signatories = await _db.visa_signatories.find({}, {"_id": 0}).to_list(None)
    entities = await _db.visa_entities.find({}, {"_id": 0}).to_list(None)

    chosen_signatory_id = (app_doc.get("business") or {}).get("signatory_id")
    chosen_entity_id = (app_doc.get("business") or {}).get("entity_id")
    default_sig = next((s for s in signatories if s.get("id") == chosen_signatory_id), None) or (signatories[0] if signatories else None)
    default_ent = next((e for e in entities if e.get("id") == chosen_entity_id), None) or (entities[0] if entities else None)

    plan = []
    for i, t in enumerate(templates, 1):
        plan.append({
            "sr_no": i,
            "letter_key": t["id"],
            "letter_name": t.get("name"),
            "subject": t.get("subject"),
            "purpose": t.get("purpose"),
            "signed_by": default_sig.get("name") if default_sig else "—",
            "entity_name": default_ent.get("name") if default_ent else "—",
            "country": app_doc.get("country_code"),
            "status": "Pending",
        })
    return plan


# ─────────────────────────────────────────────────────────────────────────────
# Letter Generation — AI via Emergent LLM Key (Claude Sonnet 4.5)
# ─────────────────────────────────────────────────────────────────────────────
_LETTER_SYSTEM_PROMPT = (
    "You are a professional immigration-letter drafter for Purnabramha, an Indian "
    "restaurant franchise group expanding internationally. Draft a formal, polished "
    "letter in third person on company letterhead style. Output ONLY the letter body — "
    "no commentary, no markdown fences, no leading/trailing whitespace. Keep length to "
    "350-600 words. Use British English. Include explicit references to the applicant "
    "name, role, dates, country, and signatory. Close with the signatory's full name and "
    "designation on separate lines. Do not invent facts not present in the context."
)


def _build_letter_prompt(letter: dict, app_doc: dict, sig: dict, ent: dict, country: dict) -> str:
    return f"""LETTER TYPE: {letter['name']}
SUBJECT: {letter['subject']}
PURPOSE: {letter['purpose']}

APPLICANT CONTEXT:
{app_doc.get('applicant', {})}

BUSINESS CONTEXT:
{app_doc.get('business', {})}

SIGNATORY: {sig.get('name')} ({sig.get('role')})
ENTITY: {ent.get('name')} — {ent.get('address', '')}
COUNTRY: {country.get('name')} ({country.get('code')})

Draft the letter now."""


@router.post("/application/{aid}/generate-letters")
async def generate_letters(aid: str, req: _GenerateLettersReq = Body(...)):
    await _auth(req.token)
    app_doc = await _db.visa_applications.find_one({"application_id": aid}, {"_id": 0})
    if not app_doc:
        raise HTTPException(404, "Application not found")

    templates = await _db.visa_letter_templates.find({}, {"_id": 0}).to_list(None)
    sig_docs = await _db.visa_signatories.find({}, {"_id": 0}).to_list(None)
    ent_docs = await _db.visa_entities.find({}, {"_id": 0}).to_list(None)
    country_doc = await _db.visa_countries.find_one({"code": app_doc["country_code"]}, {"_id": 0}) or {}

    chosen_sig_id = (app_doc.get("business") or {}).get("signatory_id")
    chosen_ent_id = (app_doc.get("business") or {}).get("entity_id")
    sig = next((s for s in sig_docs if s.get("id") == chosen_sig_id), None) or (sig_docs[0] if sig_docs else {})
    ent = next((e for e in ent_docs if e.get("id") == chosen_ent_id), None) or (ent_docs[0] if ent_docs else {})

    # Filter templates by scope
    scope_filters = {
        "all": lambda t: True,
        "company": lambda t: t["id"] in ("employment_offer", "employment_agreement", "position_description",
                                          "business_justification", "expansion_plan", "salary_justification",
                                          "shareholding_confirmation", "org_chart", "centre_setup"),
        "franchise": lambda t: t["id"] in ("franchise_support", "international_experience"),
        "personal": lambda t: t["id"] in ("personal_statement", "family_support", "experience_verification"),
        "resolutions": lambda t: t["id"] in ("director_resolution",),
    }
    scope_fn = scope_filters.get(req.scope, scope_filters["all"])
    if req.letter_keys:
        templates_to_run = [t for t in templates if t["id"] in set(req.letter_keys) and scope_fn(t)]
    else:
        templates_to_run = [t for t in templates if scope_fn(t)]

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(500, "EMERGENT_LLM_KEY not configured")

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
    except Exception as ex:
        raise HTTPException(500, f"emergentintegrations not available: {ex}")

    drafted = []
    for t in templates_to_run:
        try:
            chat = LlmChat(
                api_key=api_key,
                session_id=f"visa-letter-{aid}-{t['id']}-{uuid.uuid4().hex[:6]}",
                system_message=_LETTER_SYSTEM_PROMPT,
            ).with_model("anthropic", "claude-sonnet-4-5-20250929")
            user_text = _build_letter_prompt(t, app_doc, sig, ent, country_doc)
            body_text = await chat.send_message(UserMessage(text=user_text))
            body_text = (body_text or "").strip()
            drafted.append({
                "letter_key": t["id"], "letter_name": t["name"], "subject": t["subject"],
                "purpose": t["purpose"], "body": body_text, "status": "Drafted",
                "signed_by": sig.get("name"), "entity_name": ent.get("name"),
                "country": country_doc.get("name"), "generated_at": _now_iso(),
            })
        except Exception as ex:
            logger.warning(f"visa: letter {t['id']} failed: {ex}")
            drafted.append({
                "letter_key": t["id"], "letter_name": t["name"], "subject": t["subject"],
                "purpose": t["purpose"], "body": f"[Auto-generation failed: {ex}]",
                "status": "Pending", "signed_by": sig.get("name"),
                "entity_name": ent.get("name"), "country": country_doc.get("name"),
            })

    await _db.visa_applications.update_one(
        {"application_id": aid},
        {"$set": {"letters": drafted, "status": "letters_generated", "updated_at": _now_iso()}},
    )
    return {"success": True, "letters": drafted}


# ─────────────────────────────────────────────────────────────────────────────
# Exports — PDF report, Excel checklist, Word letters, ZIP bundle
# ─────────────────────────────────────────────────────────────────────────────
def _report_pdf_bytes(app_doc: dict, country: dict, ent: dict, sig: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    title = ParagraphStyle("T", parent=styles["Heading1"], fontSize=18, textColor=colors.HexColor("#800020"))
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, textColor=colors.HexColor("#1a365d"))
    body = ParagraphStyle("B", parent=styles["Normal"], fontSize=9, leading=12)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    report = app_doc.get("report") or {}
    applicant = app_doc.get("applicant") or {}
    business = app_doc.get("business") or {}

    story = [
        Paragraph("Purnabramha — Visa Readiness Report", title),
        Paragraph(
            f"{ent.get('name', '—')} · Applicant: {applicant.get('name', '—')} · "
            f"Country: {country.get('name', '—')} · "
            f"Prepared by: {sig.get('name', 'System')} · "
            f"Date: {datetime.now().strftime('%d %b %Y')}",
            body),
        Spacer(1, 8),
        Paragraph(f"<b>Suitability:</b> {report.get('suitability', '—')} "
                  f"({report.get('score', 0)}/100)", body),
    ]

    # Risks
    risks = report.get("risks") or []
    if risks:
        story.append(Paragraph("Key Risks", h2))
        for r in risks:
            story.append(Paragraph(f"• {r}", body))
        story.append(Spacer(1, 6))

    # Ranked pathways
    story.append(Paragraph("Suggested Visa Pathways (ranked)", h2))
    rp_rows = [["Pathway", "Type", "Fit", "Duration", "Summary"]]
    for r in (report.get("ranked_pathways") or [])[:5]:
        p = r["pathway"]
        rp_rows.append([
            p.get("name", "")[:35], p.get("type", ""),
            f"{r['fit_score']}/60",
            f"{p.get('duration_months', '?')} mo",
            (p.get("summary") or "")[:60],
        ])
    t = Table(rp_rows, colWidths=[55*mm, 22*mm, 18*mm, 18*mm, 65*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a365d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ]))
    story += [t, Spacer(1, 8)]

    # Document checklists
    for label in ("company", "applicant", "family"):
        items = report.get("documents_required", {}).get(label) or []
        if not items:
            continue
        story.append(Paragraph(f"Documents — {label.title()}", h2))
        for d in items:
            story.append(Paragraph(f"• {d}", body))
        story.append(Spacer(1, 4))

    # Cost heads
    story.append(Paragraph("Estimated Cost Heads", h2))
    for c in report.get("cost_heads") or []:
        story.append(Paragraph(f"• <b>{c['head']}:</b> {c['estimate']}", body))
    story.append(Spacer(1, 4))

    # Next steps
    story.append(Paragraph("Recommended Next Steps", h2))
    for s in report.get("next_steps") or []:
        story.append(Paragraph(f"• {s}", body))
    story.append(Spacer(1, 6))

    # Signatory plan
    plan = report.get("signatory_letter_plan") or []
    if plan:
        story.append(Paragraph("Letter Checklist", h2))
        chk_rows = [["#", "Letter", "Subject", "Signed By", "Status"]]
        for p in plan:
            chk_rows.append([str(p["sr_no"]), p["letter_name"][:30], p["subject"][:30],
                             p["signed_by"][:18], p["status"]])
        t2 = Table(chk_rows, colWidths=[8*mm, 50*mm, 60*mm, 35*mm, 22*mm])
        t2.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a365d")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ]))
        story.append(t2)

    story += [
        Spacer(1, 12),
        Paragraph(f"<i>{report.get('disclaimer', '')}</i>",
                  ParagraphStyle("D", parent=body, textColor=colors.grey, fontSize=7)),
    ]
    doc.build(story)
    return buf.getvalue()


@router.get("/application/{aid}/report-pdf")
async def report_pdf(aid: str, token: str = Query(...)):
    await _auth(token)
    app_doc = await _db.visa_applications.find_one({"application_id": aid}, {"_id": 0})
    if not app_doc:
        raise HTTPException(404, "Application not found")
    if not app_doc.get("report"):
        raise HTTPException(400, "Report not yet generated — call /generate-report first")
    country = await _db.visa_countries.find_one({"code": app_doc["country_code"]}, {"_id": 0}) or {}
    ent = await _db.visa_entities.find_one({"id": (app_doc.get("business") or {}).get("entity_id")}, {"_id": 0}) \
          or await _db.visa_entities.find_one({}, {"_id": 0}) or {}
    sig = await _db.visa_signatories.find_one({"id": (app_doc.get("business") or {}).get("signatory_id")}, {"_id": 0}) \
          or await _db.visa_signatories.find_one({}, {"_id": 0}) or {}
    pdf = _report_pdf_bytes(app_doc, country, ent, sig)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="VisaReport_{aid}.pdf"'})


@router.get("/application/{aid}/checklist-excel")
async def checklist_excel(aid: str, token: str = Query(...)):
    await _auth(token)
    import openpyxl
    from openpyxl.styles import Font, PatternFill

    app_doc = await _db.visa_applications.find_one({"application_id": aid}, {"_id": 0})
    if not app_doc:
        raise HTTPException(404, "Application not found")
    plan = (app_doc.get("report") or {}).get("signatory_letter_plan") or []

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Letter Checklist"
    headers = ["Sr. No.", "Letter / Document", "Subject", "Purpose",
               "Signed By", "Entity Name", "Country", "Status"]
    for col, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=col, value=h)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1a365d")
    for r in plan:
        ws.append([r["sr_no"], r["letter_name"], r["subject"], r["purpose"],
                   r["signed_by"], r["entity_name"], r["country"], r["status"]])
    for col in range(1, 9):
        ws.column_dimensions[chr(64 + col)].width = 22
    buf = io.BytesIO()
    wb.save(buf)
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="VisaChecklist_{aid}.xlsx"'},
    )


def _word_bytes(title: str, body: str, sig_name: str, sig_role: str, ent_name: str) -> bytes:
    """Build a minimal .docx — uses python-docx if available, else falls back to a text-like Word file."""
    try:
        from docx import Document
        from docx.shared import Pt
        doc = Document()
        head = doc.add_paragraph()
        run = head.add_run(ent_name)
        run.bold = True
        run.font.size = Pt(14)
        doc.add_paragraph(datetime.now().strftime("%d %B %Y"))
        doc.add_paragraph("")
        sub = doc.add_paragraph()
        sub.add_run("Subject: ").bold = True
        sub.add_run(title)
        doc.add_paragraph("")
        for para in body.split("\n\n"):
            doc.add_paragraph(para)
        doc.add_paragraph("")
        doc.add_paragraph("Yours sincerely,")
        doc.add_paragraph("")
        doc.add_paragraph(sig_name).runs[0].bold = True
        doc.add_paragraph(sig_role)
        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()
    except ImportError:
        # Fallback: plain-text wrapped as .docx-named file (Word will open as text)
        text = (
            f"{ent_name}\n{datetime.now().strftime('%d %B %Y')}\n\n"
            f"Subject: {title}\n\n{body}\n\nYours sincerely,\n\n{sig_name}\n{sig_role}\n"
        )
        return text.encode("utf-8")


@router.get("/application/{aid}/letter/{letter_key}/word")
async def letter_word(aid: str, letter_key: str, token: str = Query(...)):
    await _auth(token)
    app_doc = await _db.visa_applications.find_one({"application_id": aid}, {"_id": 0})
    if not app_doc:
        raise HTTPException(404, "Application not found")
    letters = app_doc.get("letters") or []
    letter = next((l for l in letters if l["letter_key"] == letter_key), None)
    if not letter:
        raise HTTPException(404, "Letter not generated yet — run /generate-letters first")
    ent = await _db.visa_entities.find_one({"id": (app_doc.get("business") or {}).get("entity_id")}, {"_id": 0}) \
          or await _db.visa_entities.find_one({}, {"_id": 0}) or {}
    sig = await _db.visa_signatories.find_one({"id": (app_doc.get("business") or {}).get("signatory_id")}, {"_id": 0}) \
          or await _db.visa_signatories.find_one({}, {"_id": 0}) or {}
    blob = _word_bytes(letter["letter_name"], letter["body"],
                       sig.get("name", "—"), sig.get("role", "—"), ent.get("name", "—"))
    return Response(
        content=blob,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{letter["letter_name"]}_{aid}.docx"'},
    )


@router.get("/application/{aid}/zip")
async def all_letters_zip(aid: str, token: str = Query(...)):
    """One-click ZIP of report PDF + checklist Excel + every drafted Word letter."""
    await _auth(token)
    app_doc = await _db.visa_applications.find_one({"application_id": aid}, {"_id": 0})
    if not app_doc:
        raise HTTPException(404, "Application not found")
    country = await _db.visa_countries.find_one({"code": app_doc["country_code"]}, {"_id": 0}) or {}
    ent = await _db.visa_entities.find_one({"id": (app_doc.get("business") or {}).get("entity_id")}, {"_id": 0}) \
          or await _db.visa_entities.find_one({}, {"_id": 0}) or {}
    sig = await _db.visa_signatories.find_one({"id": (app_doc.get("business") or {}).get("signatory_id")}, {"_id": 0}) \
          or await _db.visa_signatories.find_one({}, {"_id": 0}) or {}

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if app_doc.get("report"):
            zf.writestr(f"VisaReport_{aid}.pdf", _report_pdf_bytes(app_doc, country, ent, sig))

        # Excel checklist
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Letter Checklist"
            plan = (app_doc.get("report") or {}).get("signatory_letter_plan") or []
            headers = ["Sr. No.", "Letter / Document", "Subject", "Purpose",
                       "Signed By", "Entity Name", "Country", "Status"]
            for col, h in enumerate(headers, 1):
                c = ws.cell(row=1, column=col, value=h)
                c.font = Font(bold=True, color="FFFFFF")
                c.fill = PatternFill("solid", fgColor="1a365d")
            for r in plan:
                ws.append([r["sr_no"], r["letter_name"], r["subject"], r["purpose"],
                           r["signed_by"], r["entity_name"], r["country"], r["status"]])
            xb = io.BytesIO()
            wb.save(xb)
            zf.writestr(f"VisaChecklist_{aid}.xlsx", xb.getvalue())
        except Exception as ex:
            logger.warning(f"visa-zip: checklist Excel failed: {ex}")

        # Letters
        for letter in app_doc.get("letters") or []:
            blob = _word_bytes(
                letter["letter_name"], letter.get("body", ""),
                sig.get("name", "—"), sig.get("role", "—"), ent.get("name", "—"),
            )
            safe_name = "".join(c for c in letter["letter_name"] if c.isalnum() or c in "._- ").replace(" ", "_")
            zf.writestr(f"Letters/{safe_name}.docx", blob)

        # Manifest
        manifest = (
            f"Application: {aid}\n"
            f"Country: {country.get('name', '—')}\n"
            f"Applicant: {(app_doc.get('applicant') or {}).get('name', '—')}\n"
            f"Entity: {ent.get('name', '—')}\n"
            f"Signatory: {sig.get('name', '—')}\n"
            f"Generated: {_now_iso()}\n"
            f"\nDisclaimer: This is an internal preparation tool. Final visa advice "
            f"must be verified by a licensed immigration consultant / lawyer for the "
            f"relevant country.\n"
        )
        zf.writestr("manifest.txt", manifest)

    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="VisaBundle_{aid}.zip"'},
    )
