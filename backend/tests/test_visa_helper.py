"""Backend tests for Visa Helper / Global Mobility module."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://balance-cascade-fix.preview.emergentagent.com").rstrip("/")
SUPER_ADMIN_MOBILE = "9741399190"
SUPER_ADMIN_CENTER = "PB-MGT"
FRANCHISE_MOBILE = "8888888888"
FRANCHISE_CENTER = "PB-HSR"
OTP = "123456"


# ─── Fixtures ───────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def super_admin_token():
    requests.post(f"{BASE_URL}/api/send_otp", json={"mobile": SUPER_ADMIN_MOBILE, "center": SUPER_ADMIN_CENTER}, timeout=15)
    r = requests.post(f"{BASE_URL}/api/verify_otp",
                      json={"mobile": SUPER_ADMIN_MOBILE, "otp": OTP, "center": SUPER_ADMIN_CENTER}, timeout=15)
    assert r.status_code == 200, r.text
    token = r.json().get("token")
    assert token
    return token


@pytest.fixture(scope="module")
def franchise_token():
    requests.post(f"{BASE_URL}/api/send_otp", json={"mobile": FRANCHISE_MOBILE, "center": FRANCHISE_CENTER}, timeout=15)
    r = requests.post(f"{BASE_URL}/api/verify_otp",
                      json={"mobile": FRANCHISE_MOBILE, "otp": OTP, "center": FRANCHISE_CENTER}, timeout=15)
    if r.status_code != 200:
        return None
    return r.json().get("token")


# ─── List endpoints (seeded data) ───────────────────────────────────────────
class TestListEndpoints:
    def test_countries(self, super_admin_token):
        r = requests.get(f"{BASE_URL}/api/visa/countries", params={"token": super_admin_token}, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["success"] is True
        countries = data["countries"]
        assert isinstance(countries, list) and len(countries) >= 5
        codes = {c["code"] for c in countries}
        # Required country tiles per spec
        for needed in ["AU", "US", "JP", "BE", "SG"]:
            assert needed in codes, f"Missing seeded country {needed}"

    def test_pathways(self, super_admin_token):
        r = requests.get(f"{BASE_URL}/api/visa/pathways", params={"token": super_admin_token}, timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json()["pathways"], list) and len(r.json()["pathways"]) > 0

    def test_pathways_filter_country(self, super_admin_token):
        r = requests.get(f"{BASE_URL}/api/visa/pathways",
                         params={"token": super_admin_token, "country_code": "AU"}, timeout=15)
        assert r.status_code == 200
        for p in r.json()["pathways"]:
            assert p["country_code"] == "AU"

    def test_letter_templates(self, super_admin_token):
        r = requests.get(f"{BASE_URL}/api/visa/letter-templates", params={"token": super_admin_token}, timeout=15)
        assert r.status_code == 200
        tpls = r.json()["letter_templates"] if "letter_templates" in r.json() else r.json().get("templates", [])
        assert isinstance(tpls, list) and len(tpls) > 0

    def test_entities(self, super_admin_token):
        r = requests.get(f"{BASE_URL}/api/visa/entities", params={"token": super_admin_token}, timeout=15)
        assert r.status_code == 200
        assert len(r.json()["entities"]) > 0

    def test_signatories(self, super_admin_token):
        r = requests.get(f"{BASE_URL}/api/visa/signatories", params={"token": super_admin_token}, timeout=15)
        assert r.status_code == 200
        assert len(r.json()["signatories"]) > 0


# ─── Application CRUD + Report + Letters + Exports ──────────────────────────
class TestApplicationFlow:
    app_id = None
    entity_id = None
    signatory_id = None

    def test_pick_entity_signatory(self, super_admin_token):
        r1 = requests.get(f"{BASE_URL}/api/visa/entities", params={"token": super_admin_token}, timeout=15)
        r2 = requests.get(f"{BASE_URL}/api/visa/signatories", params={"token": super_admin_token}, timeout=15)
        TestApplicationFlow.entity_id = r1.json()["entities"][0]["id"]
        TestApplicationFlow.signatory_id = r2.json()["signatories"][0]["id"]
        assert TestApplicationFlow.entity_id and TestApplicationFlow.signatory_id

    def test_create_application(self, super_admin_token):
        payload = {
            "token": super_admin_token,
            "country_code": "AU",
            "applicant": {
                "name": "TEST_Applicant Visa",
                "age": 32,
                "years_of_experience": 8,
                "education": "Masters",
                "spouse": False,
                "children": 0,
            },
            "business": {
                "entity_id": TestApplicationFlow.entity_id,
                "signatory_id": TestApplicationFlow.signatory_id,
                "role": "Director",
                "business_type": "Expansion",
                "goal": "PR",
            },
            "status": "draft",
        }
        r = requests.post(f"{BASE_URL}/api/visa/application", json=payload, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["success"] is True
        assert body["application_id"].startswith("VA-")
        TestApplicationFlow.app_id = body["application_id"]

    def test_update_application(self, super_admin_token):
        assert TestApplicationFlow.app_id
        payload = {
            "token": super_admin_token,
            "application_id": TestApplicationFlow.app_id,
            "country_code": "AU",
            "applicant": {"name": "TEST_Applicant Visa", "age": 33, "years_of_experience": 9},
            "business": {
                "entity_id": TestApplicationFlow.entity_id,
                "signatory_id": TestApplicationFlow.signatory_id,
                "role": "Director", "goal": "PR",
            },
            "status": "draft",
        }
        r = requests.post(f"{BASE_URL}/api/visa/application", json=payload, timeout=15)
        assert r.status_code == 200
        assert r.json()["application_id"] == TestApplicationFlow.app_id
        # Persistence check
        g = requests.get(f"{BASE_URL}/api/visa/application/{TestApplicationFlow.app_id}",
                         params={"token": super_admin_token}, timeout=15)
        assert g.status_code == 200
        assert g.json()["application"]["applicant"]["age"] == 33

    def test_list_applications(self, super_admin_token):
        r = requests.get(f"{BASE_URL}/api/visa/applications",
                         params={"token": super_admin_token}, timeout=15)
        assert r.status_code == 200
        ids = [a["application_id"] for a in r.json()["applications"]]
        assert TestApplicationFlow.app_id in ids

    def test_generate_report(self, super_admin_token):
        r = requests.post(f"{BASE_URL}/api/visa/application/{TestApplicationFlow.app_id}/generate-report",
                          json={"token": super_admin_token}, timeout=45)
        assert r.status_code == 200, r.text
        body = r.json()
        report = body.get("report") or body
        # Spec required fields
        for key in ["suitability", "score", "ranked_pathways", "documents_required",
                    "cost_heads", "signatory_letter_plan", "disclaimer"]:
            assert key in report, f"Missing key in report: {key}. Keys present: {list(report.keys())}"
        # Documents required must have company/applicant/family buckets
        docs = report["documents_required"]
        assert isinstance(docs, dict)
        for sub in ["company", "applicant", "family"]:
            assert sub in docs, f"documents_required missing '{sub}' bucket"

    def test_generate_letters_small_scope(self, super_admin_token):
        """Use only 1 letter (director_resolution) to keep LLM cost low.

        generate-letters is now a background-job endpoint (returns immediately
        with job_id); the test polls /letter-status until the job completes.
        """
        import time
        payload = {
            "token": super_admin_token,
            "application_id": TestApplicationFlow.app_id,
            "letter_keys": ["director_resolution"],
            "scope": "resolutions",
        }
        r = requests.post(f"{BASE_URL}/api/visa/application/{TestApplicationFlow.app_id}/generate-letters",
                          json=payload, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("status") == "running", data
        assert data.get("total") == 1, data

        # Poll up to 90s for the job to complete
        deadline = time.time() + 90
        while time.time() < deadline:
            time.sleep(3)
            st = requests.get(
                f"{BASE_URL}/api/visa/application/{TestApplicationFlow.app_id}/letter-status",
                params={"token": super_admin_token}, timeout=15,
            )
            assert st.status_code == 200, st.text
            sdata = st.json()
            if sdata.get("status") == "done":
                break
            if sdata.get("status") == "error":
                raise AssertionError(f"Letter job errored: {sdata}")
        else:
            raise AssertionError("Letter generation did not complete within 90s")

        letters = sdata.get("letters") or []
        assert len(letters) >= 1
        ltr = next((l for l in letters if l["letter_key"] == "director_resolution"), None)
        assert ltr is not None, f"director_resolution not in {[l['letter_key'] for l in letters]}"
        assert ltr["status"] == "Drafted", f"Letter status={ltr['status']} body={ltr.get('body','')[:200]}"
        assert ltr["body"] and len(ltr["body"]) > 50

    def test_report_pdf(self, super_admin_token):
        r = requests.get(f"{BASE_URL}/api/visa/application/{TestApplicationFlow.app_id}/report-pdf",
                        params={"token": super_admin_token}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert len(r.content) > 1024

    def test_checklist_excel(self, super_admin_token):
        r = requests.get(f"{BASE_URL}/api/visa/application/{TestApplicationFlow.app_id}/checklist-excel",
                        params={"token": super_admin_token}, timeout=30)
        assert r.status_code == 200
        assert len(r.content) > 1024
        # XLSX magic bytes (PK..)
        assert r.content[:2] == b"PK"

    def test_letter_word(self, super_admin_token):
        r = requests.get(f"{BASE_URL}/api/visa/application/{TestApplicationFlow.app_id}/letter/director_resolution/word",
                        params={"token": super_admin_token}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert len(r.content) > 512
        assert r.content[:2] == b"PK"  # docx is also zip

    def test_zip_bundle(self, super_admin_token):
        r = requests.get(f"{BASE_URL}/api/visa/application/{TestApplicationFlow.app_id}/zip",
                        params={"token": super_admin_token}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.content[:2] == b"PK"
        # Inspect zip contents
        import io, zipfile
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        names = zf.namelist()
        assert any(n.lower().endswith(".pdf") for n in names), f"Missing PDF in zip: {names}"
        assert any("checklist" in n.lower() and n.lower().endswith(".xlsx") for n in names), f"Missing Excel checklist in zip: {names}"
        assert any(n.lower().startswith("letters/") and n.lower().endswith(".docx") for n in names), f"Missing letter docx in zip: {names}"
        assert any("manifest" in n.lower() for n in names), f"Missing manifest in zip: {names}"

    def test_delete_application(self, super_admin_token):
        r = requests.delete(f"{BASE_URL}/api/visa/application/{TestApplicationFlow.app_id}",
                            params={"token": super_admin_token}, timeout=15)
        assert r.status_code == 200
        g = requests.get(f"{BASE_URL}/api/visa/application/{TestApplicationFlow.app_id}",
                         params={"token": super_admin_token}, timeout=15)
        assert g.status_code == 404


# ─── Admin CRUD ─────────────────────────────────────────────────────────────
class TestAdminCRUD:
    def test_country_upsert_delete(self, super_admin_token):
        payload = {"token": super_admin_token, "code": "TEST_ZZ", "name": "TestLand",
                   "flag": "🏳️", "available": True}
        r = requests.post(f"{BASE_URL}/api/visa/admin/country", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        # Verify present
        r2 = requests.get(f"{BASE_URL}/api/visa/countries", params={"token": super_admin_token}, timeout=15)
        codes = {c["code"] for c in r2.json()["countries"]}
        assert "TEST_ZZ" in codes
        # Delete
        d = requests.delete(f"{BASE_URL}/api/visa/admin/country/TEST_ZZ",
                            params={"token": super_admin_token}, timeout=15)
        assert d.status_code == 200

    def test_pathway_upsert_delete(self, super_admin_token):
        payload = {"token": super_admin_token, "id": "TEST_PW1", "country_code": "AU",
                   "name": "TEST Pathway", "type": "Temporary", "min_age": 18, "max_age": 60}
        r = requests.post(f"{BASE_URL}/api/visa/admin/pathway", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        d = requests.delete(f"{BASE_URL}/api/visa/admin/pathway/TEST_PW1",
                            params={"token": super_admin_token}, timeout=15)
        assert d.status_code == 200

    def test_letter_template_upsert_delete(self, super_admin_token):
        payload = {"token": super_admin_token, "id": "TEST_LT1", "name": "TEST Template",
                   "subject": "subj", "purpose": "purpose"}
        r = requests.post(f"{BASE_URL}/api/visa/admin/letter-template", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        d = requests.delete(f"{BASE_URL}/api/visa/admin/letter-template/TEST_LT1",
                            params={"token": super_admin_token}, timeout=15)
        assert d.status_code == 200

    def test_entity_upsert_delete(self, super_admin_token):
        payload = {"token": super_admin_token, "id": "TEST_E1", "name": "TEST Entity",
                   "country": "India", "address": "addr"}
        r = requests.post(f"{BASE_URL}/api/visa/admin/entity", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        d = requests.delete(f"{BASE_URL}/api/visa/admin/entity/TEST_E1",
                            params={"token": super_admin_token}, timeout=15)
        assert d.status_code == 200

    def test_signatory_upsert_delete(self, super_admin_token):
        payload = {"token": super_admin_token, "id": "TEST_S1", "name": "TEST Signer",
                   "designation": "Dir", "entity_id": "ANY"}
        r = requests.post(f"{BASE_URL}/api/visa/admin/signatory", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        d = requests.delete(f"{BASE_URL}/api/visa/admin/signatory/TEST_S1",
                            params={"token": super_admin_token}, timeout=15)
        assert d.status_code == 200

    def test_admin_rejects_non_admin(self, franchise_token):
        if not franchise_token:
            pytest.skip("Franchise token unavailable")
        payload = {"token": franchise_token, "code": "TEST_NONADM", "name": "X"}
        r = requests.post(f"{BASE_URL}/api/visa/admin/country", json=payload, timeout=15)
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text[:200]}"
