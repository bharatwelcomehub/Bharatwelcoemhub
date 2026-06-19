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
    """Spec: admin panel restricted to Super Admin + Founders only.

    The platform's session shape (from /api/verify_otp) uses boolean flags
    (`is_super_admin`, `is_admin`) rather than a single `role` string, so we
    accept either flag first, then fall back to a role-name allowlist for
    legacy sessions.
    """
    sess = await _auth(token)
    if sess.get("is_super_admin") or sess.get("is_admin"):
        return sess
    role = (sess.get("role") or sess.get("role_key") or "").lower()
    if role in ("super_admin", "superadmin", "founder", "director", "admin"):
        return sess
    raise HTTPException(403, "Admin access required (Super Admin / Founder only)")


def _doc_id() -> str:
    return uuid.uuid4().hex


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strip_id(d: Optional[dict]) -> Optional[dict]:
    if not d:
        return d
    d.pop("_id", None)
    return d


def _dedupe_by(docs: List[dict], key: str) -> List[dict]:
    """Return docs deduplicated by `key`, preserving first occurrence."""
    seen = set()
    out = []
    for d in docs:
        k = d.get(key)
        if k in seen:
            continue
        seen.add(k)
        out.append(d)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Seed data — 6 priority countries with placeholder pathway info.
# Admins edit via the admin panel, so these are starter values only.
# ─────────────────────────────────────────────────────────────────────────────
_SEED_COUNTRIES = [
    {"code": "AU", "name": "Australia", "flag": "🇦🇺", "currency": "AUD",
     "common_pathway_ids": ["AU-186", "AU-482", "AU-188", "AU-494", "AU-GT", "AU-400", "AU-407", "AU-408"],
     "notes": "Long-term: 186 ENS, 482 TSS, 188 BIIP, 494 Regional, Global Talent. Short-stay activity visas: 400 (specialist), 407 (training), 408 (events / entertainment)."},
    {"code": "US", "name": "USA", "flag": "🇺🇸", "currency": "USD",
     "common_pathway_ids": ["US-L1A", "US-E2", "US-EB1C", "US-EB2NIW"],
     "notes": "L-1A executive transfer, E-2 investor, EB-1C multinational manager, EB-2 NIW."},
    {"code": "JP", "name": "Japan", "flag": "🇯🇵", "currency": "JPY",
     "common_pathway_ids": ["JP-BM", "JP-HSP"],
     "notes": "Business Manager Visa, Highly Skilled Professional."},
    {"code": "BE", "name": "Belgium / Brussels", "flag": "🇧🇪", "currency": "EUR",
     "common_pathway_ids": ["BE-SP", "BE-SE"],
     "notes": "Single Permit (work + residence), Self-employed professional card."},
    {"code": "EU", "name": "Europe (Schengen)", "flag": "🇪🇺", "currency": "EUR",
     "common_pathway_ids": ["EU-ICT", "EU-BLUE"],
     "notes": "ICT directive, EU Blue Card for highly skilled non-EU nationals."},
    {"code": "SG", "name": "Singapore", "flag": "🇸🇬", "currency": "SGD",
     "common_pathway_ids": ["SG-EP", "SG-EntrePass"],
     "notes": "Employment Pass for skilled professionals, EntrePass for entrepreneurs."},
    {"code": "UK", "name": "United Kingdom", "flag": "🇬🇧", "currency": "GBP",
     "common_pathway_ids": ["UK-SW", "UK-IF", "UK-EW", "UK-DEP"],
     "notes": "Skilled Worker, Innovator Founder (PR pathway), Expansion Worker (UK Expansion), Dependent visa."},
    {"code": "AE", "name": "UAE / Dubai", "flag": "🇦🇪", "currency": "AED",
     "common_pathway_ids": ["AE-GOLDEN", "AE-EMP", "AE-INV", "AE-PARTNER", "AE-FAMILY"],
     "notes": "Golden Visa (10-yr), Employment Visa, Investor Visa, Partner Visa, Family Visa."},
]

