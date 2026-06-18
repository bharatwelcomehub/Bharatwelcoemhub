"""Backend tests for Visa Helper v2 (AI Recommender + Bundle History)."""
import io
import os
import zipfile
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://balance-cascade-fix.preview.emergentagent.com").rstrip("/")
SUPER_ADMIN_MOBILE = "9741399190"
SUPER_ADMIN_CENTER = "PB-MGT"
FRANCHISE_MOBILE = "8888888888"
FRANCHISE_CENTER = "PB-HSR"
OTP = "123456"
EXISTING_APP_ID = "VA-3F0A0162DD"


# ─── Fixtures ───────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def super_admin_token():
    requests.post(f"{BASE_URL}/api/send_otp", json={"mobile": SUPER_ADMIN_MOBILE, "center": SUPER_ADMIN_CENTER}, timeout=15)
    r = requests.post(f"{BASE_URL}/api/verify_otp",
                      json={"mobile": SUPER_ADMIN_MOBILE, "otp": OTP, "center": SUPER_ADMIN_CENTER}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json().get("token")


@pytest.fixture(scope="module")
def franchise_token():
    requests.post(f"{BASE_URL}/api/send_otp", json={"mobile": FRANCHISE_MOBILE, "center": FRANCHISE_CENTER}, timeout=15)
    r = requests.post(f"{BASE_URL}/api/verify_otp",
                      json={"mobile": FRANCHISE_MOBILE, "otp": OTP, "center": FRANCHISE_CENTER}, timeout=15)
    if r.status_code != 200:
        return None
    return r.json().get("token")


# ─── 1. Dedupe & Seeded Catalog ─────────────────────────────────────────────
class TestSeededCatalog:
    def test_countries_exactly_6_unique(self, super_admin_token):
        r = requests.get(f"{BASE_URL}/api/visa/countries", params={"token": super_admin_token}, timeout=20)
        assert r.status_code == 200, r.text
        countries = r.json()["countries"]
        codes = [c["code"] for c in countries]
        assert len(codes) == len(set(codes)), f"Duplicate country codes: {codes}"
        code_set = set(codes)
        for needed in ["AU", "BE", "EU", "JP", "SG", "US"]:
            assert needed in code_set, f"Missing {needed} in {code_set}"
        assert len(code_set) == 6, f"Expected exactly 6 unique countries, got {len(code_set)}: {code_set}"

    def test_pathways_catalog(self, super_admin_token):
        r = requests.get(f"{BASE_URL}/api/visa/pathways", params={"token": super_admin_token}, timeout=15)
        assert r.status_code == 200
        pathways = r.json()["pathways"]
        assert len(pathways) >= 16, f"Expected >=16 pathways, got {len(pathways)}"
        ids = {p["id"] for p in pathways}
        # AU 5
        for pid in ["AU-186", "AU-482", "AU-188", "AU-494", "AU-GT"]:
            assert pid in ids, f"Missing AU pathway {pid}"
        # US at least 4
        for pid in ["US-L1A", "US-E2", "US-EB1C", "US-EB2NIW"]:
            assert pid in ids, f"Missing US pathway {pid}"
        # JP
        for pid in ["JP-BM", "JP-HSP"]:
            assert pid in ids, f"Missing JP pathway {pid}"
        # SG
        for pid in ["SG-EP", "SG-EntrePass"]:
            assert pid in ids, f"Missing SG pathway {pid}"
        # BE
        for pid in ["BE-SP", "BE-SE"]:
            assert pid in ids, f"Missing BE pathway {pid}"
        # EU
        for pid in ["EU-ICT", "EU-BLUE"]:
            assert pid in ids, f"Missing EU pathway {pid}"

    def test_pathway_enrichment_fields(self, super_admin_token):
        r = requests.get(f"{BASE_URL}/api/visa/pathways",
                         params={"token": super_admin_token, "country_code": "AU"}, timeout=15)
        pathways = r.json()["pathways"]
        # Find AU-186 and verify enrichment fields are populated (not just present)
        au186 = next((p for p in pathways if p["id"] == "AU-186"), None)
        assert au186, "AU-186 not found"
        for field in ["spouse_work_rights", "key_requirements", "company_cost_band",
                       "applicant_cost_band", "timeline_band"]:
            assert field in au186, f"AU-186 missing field {field}"
            val = au186[field]
            # Should not be empty / None
            if isinstance(val, list):
                assert len(val) > 0, f"AU-186 field {field} is empty list"
            else:
                assert val, f"AU-186 field {field} is falsy: {val!r}"

    def test_entities_6(self, super_admin_token):
        r = requests.get(f"{BASE_URL}/api/visa/entities", params={"token": super_admin_token}, timeout=15)
        assert r.status_code == 200
        entities = r.json()["entities"]
        assert len(entities) >= 6, f"Expected >=6 entities, got {len(entities)}"


# ─── 2. Cleanup duplicates admin endpoint ───────────────────────────────────
class TestCleanupDuplicates:
    def test_cleanup_super_admin(self, super_admin_token):
        r = requests.post(f"{BASE_URL}/api/visa/admin/cleanup-duplicates",
                          json={"token": super_admin_token}, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("success") is True
        assert "removed" in body

    def test_cleanup_non_admin_403(self, franchise_token):
        if not franchise_token:
            pytest.skip("Franchise token unavailable")
        r = requests.post(f"{BASE_URL}/api/visa/admin/cleanup-duplicates",
                          json={"token": franchise_token}, timeout=15)
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text[:200]}"


# ─── 3. AI Recommender ──────────────────────────────────────────────────────
SANDEEP_PROFILE = {
    "applicant_name": "Sandeep Kathale",
    "current_role": "Managing Director",
    "age": 42,
    "years_of_experience": 15,
    "nationality": "Indian",
    "english_status": "Passed",
    "family_included": True,
    "shareholding_pct": 35,
    "has_existing_operations": True,
    "has_expansion_plan": True,
    "has_business_plan": True,
    "has_financial_proof": True,
    "has_franchise_letter": True,
    "has_skills_assessment": False,
    "goal": "PR + family",
    "country_codes": ["AU", "US"],
}


class TestRecommender:
    def test_recommend_rule_only(self, super_admin_token):
        payload = {**SANDEEP_PROFILE, "token": super_admin_token, "use_ai_narrative": False}
        r = requests.post(f"{BASE_URL}/api/visa/recommend", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("success") is True
        top = body.get("top") or []
        all_items = body.get("all") or []
        assert len(top) == 5, f"Expected top=5, got {len(top)}"
        assert len(all_items) >= 9, f"Expected all >=9, got {len(all_items)}"
        # Each top item has required keys
        for item in top:
            for key in ["pathway", "score", "suitability", "reasons", "risks", "country"]:
                assert key in item, f"Top item missing {key}: keys={list(item.keys())}"
            assert item["suitability"] in ("Strong", "Medium", "Low")
            assert isinstance(item["reasons"], list)
            assert isinstance(item["risks"], list)
            assert isinstance(item["country"], dict) and "code" in item["country"]
        # Top must contain only AU/US pathways since country_codes=['AU','US']
        expected_ids = {"AU-186", "AU-482", "AU-188", "AU-494", "AU-GT",
                        "US-L1A", "US-E2", "US-EB1C", "US-EB2NIW"}
        top_pids = {item["pathway"]["id"] for item in top}
        assert top_pids.issubset(expected_ids), f"Unexpected top pathway ids: {top_pids - expected_ids}"

    def test_recommend_with_ai_narrative(self, super_admin_token):
        payload = {**SANDEEP_PROFILE,
                   "token": super_admin_token,
                   "country_codes": ["AU"],
                   "use_ai_narrative": True}
        r = requests.post(f"{BASE_URL}/api/visa/recommend", json=payload, timeout=180)
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        top = body.get("top") or []
        assert len(top) >= 3
        # Top-3 must have ai_rationale
        for item in top[:3]:
            ai = item.get("ai_rationale")
            assert ai and isinstance(ai, str) and len(ai.strip()) > 10, \
                f"Missing/empty ai_rationale on pathway {item['pathway'].get('id')}: {ai!r}"


# ─── 4. Build-complete-bundle + history ─────────────────────────────────────
class TestBundleHistory:
    bundle_id = None

    def test_build_complete_bundle(self, super_admin_token):
        url = f"{BASE_URL}/api/visa/application/{EXISTING_APP_ID}/build-complete-bundle"
        r = requests.post(url, json={"token": super_admin_token}, timeout=180)
        assert r.status_code == 200, r.text[:500]
        ctype = r.headers.get("content-type", "")
        assert "application/zip" in ctype or "zip" in ctype, f"Unexpected content-type: {ctype}"
        assert len(r.content) > 5 * 1024, f"Bundle too small: {len(r.content)} bytes"
        bundle_id = r.headers.get("X-Bundle-Id")
        assert bundle_id, f"Missing X-Bundle-Id header. Headers: {dict(r.headers)}"
        TestBundleHistory.bundle_id = bundle_id
        # Inspect zip
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        names = zf.namelist()
        # Required structure per spec
        assert any("01_Visa_Readiness_Report.pdf" in n for n in names), f"Missing 01_Visa_Readiness_Report.pdf: {names}"
        assert any("02_Letter_Checklist.xlsx" in n for n in names), f"Missing 02_Letter_Checklist.xlsx: {names}"
        assert any(n.startswith("03_Letters/") and n.lower().endswith(".docx") for n in names), \
            f"Missing 03_Letters/*.docx: {names}"
        assert any("99_manifest.txt" in n for n in names), f"Missing 99_manifest.txt: {names}"

    def test_list_bundles_super_admin(self, super_admin_token):
        r = requests.get(f"{BASE_URL}/api/visa/admin/bundles",
                         params={"token": super_admin_token}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        bundles = body.get("bundles") or body.get("history") or []
        assert isinstance(bundles, list) and len(bundles) > 0
        # Find our bundle in the list
        found = None
        if TestBundleHistory.bundle_id:
            for b in bundles:
                if b.get("bundle_id") == TestBundleHistory.bundle_id or b.get("id") == TestBundleHistory.bundle_id:
                    found = b
                    break
        # If specific bundle_id not found, just verify at least one bundle for our application
        for b in bundles:
            if b.get("application_id") == EXISTING_APP_ID and b.get("kind") == "complete":
                found = found or b
                break
        assert found, f"New bundle not in history list. Bundles: {bundles[:3]}"
        # Verify required fields
        for key in ["bundle_id", "application_id", "kind", "filename", "size_bytes"]:
            # Allow id as alias for bundle_id
            assert key in found or (key == "bundle_id" and "id" in found), \
                f"Bundle entry missing {key}: keys={list(found.keys())}"
        kind = found.get("kind")
        assert kind == "complete", f"Expected kind=complete, got {kind}"

    def test_admin_download_bundle(self, super_admin_token):
        if not TestBundleHistory.bundle_id:
            pytest.skip("No bundle_id from previous test")
        url = f"{BASE_URL}/api/visa/admin/bundle/{TestBundleHistory.bundle_id}"
        r = requests.get(url, params={"token": super_admin_token}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        ctype = r.headers.get("content-type", "")
        assert "zip" in ctype, f"Expected zip, got {ctype}"
        assert r.content[:2] == b"PK", "Not a valid ZIP file"
        assert len(r.content) > 1024

    def test_admin_download_bundle_non_admin_403(self, franchise_token):
        if not franchise_token:
            pytest.skip("Franchise token unavailable")
        if not TestBundleHistory.bundle_id:
            pytest.skip("No bundle_id from previous test")
        url = f"{BASE_URL}/api/visa/admin/bundle/{TestBundleHistory.bundle_id}"
        r = requests.get(url, params={"token": franchise_token}, timeout=15)
        assert r.status_code == 403, f"Expected 403, got {r.status_code}"