_SEED_PATHWAYS = [
    # ── Australia ───────────────────────────────────────────────────────────
    {"id": "AU-186", "country_code": "AU", "name": "Subclass 186 ENS — Employer Nomination Scheme (Direct Entry)",
     "type": "Permanent", "min_age": 18, "max_age": 45, "english_required": True,
     "skill_level": "Skilled", "company_cost_band": "AUD 4,000 – 6,000",
     "applicant_cost_band": "AUD 8,000 – 12,000",
     "duration_months": 11, "timeline_band": "8 – 14 months",
     "key_requirements": ["Existing Australian operations", "Senior management experience", "Genuine position evidence", "English (Competent)", "Skills assessment"],
     "spouse_work_rights": True,
     "summary": "Permanent residence via direct employer nomination. Strong fit for franchise operators expanding into Australia with proven senior leadership."},
    {"id": "AU-482", "country_code": "AU", "name": "Subclass 482 TSS — Temporary Skill Shortage",
     "type": "Temporary", "min_age": 18, "max_age": 60, "english_required": True,
     "skill_level": "Skilled", "company_cost_band": "AUD 2,500 – 4,500",
     "applicant_cost_band": "AUD 3,500 – 6,000",
     "duration_months": 4, "timeline_band": "3 – 6 months",
     "key_requirements": ["Sponsor (SBS approved)", "2+ years in nominated occupation", "English (Vocational)"],
     "spouse_work_rights": True,
     "summary": "Employer-sponsored temporary work visa, 2-4 year stay, common pathway to 186."},
    {"id": "AU-188", "country_code": "AU", "name": "Subclass 188 BIIP — Business Innovation & Investment (Provisional)",
     "type": "Provisional", "min_age": 18, "max_age": 55, "english_required": True,
     "skill_level": "Business", "company_cost_band": "—",
     "applicant_cost_band": "AUD 9,000 – 15,000",
     "duration_months": 12, "timeline_band": "9 – 15 months",
     "key_requirements": ["Net worth threshold", "Business turnover", "Investment commitment"],
     "spouse_work_rights": True,
     "summary": "For business owners with significant net worth + business turnover. Investor / Innovation streams."},
    {"id": "AU-494", "country_code": "AU", "name": "Subclass 494 — Skilled Employer Sponsored Regional",
     "type": "Provisional", "min_age": 18, "max_age": 45, "english_required": True,
     "skill_level": "Skilled", "company_cost_band": "AUD 4,000 – 6,000",
     "applicant_cost_band": "AUD 6,000 – 10,000",
     "duration_months": 9, "timeline_band": "6 – 12 months",
     "key_requirements": ["Regional employer sponsor", "Skills assessment", "Live in regional Australia 3 years"],
     "spouse_work_rights": True,
     "summary": "Regional employer-sponsored visa with PR pathway via 191 after 3 years in regional area."},
    {"id": "AU-GT", "country_code": "AU", "name": "Global Talent (Subclass 858)",
     "type": "Permanent", "min_age": 18, "max_age": 55, "english_required": True,
     "skill_level": "Exceptional", "company_cost_band": "—",
     "applicant_cost_band": "AUD 4,500 – 8,000",
     "duration_months": 8, "timeline_band": "6 – 12 months",
     "key_requirements": ["Exceptional / internationally recognised talent", "High salary potential (FWHIT)", "Nomination by Australian"],
     "spouse_work_rights": True,
     "summary": "PR for individuals with exceptional and internationally recognised achievement in a target sector."},
    {"id": "AU-400", "country_code": "AU", "name": "Subclass 400 — Temporary Work (Short Stay Specialist)",
     "type": "Temporary", "min_age": 18, "max_age": 99, "english_required": False,
     "skill_level": "Specialist", "company_cost_band": "AUD 400 – 800",
     "applicant_cost_band": "AUD 400 – 1,500",
     "duration_months": 1, "timeline_band": "2 – 4 weeks",
     "key_requirements": ["Highly specialised, non-ongoing work", "Stay typically up to 3 months (max 6)", "Sponsoring Australian business / event organiser", "Specific event or one-off project"],
     "spouse_work_rights": False,
     "summary": "Short-stay work visa for specific non-ongoing events, projects or specialist roles — typically 1-3 months. Ideal for chefs/managers being flown in for a launch, festival or major event."},
    {"id": "AU-407", "country_code": "AU", "name": "Subclass 407 — Training Visa",
     "type": "Temporary", "min_age": 18, "max_age": 99, "english_required": False,
     "skill_level": "Trainee", "company_cost_band": "AUD 420 – 800",
     "applicant_cost_band": "AUD 360 – 800",
     "duration_months": 3, "timeline_band": "2 – 4 months",
     "key_requirements": ["Approved temporary activities sponsor (TAS) or government", "Structured workplace-based training plan", "Occupational training programme", "Up to 24 months stay"],
     "spouse_work_rights": True,
     "summary": "For occupational / professional development training in an Australian workplace. Useful for upskilling franchise team members on Australian operations before deeper deployment."},
    {"id": "AU-408", "country_code": "AU", "name": "Subclass 408 — Temporary Activity",
     "type": "Temporary", "min_age": 18, "max_age": 99, "english_required": False,
     "skill_level": "Activity-specific", "company_cost_band": "AUD 350 – 800",
     "applicant_cost_band": "AUD 360 – 800",
     "duration_months": 4, "timeline_band": "1 – 3 months",
     "key_requirements": ["Sponsored by an Australian organisation (TAS)", "Specific activity: entertainment, sports, religious, research, exchange", "Up to 4 years (event-dependent)"],
     "spouse_work_rights": True,
     "summary": "Event / activity-driven temporary visa — entertainment, sports, religious work, exchange programmes, cultural exchanges. Often paired with culinary / hospitality events and franchise launches."},

    # ── USA ─────────────────────────────────────────────────────────────────
    {"id": "US-L1A", "country_code": "US", "name": "L-1A Intra-Company Transferee — Executive / Manager",
     "type": "Temporary", "min_age": 18, "max_age": 99, "english_required": False,
     "skill_level": "Executive", "company_cost_band": "USD 4,000 – 8,000",
     "applicant_cost_band": "USD 2,000 – 4,000",
     "duration_months": 5, "timeline_band": "3 – 6 months (premium ~2 weeks)",
     "key_requirements": ["1+ year as Manager/Executive abroad", "Qualifying US affiliate", "New office or existing"],
     "spouse_work_rights": True,
     "summary": "Transfer of executive / senior manager from foreign parent to US affiliate. 7-year max stay; pathway to EB-1C."},
    {"id": "US-E2", "country_code": "US", "name": "E-2 Treaty Investor",
     "type": "Temporary", "english_required": False,
     "company_cost_band": "—",
     "applicant_cost_band": "USD 3,000 – 8,000 + investment capital",
     "duration_months": 5, "timeline_band": "3 – 6 months",
     "key_requirements": ["Treaty-country nationality (India NOT a treaty country — needs alternative passport)", "Substantial investment", "Active managerial role"],
     "spouse_work_rights": True,
     "summary": "For nationals of E-2 treaty countries to direct and develop their US investment enterprise."},
    {"id": "US-EB1C", "country_code": "US", "name": "EB-1C — Multinational Manager / Executive (PR)",
     "type": "Permanent", "english_required": False,
     "company_cost_band": "USD 6,000 – 10,000",
     "applicant_cost_band": "USD 3,500 – 5,500",
     "duration_months": 14, "timeline_band": "12 – 18 months",
     "key_requirements": ["1+ year as Manager/Executive abroad", "US affiliate operating 1+ year", "Permanent role offer"],
     "spouse_work_rights": True,
     "summary": "Green Card for multinational managers / executives. Common PR path after L-1A."},
    {"id": "US-EB2NIW", "country_code": "US", "name": "EB-2 NIW — National Interest Waiver",
     "type": "Permanent", "english_required": False,
     "company_cost_band": "—",
     "applicant_cost_band": "USD 5,000 – 10,000",
     "duration_months": 14, "timeline_band": "10 – 24 months",
     "key_requirements": ["Advanced degree OR exceptional ability", "Endeavour of national importance", "Well-positioned to advance the endeavour"],
     "spouse_work_rights": True,
     "summary": "Self-petitioned Green Card for individuals whose work is of national US interest — no employer needed."},

    # ── Japan ──────────────────────────────────────────────────────────────
    {"id": "JP-BM", "country_code": "JP", "name": "Business Manager Visa",
     "type": "Temporary", "english_required": False,
     "company_cost_band": "JPY 300,000 – 600,000",
     "applicant_cost_band": "JPY 50,000 – 100,000",
     "duration_months": 5, "timeline_band": "3 – 6 months",
     "key_requirements": ["≥ JPY 5M capital OR 2 full-time employees", "Physical office in Japan", "Business plan"],
     "spouse_work_rights": True,
     "summary": "For directors / managers establishing or operating a business in Japan."},
    {"id": "JP-HSP", "country_code": "JP", "name": "Highly Skilled Professional (HSP)",
     "type": "Provisional", "english_required": False,
     "company_cost_band": "—",
     "applicant_cost_band": "JPY 50,000 – 100,000",
     "duration_months": 3, "timeline_band": "2 – 4 months",
     "key_requirements": ["70+ points (education, experience, salary, age)", "Sponsoring organisation"],
     "spouse_work_rights": True,
     "summary": "Points-based fast-track residence with PR eligibility in 1-3 years. Spouse can work."},

    # ── Belgium ────────────────────────────────────────────────────────────
    {"id": "BE-SP", "country_code": "BE", "name": "Single Permit (Work + Residence)",
     "type": "Temporary", "english_required": False,
     "company_cost_band": "EUR 200 – 600",
     "applicant_cost_band": "EUR 350 – 800",
     "duration_months": 4, "timeline_band": "3 – 5 months",
     "key_requirements": ["Belgian employer sponsor", "Salary above regional threshold", "Labour-market test (some regions)"],
     "spouse_work_rights": True,
     "summary": "Combined work + residence permit for non-EU nationals filling Belgian roles."},
    {"id": "BE-SE", "country_code": "BE", "name": "Self-Employed Professional Card",
     "type": "Temporary", "english_required": False,
     "company_cost_band": "EUR 350 – 800",
     "applicant_cost_band": "EUR 300 – 600",
     "duration_months": 6, "timeline_band": "4 – 8 months",
     "key_requirements": ["Business plan", "Financial means", "Regional approval"],
     "spouse_work_rights": False,
     "summary": "For non-EU entrepreneurs operating their own business in Belgium."},

    # ── EU general ─────────────────────────────────────────────────────────
    {"id": "EU-ICT", "country_code": "EU", "name": "EU ICT Directive — Intra-Corporate Transferee",
     "type": "Temporary", "english_required": False,
     "company_cost_band": "EUR 150 – 400",
     "applicant_cost_band": "EUR 300 – 600",
     "duration_months": 4, "timeline_band": "3 – 6 months",
     "key_requirements": ["6+ months with non-EU parent", "Manager/Specialist/Trainee", "Host EU entity"],
     "spouse_work_rights": True,
     "summary": "EU-wide directive for transferring managers / specialists / trainees within a multinational group."},
    {"id": "EU-BLUE", "country_code": "EU", "name": "EU Blue Card",
     "type": "Temporary", "english_required": False,
     "company_cost_band": "—",
     "applicant_cost_band": "EUR 140 – 600",
     "duration_months": 3, "timeline_band": "2 – 4 months",
     "key_requirements": ["University degree (3+ yrs)", "Salary ≥ 1.5× national average", "Binding job offer"],
     "spouse_work_rights": True,
     "summary": "Highly-skilled work permit valid across EU; long-term residence path."},

    # ── Singapore ──────────────────────────────────────────────────────────
    {"id": "SG-EP", "country_code": "SG", "name": "Employment Pass",
     "type": "Temporary", "english_required": False,
     "company_cost_band": "SGD 250 – 500",
     "applicant_cost_band": "SGD 250 – 500",
     "duration_months": 2, "timeline_band": "3 – 8 weeks",
     "key_requirements": ["Fixed monthly salary ≥ SGD 5,000 (higher for finance)", "Qualifying degree", "COMPASS score ≥ 40"],
     "spouse_work_rights": True,
     "summary": "Skilled-professional pass; required for foreign managers / directors / specialists."},
    {"id": "SG-EntrePass", "country_code": "SG", "name": "EntrePass",
     "type": "Temporary", "english_required": False,
     "company_cost_band": "—",
     "applicant_cost_band": "SGD 175 – 500",
     "duration_months": 3, "timeline_band": "2 – 4 months",
     "key_requirements": ["Innovative business plan", "Funding / investor backing", "Singapore-registered company"],
     "spouse_work_rights": False,
     "summary": "For foreign entrepreneurs starting and operating a Singapore-registered company."},

    # ── Australia — additional ──────────────────────────────────────────────
    {"id": "AU-DAMA", "country_code": "AU", "name": "DAMA WA — Designated Area Migration Agreement (Western Australia)",
     "type": "Provisional", "min_age": 18, "max_age": 55, "english_required": True,
     "skill_level": "Skilled", "company_cost_band": "AUD 5,000 – 8,000",
     "applicant_cost_band": "AUD 5,000 – 9,000",
     "duration_months": 5, "timeline_band": "4 – 7 months",
     "key_requirements": ["Approved DAMA WA employer", "Work in regional WA", "Occupation on the DAMA WA list", "Concessions on age/English/salary"],
     "spouse_work_rights": True,
     "summary": "WA-specific regional labour agreement with concessions on age, English and TSMIT — strong fit for hospitality / chef roles in Perth & regional WA. PR pathway via 191 after 3 years."},
    {"id": "AU-600", "country_code": "AU", "name": "Subclass 600 — Business Visitor Visa",
     "type": "Temporary", "min_age": 18, "max_age": 99, "english_required": False,
     "skill_level": "Visitor", "company_cost_band": "—",
     "applicant_cost_band": "AUD 195 – 395",
     "duration_months": 1, "timeline_band": "2 – 6 weeks",
     "key_requirements": ["Genuine short-term business activity", "No paid Australian work", "Invitation from Australian business", "Sufficient funds"],
     "spouse_work_rights": False,
     "summary": "Short business visitor visa for meetings, conferences and exploratory business activities — no paid work permitted."},

    # ── USA — additional ───────────────────────────────────────────────────
    {"id": "US-L1B", "country_code": "US", "name": "L-1B Intra-Company Transferee — Specialized Knowledge",
     "type": "Temporary", "english_required": False,
     "company_cost_band": "USD 4,000 – 8,000",
     "applicant_cost_band": "USD 2,000 – 4,000",
     "duration_months": 5, "timeline_band": "3 – 6 months (premium ~2 weeks)",
     "key_requirements": ["1+ year specialised knowledge with foreign parent", "Qualifying US affiliate", "Specialised company-specific skills"],
     "spouse_work_rights": True,
     "summary": "Transfer of specialised-knowledge employees from foreign parent to US affiliate. 5-year max stay."},
    {"id": "US-EB1", "country_code": "US", "name": "EB-1 — Priority Worker (Extraordinary Ability / Outstanding Professor / Multinational Executive)",
     "type": "Permanent", "english_required": False,
     "company_cost_band": "USD 4,000 – 8,000",
     "applicant_cost_band": "USD 4,000 – 8,000",
     "duration_months": 12, "timeline_band": "10 – 18 months",
     "key_requirements": ["Extraordinary ability OR outstanding professor OR multinational manager", "Sustained national/international acclaim", "Evidence of recognition"],
     "spouse_work_rights": True,
     "summary": "Green-card priority category for individuals of extraordinary ability or multinational managers. Faster than EB-2/3, no labour cert."},
    {"id": "US-H1B", "country_code": "US", "name": "H-1B Specialty Occupation",
     "type": "Temporary", "english_required": False,
     "company_cost_band": "USD 5,000 – 9,000",
     "applicant_cost_band": "USD 460 – 2,500",
     "duration_months": 6, "timeline_band": "Cap-subject lottery (Mar) → start Oct",
     "key_requirements": ["Speciality occupation requiring bachelor's degree", "Annual H-1B lottery (Mar)", "US employer petition + LCA"],
     "spouse_work_rights": False,
     "summary": "Speciality-occupation work visa, 6-year max stay. Lottery-subject for cap-subject filings."},
    {"id": "US-B12", "country_code": "US", "name": "B-1 / B-2 Business / Tourist Visa",
     "type": "Temporary", "english_required": False,
     "company_cost_band": "—",
     "applicant_cost_band": "USD 185",
     "duration_months": 1, "timeline_band": "2 – 8 weeks (depends on consulate)",
     "key_requirements": ["Genuine short-term business OR tourism intent", "Strong home-country ties", "No paid US work"],
     "spouse_work_rights": False,
     "summary": "Short-stay business (B-1) or tourist (B-2) visa for meetings, conferences, family visits. No employment permitted."},

    # ── Belgium — additional ────────────────────────────────────────────────
    {"id": "BE-BV", "country_code": "BE", "name": "Belgium Business Visitor Visa",
     "type": "Temporary", "english_required": False,
     "company_cost_band": "—",
     "applicant_cost_band": "EUR 80 – 200",
     "duration_months": 1, "timeline_band": "2 – 4 weeks",
     "key_requirements": ["Short-term business activity", "Invitation from Belgian/EU host", "No paid local work"],
     "spouse_work_rights": False,
     "summary": "Schengen short-stay visa for business meetings, conferences and exploratory visits across Belgium / Schengen."},
    {"id": "BE-RES", "country_code": "BE", "name": "Belgium Residence Permit (Long Stay)",
     "type": "Provisional", "english_required": False,
     "company_cost_band": "EUR 200 – 500",
     "applicant_cost_band": "EUR 200 – 500",
     "duration_months": 4, "timeline_band": "3 – 5 months",
     "key_requirements": ["Belgian residence purpose (study/work/family)", "Health insurance", "Sufficient funds"],
     "spouse_work_rights": True,
     "summary": "Long-stay residence card (D-visa + A-card). Renewable yearly, leads to long-term residence after 5 years."},

    # ── Europe — additional ────────────────────────────────────────────────
    {"id": "EU-BRP", "country_code": "EU", "name": "EU Business Residence Permit",
     "type": "Provisional", "english_required": False,
     "company_cost_band": "EUR 200 – 600",
     "applicant_cost_band": "EUR 200 – 600",
     "duration_months": 4, "timeline_band": "3 – 6 months",
     "key_requirements": ["Establish or run an EU business", "Local company registration", "Financial means"],
     "spouse_work_rights": True,
     "summary": "Country-specific business / self-employed residence permit (variants in DE, NL, FR, PT, ES, IT). Combine with a local director model."},
    {"id": "EU-INV", "country_code": "EU", "name": "EU Investor / Golden Visa (Portugal · Spain · Greece · Italy)",
     "type": "Provisional", "english_required": False,
     "company_cost_band": "—",
     "applicant_cost_band": "EUR 250,000 – 500,000 investment + processing",
     "duration_months": 5, "timeline_band": "4 – 9 months",
     "key_requirements": ["Qualifying investment (property / fund / business)", "Clean criminal record", "Health insurance"],
     "spouse_work_rights": True,
     "summary": "EU residence by investment — country-specific schemes (PT golden visa, ES investor, IT investor, GR investor)."},

    # ── United Kingdom ─────────────────────────────────────────────────────
    {"id": "UK-SW", "country_code": "UK", "name": "UK Skilled Worker Visa",
     "type": "Temporary", "min_age": 18, "max_age": 99, "english_required": True,
     "skill_level": "Skilled", "company_cost_band": "GBP 1,500 – 3,500",
     "applicant_cost_band": "GBP 2,500 – 5,500",
     "duration_months": 3, "timeline_band": "3 – 8 weeks",
     "key_requirements": ["Job offer from Home-Office licensed sponsor", "Eligible occupation code", "Salary ≥ GBP 38,700 (or going rate)", "English (B1)"],
     "spouse_work_rights": True,
     "summary": "Main UK work visa — 5-year stay, ILR after 5 years. Pathway to PR / British citizenship."},
    {"id": "UK-IF", "country_code": "UK", "name": "UK Innovator Founder Visa",
     "type": "Provisional", "min_age": 18, "max_age": 99, "english_required": True,
     "skill_level": "Business", "company_cost_band": "—",
     "applicant_cost_band": "GBP 1,500 – 3,000 + business funding",
     "duration_months": 4, "timeline_band": "3 – 6 months",
     "key_requirements": ["Innovative, viable & scalable UK business idea", "Endorsement from an Endorsing Body", "Direct involvement in business"],
     "spouse_work_rights": True,
     "summary": "For founders launching an innovative UK business. 3-year visa with direct PR pathway after 3 years."},
    {"id": "UK-EW", "country_code": "UK", "name": "UK Expansion Worker Visa (Global Business Mobility)",
     "type": "Temporary", "english_required": False,
     "company_cost_band": "GBP 1,000 – 2,500",
     "applicant_cost_band": "GBP 600 – 1,500",
     "duration_months": 3, "timeline_band": "3 – 8 weeks",
     "key_requirements": ["Senior employee setting up first UK branch", "Existing overseas business with UK expansion plan", "12+ months with foreign parent"],
     "spouse_work_rights": True,
     "summary": "For senior employees expanding a foreign business into the UK (no UK trading history yet). Up to 2-year stay."},
    {"id": "UK-DEP", "country_code": "UK", "name": "UK Dependent Visa",
     "type": "Temporary", "english_required": False,
     "company_cost_band": "—",
     "applicant_cost_band": "GBP 1,500 – 3,500 per dependent",
     "duration_months": 3, "timeline_band": "3 – 6 weeks",
     "key_requirements": ["Primary applicant on eligible work / study visa", "Proof of relationship", "Financial support"],
     "spouse_work_rights": True,
     "summary": "Partner / dependent children of UK Skilled Worker, Innovator, Expansion Worker etc."},

    # ── UAE / Dubai ────────────────────────────────────────────────────────
    {"id": "AE-GOLDEN", "country_code": "AE", "name": "UAE Golden Visa (10-Year Residence)",
     "type": "Provisional", "english_required": False,
     "company_cost_band": "—",
     "applicant_cost_band": "AED 2,800 – 9,000 (govt) + agent fees",
     "duration_months": 1, "timeline_band": "2 – 4 weeks",
     "key_requirements": ["Investor (AED 2M+ property OR business) OR outstanding talent OR senior executive OR specialist", "Clean record", "Health insurance"],
     "spouse_work_rights": True,
     "summary": "10-year renewable residence with full work + sponsorship rights. No local sponsor needed."},
    {"id": "AE-EMP", "country_code": "AE", "name": "UAE Employment Visa",
     "type": "Temporary", "english_required": False,
     "company_cost_band": "AED 3,000 – 7,000",
     "applicant_cost_band": "AED 1,000 – 3,000",
     "duration_months": 1, "timeline_band": "2 – 5 weeks",
     "key_requirements": ["UAE employer sponsorship", "Labour contract + Emirates ID", "Medical fitness"],
     "spouse_work_rights": True,
     "summary": "Standard 2-year employer-sponsored work residence. Sponsor handles labour card + EID."},
    {"id": "AE-INV", "country_code": "AE", "name": "UAE Investor / Partner Visa",
     "type": "Provisional", "english_required": False,
     "company_cost_band": "—",
     "applicant_cost_band": "AED 5,000 – 12,000 + investment",
     "duration_months": 2, "timeline_band": "4 – 8 weeks",
     "key_requirements": ["Equity stake in UAE entity (typically AED 50K+)", "Trade licence", "Approved free-zone / mainland setup"],
     "spouse_work_rights": True,
     "summary": "Investor / shareholder residence visa. 2 or 3-year terms depending on investment size."},
    {"id": "AE-PARTNER", "country_code": "AE", "name": "UAE Partner Visa",
     "type": "Temporary", "english_required": False,
     "company_cost_band": "—",
     "applicant_cost_band": "AED 5,000 – 10,000",
     "duration_months": 2, "timeline_band": "4 – 6 weeks",
     "key_requirements": ["Shareholder/partner in UAE LLC", "MOA / trade licence", "Minimum capital contribution per emirate rules"],
     "spouse_work_rights": True,
     "summary": "Partnership / shareholder visa — common for setting up Purnabramha LLC branches."},
    {"id": "AE-FAMILY", "country_code": "AE", "name": "UAE Family / Dependent Visa",
     "type": "Temporary", "english_required": False,
     "company_cost_band": "—",
     "applicant_cost_band": "AED 1,500 – 3,500 per dependent",
     "duration_months": 1, "timeline_band": "2 – 4 weeks",
     "key_requirements": ["Sponsor with min salary (AED 4-6K)", "Adequate housing", "Health insurance"],
     "spouse_work_rights": True,
     "summary": "Sponsor your spouse / children / parents under your UAE residence."},
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
    # Country-specific expansion / setup letters
    ("au_south_perth_setup", "AU — South Perth Setup Letter", "South Perth Centre Setup Confirmation", "Confirm Purnabramha's South Perth presence"),
    ("au_melbourne_expansion", "AU — Melbourne Expansion Letter", "Melbourne Expansion Plan", "Detail Melbourne expansion strategy"),
    ("au_sydney_expansion", "AU — Sydney Expansion Letter", "Sydney Expansion Plan", "Detail Sydney expansion strategy"),
    ("us_atlanta_expansion", "USA — Atlanta Expansion Letter", "Atlanta Expansion Plan", "Detail Atlanta expansion strategy"),
    ("us_dallas_expansion", "USA — Dallas Expansion Plan", "Dallas Expansion Plan", "Detail Dallas expansion strategy"),
    ("us_l1a_support", "USA — L-1A Support Letter", "L-1A Multinational Manager Support", "Support letter for L-1A petition"),
    ("us_eb1c_support", "USA — EB-1C Support Letter", "EB-1C Multinational Manager Support", "Support letter for EB-1C petition"),
    ("jp_market_entry", "JP — Japan Market Entry Note", "Japan Market Entry Strategy", "Note explaining market-entry rationale"),
    ("jp_business_expansion", "JP — Business Expansion Letter", "Business Expansion Plan for Japan", "Detail Japan expansion plan"),
    ("be_single_permit_justification", "BE — Single Permit Justification", "Single Permit Justification", "Justify need for Single Permit hire"),
    ("be_local_entity_requirement", "BE — Local Entity Requirement Note", "Belgium Local Entity Requirement", "Confirm Belgian entity status"),
    ("sg_ep_support", "SG — Employment Pass Support Letter", "Employment Pass Support", "Support letter for EP application"),
    ("sg_entrepass_plan", "SG — EntrePass Business Plan Summary", "EntrePass Business Plan Summary", "Summary of EntrePass business plan"),
    # General-purpose extended letters (added per founder spec 2026-02-18)
    ("invitation_letter", "Invitation Letter", "Invitation to Visit / Work", "Formal invitation from host entity"),
    ("genuine_position", "Genuine Position Letter", "Genuine Position Justification", "Prove the role is genuine and operationally needed (Australia 482 / 186)"),
    ("training_plan", "Training Plan", "Structured Training Plan", "Workplace-based training plan (AU 407, US H-1B trainee)"),
    ("investor_proposal", "Investor Proposal", "Investor Proposal & Business Case", "Investor visa narrative (US E-2, UK Innovator, UAE Golden)"),
    ("business_plan", "Business Plan", "Business Plan Summary", "Full business plan summary for investor / innovator visas"),
    ("shareholding_certificate", "Shareholding Certificate", "Certificate of Shareholding", "Formal shareholding certificate signed by company secretary"),
    ("cost_summary", "Cost & Timeline Summary", "Visa Cost & Timeline Summary", "One-page summary of all fees & expected timelines"),
    ("risk_analysis", "Risk Analysis Note", "Risk Analysis & Mitigations", "Internal risk analysis for the chosen pathway"),
]

_DEFAULT_ENTITIES = [
    {"id": "ENT-IN", "name": "Manaswini Foods Pvt. Ltd.",
     "country_code": "IN", "registration_number": "U15549MH2014PTC257421",
     "address": "Hinjewadi, Pune, Maharashtra, India",
     "is_parent": True, "notes": "Indian parent company."},
    {"id": "ENT-AU", "name": "Purnabramha Australia Pty Ltd",
     "country_code": "AU", "registration_number": "",
     "address": "South Perth, Western Australia, Australia",
     "is_parent": False, "notes": "Australian subsidiary."},
    {"id": "ENT-US", "name": "Purnabramha USA LLC",
     "country_code": "US", "registration_number": "",
     "address": "Atlanta, Georgia, USA",
     "is_parent": False, "notes": "US subsidiary."},
    {"id": "ENT-JP", "name": "Purnabramha Japan KK",
     "country_code": "JP", "registration_number": "",
     "address": "Tokyo, Japan",
     "is_parent": False, "notes": "Japan subsidiary."},
    {"id": "ENT-BE", "name": "Purnabramha Belgium SRL",
     "country_code": "BE", "registration_number": "",
     "address": "Brussels, Belgium",
     "is_parent": False, "notes": "Belgium subsidiary."},
    {"id": "ENT-SG", "name": "Purnabramha Singapore Pte Ltd",
     "country_code": "SG", "registration_number": "",
     "address": "Singapore",
     "is_parent": False, "notes": "Singapore subsidiary."},
    {"id": "ENT-UK", "name": "Purnabramha UK Ltd",
     "country_code": "UK", "registration_number": "",
     "address": "London, United Kingdom",
     "is_parent": False, "notes": "UK subsidiary."},
    {"id": "ENT-AE", "name": "Purnabramha LLC (UAE)",
     "country_code": "AE", "registration_number": "",
     "address": "Dubai, United Arab Emirates",
     "is_parent": False, "notes": "UAE / Dubai subsidiary."},
]

_DEFAULT_SIGNATORIES = [
    {"id": "SIG-JK", "name": "Jayanti Kathale", "role": "Founder & Managing Director",
     "entity_id": "ENT-IN", "email": "jayanti@purnabramha.com", "phone": ""},
    {"id": "SIG-SK", "name": "Sandeep Kathale", "role": "Director — Global Operations",
     "entity_id": "ENT-IN", "email": "sandeep@purnabramha.com", "phone": ""},
    {"id": "SIG-LOCAL", "name": "Local Director (to be assigned)", "role": "Local Director",
     "entity_id": "", "email": "", "phone": ""},
    {"id": "SIG-CS", "name": "Company Secretary", "role": "Company Secretary",
     "entity_id": "ENT-IN", "email": "", "phone": ""},
]


async def _ensure_seeds():
    """Idempotent upsert-style seeding.

    Each row is upserted by its primary key (`code` for countries, `id` elsewhere),
    so re-running this on a populated production DB *fills gaps* (e.g. newly added
    pathways for AU-494 / Global Talent) without creating duplicates.

    A separate cleanup pass deletes any duplicate rows that may have been
    accidentally inserted in earlier deploys.
    """
    if _db is None:
        return

    # Defensive cleanup: collapse duplicates by primary key, keeping the oldest.
    await _cleanup_duplicates_internal()

    # Upsert seeds (idempotent).
    # For human-editable rows ($setOnInsert) admins can rename/tweak without our overrides clobbering.
    # For machine-readable config fields we $set them on _seed rows so newly-added fields backfill.
    for c in _SEED_COUNTRIES:
        await _db.visa_countries.update_one(
            {"code": c["code"]},
            {
                "$setOnInsert": {"_seed": True, "created_at": _now_iso()},
                "$set": {k: v for k, v in c.items() if k != "code"},
            },
            upsert=True,
        )
    _PATHWAY_MACHINE_FIELDS = (
        "country_code", "type", "min_age", "max_age", "english_required",
        "skill_level", "company_cost_band", "applicant_cost_band", "duration_months",
        "timeline_band", "key_requirements", "spouse_work_rights",
    )
    for p in _SEED_PATHWAYS:
        machine = {k: p[k] for k in _PATHWAY_MACHINE_FIELDS if k in p}
        await _db.visa_pathways.update_one(
            {"id": p["id"]},
            {
                "$setOnInsert": {
                    "_seed": True, "created_at": _now_iso(),
                    "name": p["name"], "summary": p.get("summary", ""),
                },
                "$set": machine,
            },
            upsert=True,
        )
    for (k, n, s, p) in _DEFAULT_LETTER_TYPES:
        await _db.visa_letter_templates.update_one(
            {"id": k},
            {"$setOnInsert": {
                "id": k, "name": n, "subject": s, "purpose": p,
                "body_template": f"[{n} — body will be AI-generated using applicant + company context]",
                "_seed": True, "created_at": _now_iso(),
            }},
            upsert=True,
        )
    for e in _DEFAULT_ENTITIES:
        await _db.visa_entities.update_one(
            {"id": e["id"]},
            {"$setOnInsert": {**e, "_seed": True, "created_at": _now_iso()}},
            upsert=True,
        )
    for s in _DEFAULT_SIGNATORIES:
        await _db.visa_signatories.update_one(
            {"id": s["id"]},
            {"$setOnInsert": {**s, "_seed": True, "created_at": _now_iso()}},
            upsert=True,
        )


async def _cleanup_duplicates_internal() -> dict:
    """Remove duplicate rows (same primary key) across all visa collections."""
    if _db is None:
        return {}
    removed = {}
    plans = [
        ("visa_countries", "code"),
        ("visa_pathways", "id"),
        ("visa_letter_templates", "id"),
        ("visa_entities", "id"),
        ("visa_signatories", "id"),
    ]
    for coll, key in plans:
        seen = set()
        dup_ids = []
        async for doc in _db[coll].find({}, sort=[("created_at", 1)]):
            k = doc.get(key)
            if k in seen:
                dup_ids.append(doc["_id"])
            else:
                seen.add(k)
        if dup_ids:
            res = await _db[coll].delete_many({"_id": {"$in": dup_ids}})
            removed[coll] = res.deleted_count
    return removed


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
    return {"success": True, "countries": _dedupe_by(docs, "code")}


@router.get("/pathways")
async def list_pathways(token: str = Query(...), country_code: Optional[str] = Query(None)):
    await _auth(token)
    await _ensure_seeds()
    q = {"country_code": country_code} if country_code else {}
    docs = await _db.visa_pathways.find(q, {"_id": 0}).sort("name", 1).to_list(None)
    return {"success": True, "pathways": _dedupe_by(docs, "id")}


@router.get("/letter-templates")
async def list_letter_templates(token: str = Query(...)):
    await _auth(token)
    await _ensure_seeds()
    docs = await _db.visa_letter_templates.find({}, {"_id": 0}).sort("name", 1).to_list(None)
    return {"success": True, "templates": _dedupe_by(docs, "id")}


@router.get("/entities")
async def list_entities(token: str = Query(...)):
    await _auth(token)
    await _ensure_seeds()
    docs = await _db.visa_entities.find({}, {"_id": 0}).sort("name", 1).to_list(None)
    return {"success": True, "entities": _dedupe_by(docs, "id")}


@router.get("/signatories")
async def list_signatories(token: str = Query(...)):
    await _auth(token)
    await _ensure_seeds()
    docs = await _db.visa_signatories.find({}, {"_id": 0}).sort("name", 1).to_list(None)
    return {"success": True, "signatories": _dedupe_by(docs, "id")}


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
    is_admin = bool(sess.get("is_super_admin") or sess.get("is_admin"))
    role = (sess.get("role") or sess.get("role_key") or "").lower()
    if not is_admin and role not in ("super_admin", "superadmin", "founder", "director", "admin"):
        q = {"owner_user": sess.get("mobile") or sess.get("email") or "unknown"}
    else:
        q = {}
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
async def delete_application(
    aid: str,
    token: str = Query(...),
    hard: bool = Query(False, description="Super-admin only — permanently remove"),
):
    """Soft delete by default (status='archived'). Super Admin may pass hard=true to permanently remove."""
    sess = await _auth(token)
    doc = await _db.visa_applications.find_one({"application_id": aid}, {"_id": 0, "status": 1})
    if not doc:
        raise HTTPException(404, "Application not found")
    if hard:
        is_admin = bool(sess.get("is_super_admin") or sess.get("is_admin"))
        if not is_admin:
            raise HTTPException(403, "Permanent delete is restricted to Super Admin")
        await _db.visa_applications.delete_one({"application_id": aid})
        return {"success": True, "mode": "hard"}
    # Soft delete
    await _db.visa_applications.update_one(
        {"application_id": aid},
        {"$set": {
            "status": "archived",
            "archived_at": _now_iso(),
            "archived_by": sess.get("mobile") or sess.get("email") or "system",
            "updated_at": _now_iso(),
        }},
    )
    return {"success": True, "mode": "soft", "status": "archived"}


@router.post("/application/{aid}/restore")
async def restore_application(aid: str, req: _TokenReq = Body(...)):
    """Restore an archived application back to its prior status."""
    await _auth(req.token)
    res = await _db.visa_applications.update_one(
        {"application_id": aid, "status": "archived"},
        {"$set": {"status": "draft", "updated_at": _now_iso()},
         "$unset": {"archived_at": "", "archived_by": ""}},
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Archived application not found")
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

    # Background-job pattern: a 15-letter Sonnet 4.5 batch can take 30-90s and
    # will get killed by the 60s production ingress timeout. We therefore kick
    # off the LLM work as an asyncio.create_task and return immediately. The
    # frontend polls /letter-status until status == 'done'.
    import asyncio

    job_id = uuid.uuid4().hex[:10]
    started_at = _now_iso()
    await _db.visa_applications.update_one(
        {"application_id": aid},
        {"$set": {
            "letters_job": {
                "job_id": job_id,
                "status": "running",
                "started_at": started_at,
                "completed_at": None,
                "total": len(templates_to_run),
                "drafted_count": 0,
                "scope": req.scope,
                "letter_keys": [t["id"] for t in templates_to_run],
            },
            "updated_at": started_at,
        }},
    )

    async def _draft_one(t: dict) -> dict:
        """Run the (sync-under-the-hood) LLM call in a thread pool so multiple
        letters truly process in parallel — the emergentintegrations client
        blocks the event loop, so a plain asyncio.gather wouldn't parallelize."""
        loop = asyncio.get_event_loop()

        def _call_llm() -> str:
            chat = LlmChat(
                api_key=api_key,
                session_id=f"visa-letter-{aid}-{t['id']}-{uuid.uuid4().hex[:6]}",
                system_message=_LETTER_SYSTEM_PROMPT,
            ).with_model("anthropic", "claude-sonnet-4-5-20250929")
            user_text = _build_letter_prompt(t, app_doc, sig, ent, country_doc)
            # send_message is awaitable but underneath uses a sync HTTP client
            # via litellm — wrap in asyncio.run to drive it inside the thread.
            return asyncio.run(chat.send_message(UserMessage(text=user_text))) or ""

        try:
            body_text = await asyncio.wait_for(
                loop.run_in_executor(None, _call_llm),
                timeout=90,
            )
            body_text = (body_text or "").strip()
            return {
                "letter_key": t["id"], "letter_name": t["name"], "subject": t["subject"],
                "purpose": t["purpose"], "body": body_text, "status": "Drafted",
                "signed_by": sig.get("name"), "entity_name": ent.get("name"),
                "country": country_doc.get("name"), "generated_at": _now_iso(),
            }
        except asyncio.TimeoutError:
            logger.warning(f"visa: letter {t['id']} timed out after 90s")
            return {
                "letter_key": t["id"], "letter_name": t["name"], "subject": t["subject"],
                "purpose": t["purpose"],
                "body": "[Auto-generation timed out — click Regenerate to retry just this letter.]",
                "status": "Pending", "signed_by": sig.get("name"),
                "entity_name": ent.get("name"), "country": country_doc.get("name"),
            }
        except Exception as ex:
            logger.warning(f"visa: letter {t['id']} failed: {ex}")
            return {
                "letter_key": t["id"], "letter_name": t["name"], "subject": t["subject"],
                "purpose": t["purpose"], "body": f"[Auto-generation failed: {ex}]",
                "status": "Pending", "signed_by": sig.get("name"),
                "entity_name": ent.get("name"), "country": country_doc.get("name"),
            }

    async def _run_batch():
        try:
            drafted = await asyncio.gather(*[_draft_one(t) for t in templates_to_run])
            # Merge with any previously-drafted letters not in this batch
            doc = await _db.visa_applications.find_one({"application_id": aid}, {"_id": 0}) or {}
            existing = doc.get("letters") or []
            by_key = {l["letter_key"]: l for l in existing}
            for d in drafted:
                by_key[d["letter_key"]] = d
            merged = list(by_key.values())
            drafted_count = sum(1 for d in drafted if d.get("status") == "Drafted")
            await _db.visa_applications.update_one(
                {"application_id": aid},
                {"$set": {
                    "letters": merged,
                    "status": "letters_generated",
                    "letters_job.status": "done",
                    "letters_job.completed_at": _now_iso(),
                    "letters_job.drafted_count": drafted_count,
                    "updated_at": _now_iso(),
                }},
            )
        except Exception as ex:
            logger.exception(f"visa: letters batch failed: {ex}")
            await _db.visa_applications.update_one(
                {"application_id": aid},
                {"$set": {
                    "letters_job.status": "error",
                    "letters_job.error": str(ex),
                    "letters_job.completed_at": _now_iso(),
                    "updated_at": _now_iso(),
                }},
            )

    asyncio.create_task(_run_batch())
    return {
        "success": True,
        "job_id": job_id,
        "status": "running",
        "total": len(templates_to_run),
        "message": "Letter generation started — poll /letter-status for progress.",
    }


@router.get("/application/{aid}/letter-status")
async def letter_status(aid: str, token: str = Query(...)):
    """Poll for background letter-generation progress."""
    await _auth(token)
    doc = await _db.visa_applications.find_one(
        {"application_id": aid},
        {"_id": 0, "letters": 1, "letters_job": 1},
    )
    if not doc:
        raise HTTPException(404, "Application not found")
    job = doc.get("letters_job") or {}
    letters = doc.get("letters") or []
    return {
        "success": True,
        "job": job,
        "letters": letters,
        "status": job.get("status", "idle"),
        "drafted_count": job.get("drafted_count", 0),
        "total": job.get("total", 0),
    }


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



# ─────────────────────────────────────────────────────────────────────────────
# Send to Immigration Lawyer — curated bundle with cover letter + preview
# ─────────────────────────────────────────────────────────────────────────────
def _safe_name(s: str) -> str:
    return "".join(c for c in (s or "") if c.isalnum() or c in "._- ").replace(" ", "_")


def _lawyer_cover_pdf_bytes(app_doc: dict, country: dict, ent: dict, sig: dict,
                            lawyer_name: str, lawyer_firm: str, notes: str) -> bytes:
    """Generates a polished, lawyer-facing cover letter PDF."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    styles = getSampleStyleSheet()
    title = ParagraphStyle("T", parent=styles["Heading1"], fontSize=16,
                           textColor=colors.HexColor("#800020"))
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=11,
                        textColor=colors.HexColor("#1a365d"))
    body = ParagraphStyle("B", parent=styles["Normal"], fontSize=10, leading=14)
    small = ParagraphStyle("S", parent=body, fontSize=8, textColor=colors.grey)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm,
                            topMargin=18*mm, bottomMargin=18*mm)

    applicant = app_doc.get("applicant") or {}
    business = app_doc.get("business") or {}
    report = app_doc.get("report") or {}
    letters = app_doc.get("letters") or []
    today = datetime.now().strftime("%d %B %Y")

    story = [
        Paragraph(ent.get("name", "Purnabramha"), title),
        Paragraph(ent.get("address", ""), small),
        Spacer(1, 6),
        Paragraph(today, body),
        Spacer(1, 10),
        Paragraph(
            f"To,<br/>"
            f"<b>{lawyer_name or 'The Immigration Counsel'}</b><br/>"
            f"{lawyer_firm or ''}",
            body,
        ),
        Spacer(1, 10),
        Paragraph(
            f"<b>Subject: Visa Application Bundle — {applicant.get('name', '—')} "
            f"for {country.get('name', '—')}</b>",
            body,
        ),
        Spacer(1, 8),
        Paragraph("Dear Counsel,", body),
        Paragraph(
            "Please find enclosed the complete preparation bundle for the above-named "
            "applicant. This pack has been compiled internally by Purnabramha as a "
            "starting point and is intended for your professional review before any "
            "filing or lodgement with the relevant immigration authority.",
            body,
        ),
        Spacer(1, 6),

        Paragraph("Applicant Snapshot", h2),
        Paragraph(
            f"• <b>Name:</b> {applicant.get('name', '—')}<br/>"
            f"• <b>Age:</b> {applicant.get('age', '—')} &nbsp;&nbsp; "
            f"<b>Nationality:</b> {applicant.get('nationality', '—')}<br/>"
            f"• <b>Total experience:</b> {applicant.get('years_of_experience', '—')} years<br/>"
            f"• <b>Current role:</b> {applicant.get('current_role', '—')}<br/>"
            f"• <b>English test status:</b> {applicant.get('english_test_status', '—')} "
            f"{('('+applicant.get('english_test_score','')+')') if applicant.get('english_test_score') else ''}<br/>"
            f"• <b>Family included:</b> {'Yes' if applicant.get('family_included') else 'No'}",
            body,
        ),
        Spacer(1, 6),

        Paragraph("Proposed Role", h2),
        Paragraph(
            f"• <b>Role offered:</b> {business.get('role_offered', '—')}<br/>"
            f"• <b>Proposed salary:</b> {business.get('proposed_salary', '—')}<br/>"
            f"• <b>Proposed start:</b> {business.get('proposed_start_date', '—')}<br/>"
            f"• <b>Centre / branch:</b> {business.get('proposed_centre', '—')}<br/>"
            f"• <b>Signing entity:</b> {ent.get('name', '—')}<br/>"
            f"• <b>Authorised signatory:</b> {sig.get('name', '—')} ({sig.get('role', '—')})",
            body,
        ),
        Spacer(1, 6),

        Paragraph("Internal Readiness Assessment", h2),
        Paragraph(
            f"• <b>Suitability:</b> {report.get('suitability', '—')} "
            f"({report.get('score', 0)}/100)<br/>"
            f"• <b>Top pathway match:</b> "
            f"{(report.get('ranked_pathways') or [{}])[0].get('pathway', {}).get('name', '—')}<br/>"
            f"• <b>Estimated end-to-end timeline:</b> "
            f"{report.get('estimated_timeline', '—')} months",
            body,
        ),
        Spacer(1, 6),
    ]

    risks = report.get("risks") or []
    if risks:
        story.append(Paragraph("Open Risks to Address", h2))
        for r in risks[:8]:
            story.append(Paragraph(f"• {r}", body))
        story.append(Spacer(1, 6))

    story += [
        Paragraph("Contents of This Bundle", h2),
        Paragraph(
            "1. <b>00_COVER_LETTER_TO_LAWYER.pdf</b> — this cover letter<br/>"
            "2. <b>01_Visa_Readiness_Report.pdf</b> — full internal assessment "
            "(suitability, ranked pathways, document checklist, cost heads, next steps)<br/>"
            "3. <b>02_Letter_Checklist.xlsx</b> — tabular checklist of every supporting letter<br/>"
            f"4. <b>03_Letters/</b> — {len(letters)} AI-drafted supporting letters in Word "
            "format (each ready for signatory review &amp; signature)<br/>"
            "5. <b>99_manifest.txt</b> — machine-readable manifest of the bundle",
            body,
        ),
        Spacer(1, 8),
    ]

    if notes:
        story += [
            Paragraph("Specific Notes / Requests From Purnabramha", h2),
            Paragraph(notes.replace("\n", "<br/>"), body),
            Spacer(1, 6),
        ]

    story += [
        Paragraph(
            "We would be grateful if you could (a) confirm the most appropriate visa "
            "pathway for this case, (b) flag any gaps in the documents or letters provided, "
            "and (c) advise on next steps and your engagement terms.",
            body,
        ),
        Spacer(1, 10),
        Paragraph("With kind regards,", body),
        Spacer(1, 8),
        Paragraph(f"<b>{sig.get('name', '—')}</b>", body),
        Paragraph(sig.get("role", "—"), body),
        Paragraph(ent.get("name", "—"), body),
        Spacer(1, 12),
        Paragraph(
            "Disclaimer: This bundle is an internal preparation pack only. Final visa "
            "strategy, eligibility and lodgement remain subject to your professional "
            "advice and the laws of the destination country.",
            small,
        ),
    ]
    doc.build(story)
    return buf.getvalue()


class _LawyerBundleReq(BaseModel):
    token: str
    lawyer_name: Optional[str] = ""
    lawyer_firm: Optional[str] = ""
    notes: Optional[str] = ""


@router.post("/application/{aid}/lawyer-bundle-preview")
async def lawyer_bundle_preview(aid: str, req: _LawyerBundleReq = Body(...)):
    """Return the list of files (no bytes) that will be included in the lawyer bundle."""
    await _auth(req.token)
    app_doc = await _db.visa_applications.find_one({"application_id": aid}, {"_id": 0})
    if not app_doc:
        raise HTTPException(404, "Application not found")

    letters = app_doc.get("letters") or []
    has_report = bool(app_doc.get("report"))
    plan_rows = len(((app_doc.get("report") or {}).get("signatory_letter_plan")) or [])

    files = [
        {"order": "00", "name": "00_COVER_LETTER_TO_LAWYER.pdf",
         "kind": "PDF", "description": "Professional cover letter addressed to the immigration counsel."},
    ]
    if has_report:
        files.append({"order": "01", "name": "01_Visa_Readiness_Report.pdf",
                      "kind": "PDF", "description": "Full internal readiness assessment with ranked pathways and document checklists."})
    files.append({"order": "02", "name": "02_Letter_Checklist.xlsx",
                  "kind": "Excel", "description": f"Tabular checklist of all {plan_rows or len(letters) or '—'} supporting letters."})
    for i, lt in enumerate(letters, 1):
        files.append({
            "order": f"03.{i:02d}",
            "name": f"03_Letters/{_safe_name(lt.get('letter_name', 'letter'))}.docx",
            "kind": "Word",
            "description": lt.get("subject") or lt.get("letter_name", ""),
        })
    files.append({"order": "99", "name": "99_manifest.txt",
                  "kind": "Text", "description": "Machine-readable manifest of the bundle."})

    warnings = []
    if not has_report:
        warnings.append("Readiness report has not been generated yet — bundle will still be created but without `01_Visa_Readiness_Report.pdf`.")
    if not letters:
        warnings.append("No AI letters drafted yet — bundle will not include `03_Letters/*.docx`. Generate letters first for a complete pack.")

    return {
        "success": True,
        "application_id": aid,
        "file_count": len(files),
        "files": files,
        "warnings": warnings,
        "applicant_name": (app_doc.get("applicant") or {}).get("name"),
        "country_code": app_doc.get("country_code"),
    }


@router.post("/application/{aid}/lawyer-bundle")
async def lawyer_bundle(aid: str, req: _LawyerBundleReq = Body(...)):
    """One-click curated ZIP for the immigration lawyer: cover letter + report + checklist + letters + manifest."""
    await _auth(req.token)
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
        # 00 — cover letter
        zf.writestr(
            "00_COVER_LETTER_TO_LAWYER.pdf",
            _lawyer_cover_pdf_bytes(app_doc, country, ent, sig,
                                    req.lawyer_name or "", req.lawyer_firm or "",
                                    req.notes or ""),
        )

        # 01 — readiness report (if present)
        if app_doc.get("report"):
            zf.writestr("01_Visa_Readiness_Report.pdf",
                        _report_pdf_bytes(app_doc, country, ent, sig))

        # 02 — checklist Excel
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
            zf.writestr("02_Letter_Checklist.xlsx", xb.getvalue())
        except Exception as ex:
            logger.warning(f"lawyer-bundle: checklist failed: {ex}")

        # 03 — letters
        for letter in app_doc.get("letters") or []:
            blob = _word_bytes(
                letter["letter_name"], letter.get("body", ""),
                sig.get("name", "—"), sig.get("role", "—"), ent.get("name", "—"),
            )
            zf.writestr(f"03_Letters/{_safe_name(letter['letter_name'])}.docx", blob)

        # 99 — manifest
        manifest = (
            f"PURNABRAMHA — IMMIGRATION LAWYER BUNDLE\n"
            f"========================================\n"
            f"Application: {aid}\n"
            f"Country: {country.get('name', '—')} ({country.get('code', '—')})\n"
            f"Applicant: {(app_doc.get('applicant') or {}).get('name', '—')}\n"
            f"Entity: {ent.get('name', '—')}\n"
            f"Signatory: {sig.get('name', '—')} ({sig.get('role', '—')})\n"
            f"Addressed to: {req.lawyer_name or '—'} / {req.lawyer_firm or '—'}\n"
            f"Generated: {_now_iso()}\n"
            f"\nContents:\n"
            f"  00_COVER_LETTER_TO_LAWYER.pdf  — cover letter to immigration counsel\n"
            f"  01_Visa_Readiness_Report.pdf   — internal readiness assessment\n"
            f"  02_Letter_Checklist.xlsx       — supporting letter checklist\n"
            f"  03_Letters/*.docx              — {len(app_doc.get('letters') or [])} drafted supporting letters\n"
            f"  99_manifest.txt                — this file\n"
            f"\nDisclaimer: Internal preparation pack only. Final visa strategy and "
            f"lodgement remain subject to professional advice and applicable laws.\n"
        )
        zf.writestr("99_manifest.txt", manifest)

    # Audit trail: persist who/when the bundle was generated
    await _db.visa_applications.update_one(
        {"application_id": aid},
        {"$set": {
            "lawyer_dispatch": {
                "lawyer_name": req.lawyer_name or "",
                "lawyer_firm": req.lawyer_firm or "",
                "notes": req.notes or "",
                "generated_at": _now_iso(),
            },
            "status": "lawyer_bundle_ready",
            "updated_at": _now_iso(),
        }},
    )

    applicant_safe = _safe_name((app_doc.get("applicant") or {}).get("name") or "Applicant")
    fname = f"PB_VisaBundle_{applicant_safe}_{country.get('code','XX')}_{aid}.zip"
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Admin: cleanup duplicates (one-shot migration for production DB)
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/admin/cleanup-duplicates")
async def admin_cleanup_duplicates(req: _TokenReq = Body(...)):
    await _require_admin(req.token)
    removed = await _cleanup_duplicates_internal()
    return {"success": True, "removed": removed}


# ─────────────────────────────────────────────────────────────────────────────
# AI Recommendation Engine (rules + Claude Sonnet 4.5 narrative)
# ─────────────────────────────────────────────────────────────────────────────
class _RecommendReq(BaseModel):
    token: str
    applicant_name: str = ""
    current_role: str = ""
    age: Optional[int] = None
    years_of_experience: Optional[int] = None
    nationality: Optional[str] = "Indian"
    english_status: Optional[str] = "Not Started"   # Not Started / Booked / Passed / Exempt
    family_included: bool = False
    spouse_work_rights_required: bool = False
    shareholding_pct: Optional[float] = None        # in destination entity
    has_existing_operations: bool = False           # company already operating in country
    has_expansion_plan: bool = False
    has_business_plan: bool = False
    has_financial_proof: bool = False
    has_franchise_letter: bool = False
    has_skills_assessment: bool = False
    goal: Optional[str] = ""                         # e.g. "PR + family" / "Temporary" / "Investor"
    country_codes: Optional[List[str]] = None        # shortlist; None = all
    use_ai_narrative: bool = True                    # if False → pure rule output, no LLM


def _score_pathway(p: dict, r: _RecommendReq) -> dict:
    """Pure-rule fit score (0-100) + reasons + risks for one pathway."""
    score = 50
    reasons: List[str] = []
    risks: List[str] = []

    age = r.age or 0
    yoe = r.years_of_experience or 0
    role = (r.current_role or "").lower()

    # Age window
    if p.get("min_age") and p.get("max_age"):
        if age and p["min_age"] <= age <= p["max_age"]:
            score += 8; reasons.append(f"Within age window ({p['min_age']}-{p['max_age']})")
        elif age:
            score -= 25; risks.append(f"Outside age window ({p['min_age']}-{p['max_age']})")

    # Experience
    if yoe >= 10:
        score += 12; reasons.append(f"Strong experience ({yoe} years)")
    elif yoe >= 5:
        score += 6
    elif yoe and yoe < 3:
        score -= 8; risks.append("Limited experience (<3 years)")

    # Seniority match
    skill = (p.get("skill_level") or "").lower()
    if skill in ("executive", "exceptional") and any(k in role for k in ["director", "managing", "ceo", "founder", "vp", "head"]):
        score += 14; reasons.append("Senior leadership role matches pathway seniority")
    if skill == "business" and (r.shareholding_pct or 0) > 0:
        score += 8; reasons.append("Has shareholding stake in destination business")

    # English
    if p.get("english_required"):
        if r.english_status == "Passed":
            score += 8; reasons.append("English test already passed")
        elif r.english_status == "Booked":
            score += 2
        elif r.english_status == "Exempt":
            score += 6; reasons.append("Eligible for English exemption")
        else:
            score -= 15; risks.append("English test not started — required for this pathway")

    # Operations / expansion / docs
    if r.has_existing_operations:
        score += 10; reasons.append("Existing operations in country strengthen the case")
    if r.has_expansion_plan:
        score += 5; reasons.append("Expansion plan available")
    if r.has_business_plan:
        score += 4; reasons.append("Business plan ready")
    if r.has_financial_proof:
        score += 4; reasons.append("Financial proof available")
    if r.has_franchise_letter:
        score += 4; reasons.append("Franchise support letter available")

    # Family & spouse rights
    if r.family_included and p.get("spouse_work_rights") is True:
        score += 6; reasons.append("Family included — spouse gets unrestricted work rights")
    if r.family_included and p.get("spouse_work_rights") is False:
        risks.append("Spouse work rights restricted on this pathway")

    # E-2 treaty India exclusion
    if p.get("id") == "US-E2" and (r.nationality or "").lower() in ("indian", "india"):
        score -= 30; risks.append("India is NOT an E-2 treaty country — needs alternative passport")

    # Skills assessment for AU skilled streams
    if p.get("country_code") == "AU" and p.get("id") in ("AU-186", "AU-482", "AU-494") and not r.has_skills_assessment:
        risks.append("Skills assessment required and not yet completed")

    # Goal preference
    goal = (r.goal or "").lower()
    if "pr" in goal or "permanent" in goal:
        if p.get("type") == "Permanent":
            score += 10; reasons.append("Direct PR pathway aligns with stated goal")
        elif p.get("type") == "Temporary":
            score -= 5; risks.append("Temporary only — PR via subsequent step")
    if "invest" in goal and p.get("skill_level") == "Business":
        score += 8; reasons.append("Investor / business pathway aligns with goal")
    # Short-stay / event keywords — boost activity & specialist visas
    short_keywords = ["event", "events", "festival", "launch", "training",
                       "short", "short-stay", "short stay", "specific event",
                       "specialist", "activity", "temporary stay", "few months",
                       "specialised", "specialized"]
    is_short_goal = any(k in goal for k in short_keywords)
    is_short_pathway = p.get("id") in ("AU-400", "AU-407", "AU-408")
    if is_short_goal and is_short_pathway:
        score += 22
        reasons.append("Short-stay / event-driven goal directly matches this activity visa")
    elif is_short_goal and p.get("type") == "Permanent":
        score -= 8
        risks.append("Permanent pathway over-shoots a short-stay/event goal")

    score = max(0, min(100, score))
    return {
        "pathway": p,
        "score": score,
        "suitability": "Strong" if score >= 75 else "Medium" if score >= 55 else "Low",
        "reasons": reasons,
        "risks": risks,
    }


async def _llm_enrich_narratives(req: _RecommendReq, top: List[dict]) -> List[dict]:
    """Add a short 2-3 sentence AI rationale to each top pathway.

    Runs all 5 LLM calls in parallel via a thread pool — emergentintegrations
    is sync-under-the-hood, so plain asyncio.gather wouldn't parallelize.
    Per-call 25s timeout; one slow call cannot block the others. Total wall
    time ~25-30s, well under the production 60s ingress timeout.
    """
    if not req.use_ai_narrative or not top:
        return top
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return top
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
    except Exception:
        return top

    import asyncio

    applicant_summary = (
        f"Applicant: {req.applicant_name or '—'}, role={req.current_role or '—'}, "
        f"age={req.age or '?'}, experience={req.years_of_experience or '?'} yrs, "
        f"nationality={req.nationality}, family={'yes' if req.family_included else 'no'}, "
        f"shareholding={req.shareholding_pct or 0}%, goal={req.goal or '—'}, "
        f"existing_operations={req.has_existing_operations}, expansion_plan={req.has_expansion_plan}"
    )

    def _enrich_sync(item: dict) -> str:
        p = item["pathway"]
        chat = LlmChat(
            api_key=api_key,
            session_id=f"visa-rec-{p['id']}-{uuid.uuid4().hex[:6]}",
            system_message=(
                "You are a senior immigration strategist for Purnabramha (Indian franchise group). "
                "Be concise and factual. Output 2-3 sentences only, no preamble."
            ),
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        prompt = (
            f"In 2-3 sentences, explain WHY pathway '{p['name']}' (country {p['country_code']}) "
            f"is a {item['suitability'].lower()}-fit (score {item['score']}/100) for this applicant. "
            f"Be specific and reference 1-2 strongest factors and 1 risk if relevant. "
            f"Do not use bullet points.\n\nApplicant: {applicant_summary}\n"
            f"Pathway summary: {p.get('summary', '')}\n"
            f"Key requirements: {', '.join(p.get('key_requirements') or [])}"
        )
        # send_message returns a coroutine — drive it in this thread.
        return asyncio.run(chat.send_message(UserMessage(text=prompt))) or ""

    async def _wrap(item: dict) -> None:
        loop = asyncio.get_event_loop()
        try:
            text = await asyncio.wait_for(
                loop.run_in_executor(None, _enrich_sync, item),
                timeout=35,
            )
            item["ai_rationale"] = (text or "").strip()
        except asyncio.TimeoutError:
            item["ai_rationale"] = ""
            logger.warning(f"visa recommender: narrative timed out for {item['pathway']['id']}")
        except Exception as ex:
            item["ai_rationale"] = ""
            logger.warning(f"visa recommender: narrative failed for {item['pathway']['id']}: {ex}")

    await asyncio.gather(*[_wrap(it) for it in top])
    return top


@router.post("/recommend")
async def recommend(req: _RecommendReq = Body(...)):
    """Compare all available pathways against applicant profile, rank by fit."""
    await _auth(req.token)
    await _ensure_seeds()

    q = {}
    if req.country_codes:
        q["country_code"] = {"$in": req.country_codes}
    pathways = await _db.visa_pathways.find(q, {"_id": 0}).to_list(None)
    pathways = _dedupe_by(pathways, "id")
    if not pathways:
        raise HTTPException(404, "No pathways available for the selected countries")

    scored = [_score_pathway(p, req) for p in pathways]
    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:5]
    top = await _llm_enrich_narratives(req, top)

    all_country_codes = sorted({p["country_code"] for p in pathways})
    country_docs = await _db.visa_countries.find(
        {"code": {"$in": all_country_codes}}, {"_id": 0},
    ).to_list(None)
    country_map = {c["code"]: c for c in _dedupe_by(country_docs, "code")}

    for item in scored:
        item["country"] = country_map.get(item["pathway"]["country_code"], {})

    return {
        "success": True,
        "applicant_summary": {
            "name": req.applicant_name, "role": req.current_role,
            "age": req.age, "years_of_experience": req.years_of_experience,
            "nationality": req.nationality, "family_included": req.family_included,
            "goal": req.goal,
        },
        "top": top,
        "all": scored,
        "generated_at": _now_iso(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Server-stored bundle history (last 30 generated bundles per application)
# ─────────────────────────────────────────────────────────────────────────────
BUNDLE_STORAGE_DIR = "/app/backend/visa_bundles"
os.makedirs(BUNDLE_STORAGE_DIR, exist_ok=True)


def _safe_dir_name(s: str) -> str:
    return "".join(c for c in (s or "") if c.isalnum() or c in "._-") or "unnamed"


async def _persist_bundle(aid: str, kind: str, filename: str, payload: bytes,
                           applicant_name: str = "", lawyer_name: str = "") -> dict:
    """Write bundle ZIP to disk + log to MongoDB. Returns the history record."""
    applicant_dir = os.path.join(BUNDLE_STORAGE_DIR, _safe_dir_name(applicant_name) or aid)
    os.makedirs(applicant_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stored_name = f"{timestamp}_{kind}_{filename}"
    full_path = os.path.join(applicant_dir, stored_name)
    with open(full_path, "wb") as f:
        f.write(payload)

    bundle_id = uuid.uuid4().hex[:12]
    record = {
        "bundle_id": bundle_id,
        "application_id": aid,
        "kind": kind,                 # "lawyer" | "complete"
        "applicant_name": applicant_name,
        "lawyer_name": lawyer_name,
        "filename": filename,
        "size_bytes": len(payload),
        "stored_path": full_path,
        "generated_at": _now_iso(),
    }
    await _db.visa_bundle_history.insert_one({**record})

    # Prune to last 30 records globally
    total = await _db.visa_bundle_history.count_documents({})
    if total > 30:
        old_docs = await _db.visa_bundle_history.find(
            {}, {"_id": 1, "stored_path": 1},
        ).sort("generated_at", 1).limit(total - 30).to_list(None)
        for d in old_docs:
            try:
                if d.get("stored_path") and os.path.exists(d["stored_path"]):
                    os.remove(d["stored_path"])
            except Exception:
                pass
        await _db.visa_bundle_history.delete_many({"_id": {"$in": [d["_id"] for d in old_docs]}})

    return {k: v for k, v in record.items() if k != "_id"}


@router.get("/admin/bundles")
async def list_bundle_history(token: str = Query(...)):
    await _require_admin(token)
    docs = await _db.visa_bundle_history.find({}, {"_id": 0}).sort("generated_at", -1).limit(30).to_list(None)
    return {"success": True, "bundles": docs}


@router.get("/admin/bundle/{bundle_id}")
async def admin_download_bundle(bundle_id: str, token: str = Query(...)):
    await _require_admin(token)
    doc = await _db.visa_bundle_history.find_one({"bundle_id": bundle_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Bundle not found")
    path = doc.get("stored_path", "")
    if not os.path.exists(path):
        raise HTTPException(410, "Bundle file no longer exists on disk")
    with open(path, "rb") as f:
        data = f.read()
    fname = doc.get("filename", f"bundle_{bundle_id}.zip")
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Complete bundle (auto-generate everything: report + letters + zip + persist)
# ─────────────────────────────────────────────────────────────────────────────
class _CompleteBundleReq(BaseModel):
    token: str
    signatory_id: Optional[str] = None
    entity_id: Optional[str] = None
    pathway_id: Optional[str] = None
    expansion_letter_keys: Optional[List[str]] = None  # which country-specific letters to draft


@router.post("/application/{aid}/build-complete-bundle")
async def build_complete_bundle(aid: str, req: _CompleteBundleReq = Body(...)):
    """End-to-end factory: ensure report + letters are generated, then assemble
    a structured ZIP, persist on disk, and return the download."""
    await _auth(req.token)
    app_doc = await _db.visa_applications.find_one({"application_id": aid}, {"_id": 0})
    if not app_doc:
        raise HTTPException(404, "Application not found")

    # Allow caller to override signatory / entity before bundling
    updates = {}
    biz = app_doc.get("business") or {}
    if req.signatory_id:
        biz["signatory_id"] = req.signatory_id
    if req.entity_id:
        biz["entity_id"] = req.entity_id
    if req.pathway_id:
        biz["selected_pathway_id"] = req.pathway_id
    if req.signatory_id or req.entity_id or req.pathway_id:
        updates["business"] = biz
        updates["updated_at"] = _now_iso()
        await _db.visa_applications.update_one({"application_id": aid}, {"$set": updates})
        app_doc = await _db.visa_applications.find_one({"application_id": aid}, {"_id": 0})

    country = await _db.visa_countries.find_one({"code": app_doc["country_code"]}, {"_id": 0}) or {}
    ent = await _db.visa_entities.find_one({"id": biz.get("entity_id")}, {"_id": 0}) \
          or await _db.visa_entities.find_one({}, {"_id": 0}) or {}
    sig = await _db.visa_signatories.find_one({"id": biz.get("signatory_id")}, {"_id": 0}) \
          or await _db.visa_signatories.find_one({}, {"_id": 0}) or {}

    # If report not yet generated, run it.
    if not app_doc.get("report"):
        await generate_report(aid, {"token": req.token})  # type: ignore[arg-type]
        app_doc = await _db.visa_applications.find_one({"application_id": aid}, {"_id": 0})

    # Letters are generated via the background-job endpoint to stay within
    # the production ingress 60s window. Complete-bundle does NOT itself draft
    # letters in-line (that would re-introduce the original timeout bug).
    # Whatever letters are already on the application are bundled; if none,
    # the ZIP still ships the report + checklist and the manifest notes it.
    letters = app_doc.get("letters") or []

    # Assemble structured ZIP
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if app_doc.get("report"):
            zf.writestr("01_Visa_Readiness_Report.pdf", _report_pdf_bytes(app_doc, country, ent, sig))

        # 02 — Excel checklist
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Letter Checklist"
            plan = (app_doc.get("report") or {}).get("signatory_letter_plan") or []
            headers = ["Sr. No.", "Letter / Document", "Subject", "Purpose",
                       "Signed By", "Entity", "Country", "Status"]
            for col, h in enumerate(headers, 1):
                c = ws.cell(row=1, column=col, value=h)
                c.font = Font(bold=True, color="FFFFFF")
                c.fill = PatternFill("solid", fgColor="1a365d")
            for r in plan:
                ws.append([r["sr_no"], r["letter_name"], r["subject"], r["purpose"],
                           r["signed_by"], r["entity_name"], r["country"], r["status"]])
            xb = io.BytesIO()
            wb.save(xb)
            zf.writestr("02_Letter_Checklist.xlsx", xb.getvalue())
        except Exception as ex:
            logger.warning(f"complete-bundle: checklist failed: {ex}")

        # 03 — letters
        for i, lt in enumerate(letters, 1):
            try:
                blob = _word_bytes(
                    lt["letter_name"], lt.get("body", ""),
                    sig.get("name", "—"), sig.get("role", "—"), ent.get("name", "—"),
                )
                safe_nm = "".join(c for c in lt['letter_name'] if c.isalnum() or c in " _-").replace(" ", "_")
                zf.writestr(f"03_Letters/{i:02d}_{safe_nm}.docx", blob)
            except Exception as ex:
                logger.warning(f"complete-bundle: letter {lt.get('letter_key')} failed: {ex}")

        # 99 — manifest
        manifest = (
            f"PURNABRAMHA — COMPLETE VISA BUNDLE\n"
            f"===================================\n"
            f"Application: {aid}\n"
            f"Country: {country.get('name', '—')} ({country.get('code', '—')})\n"
            f"Applicant: {(app_doc.get('applicant') or {}).get('name', '—')}\n"
            f"Pathway selected: {biz.get('selected_pathway_id') or '—'}\n"
            f"Entity: {ent.get('name', '—')}\n"
            f"Signatory: {sig.get('name', '—')} ({sig.get('role', '—')})\n"
            f"Generated: {_now_iso()}\n"
            f"Total letters: {len(letters)}\n"
        )
        zf.writestr("99_manifest.txt", manifest)

    payload = buf.getvalue()
    applicant_name = (app_doc.get("applicant") or {}).get("name") or "Applicant"
    fname = f"PB_CompleteBundle_{_safe_dir_name(applicant_name)}_{country.get('code', 'XX')}_{aid}.zip"

    record = await _persist_bundle(
        aid=aid, kind="complete", filename=fname, payload=payload,
        applicant_name=applicant_name,
    )

    await _db.visa_applications.update_one(
        {"application_id": aid},
        {"$set": {"status": "complete_bundle_ready",
                  "last_bundle_id": record["bundle_id"],
                  "updated_at": _now_iso()}},
    )

    return Response(
        content=payload,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{fname}"',
            "X-Bundle-Id": record["bundle_id"],
        },
    )

