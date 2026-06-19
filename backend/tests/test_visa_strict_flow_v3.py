"""Iteration 95 — Strict Visa Flow Phase B/C/D tests.

Covers:
- list_applications include_archived param
- delete_application (soft) + restore + hard delete
- bulk_delete_applications
- generate-letters scope='selected_pathway' uses pathway required_letters
- admin pathway upsert round-trip for required_letters + required_documents
- Pathway list returns required_letters & required_documents for seeded ones
"""
import os
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or
            "https://balance-cascade-fix.preview.emergentagent.com").rstrip("/")
SUPER_ADMIN_MOBILE = "9741399190"
SUPER_ADMIN_CENTER = "PB-MGT"
FRANCHISE_MOBILE = "8888888888"
FRANCHISE_CENTER = "PB-HSR"
OTP = "123456"


@pytest.fixture(scope="module")
def super_admin_token():
    requests.post(f"{BASE_URL}/api/send_otp",
                  json={"mobile": SUPER_ADMIN_MOBILE, "center": SUPER_ADMIN_CENTER},
                  timeout=15)
    r = requests.post(f"{BASE_URL}/api/verify_otp",
                      json={"mobile": SUPER_ADMIN_MOBILE, "otp": OTP,
                            "center": SUPER_ADMIN_CENTER}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json().get("token")


@pytest.fixture(scope="module")
def franchise_token():
    requests.post(f"{BASE_URL}/api/send_otp",
                  json={"mobile": FRANCHISE_MOBILE, "center": FRANCHISE_CENTER},
                  timeout=15)
    r = requests.post(f"{BASE_URL}/api/verify_otp",
                      json={"mobile": FRANCHISE_MOBILE, "otp": OTP,
                            "center": FRANCHISE_CENTER}, timeout=15)
    if r.status_code != 200:
        return None
    return r.json().get("token")


def _create_app(token, pathway_id="AU-400", name="TEST_StrictFlow"):
    payload = {
        "token": token,
        "country_code": pathway_id.split("-")[0],
        "applicant": {"name": name, "age": 40, "nationality": "Indian"},
        "business": {"selected_pathway_id": pathway_id,
                     "signatory_id": None, "entity_id": None},
        "status": "draft",
    }
    r = requests.post(f"{BASE_URL}/api/visa/application", json=payload, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["application_id"]


# ─── Pathways: seeded required_letters/documents ────────────────────────────
class TestPathwaySeededLetters:
    def test_au400_seed(self, super_admin_token):
        r = requests.get(f"{BASE_URL}/api/visa/pathways",
                         params={"token": super_admin_token, "country_code": "AU"},
                         timeout=15)
        assert r.status_code == 200
        pws = r.json()["pathways"]
        au400 = next((p for p in pws if p["id"] == "AU-400"), None)
        assert au400, "AU-400 missing"
        assert len(au400.get("required_letters") or []) == 7, \
            f"AU-400 letters={au400.get('required_letters')}"
        assert len(au400.get("required_documents") or []) == 12, \
            f"AU-400 docs count={len(au400.get('required_documents') or [])}"
        # docs must have source field
        for d in au400["required_documents"]:
            assert "name" in d and "source" in d, f"bad doc: {d}"

    def test_au186_seed(self, super_admin_token):
        r = requests.get(f"{BASE_URL}/api/visa/pathways",
                         params={"token": super_admin_token, "country_code": "AU"},
                         timeout=15)
        pws = r.json()["pathways"]
        au186 = next((p for p in pws if p["id"] == "AU-186"), None)
        assert au186
        assert len(au186.get("required_letters") or []) == 13
        assert len(au186.get("required_documents") or []) == 10


# ─── List + Soft/Hard Delete + Restore ──────────────────────────────────────
class TestArchiveFlow:
    def test_default_list_excludes_archived(self, super_admin_token):
        aid = _create_app(super_admin_token, name="TEST_Archive1")
        # delete (soft)
        r = requests.delete(f"{BASE_URL}/api/visa/application/{aid}",
                            params={"token": super_admin_token}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["mode"] == "soft"

        # list (default) should NOT include this id
        r2 = requests.get(f"{BASE_URL}/api/visa/applications",
                          params={"token": super_admin_token}, timeout=15)
        assert r2.status_code == 200
        apps = r2.json()["applications"]
        assert all(a["application_id"] != aid for a in apps), \
            "Archived app appears in default list"

        # list with include_archived=true should include it
        r3 = requests.get(f"{BASE_URL}/api/visa/applications",
                          params={"token": super_admin_token, "include_archived": "true"},
                          timeout=15)
        assert r3.status_code == 200
        apps_all = r3.json()["applications"]
        found = next((a for a in apps_all if a["application_id"] == aid), None)
        assert found, "Archived app should appear with include_archived=true"
        assert found["status"] == "archived"

        # restore brings it back as draft
        rr = requests.post(f"{BASE_URL}/api/visa/application/{aid}/restore",
                           json={"token": super_admin_token}, timeout=15)
        assert rr.status_code == 200, rr.text
        # confirm it now reappears in default list
        r4 = requests.get(f"{BASE_URL}/api/visa/applications",
                          params={"token": super_admin_token}, timeout=15)
        apps2 = r4.json()["applications"]
        restored = next((a for a in apps2 if a["application_id"] == aid), None)
        assert restored, "Restored app should be in default list"
        assert restored["status"] == "draft"
        # cleanup hard
        requests.delete(f"{BASE_URL}/api/visa/application/{aid}",
                        params={"token": super_admin_token, "hard": "true"}, timeout=15)

    def test_hard_delete_super_admin(self, super_admin_token):
        aid = _create_app(super_admin_token, name="TEST_Hard1")
        r = requests.delete(f"{BASE_URL}/api/visa/application/{aid}",
                            params={"token": super_admin_token, "hard": "true"},
                            timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["mode"] == "hard"
        # confirm gone
        r2 = requests.get(f"{BASE_URL}/api/visa/application/{aid}",
                          params={"token": super_admin_token}, timeout=15)
        assert r2.status_code == 404


# ─── Bulk delete ────────────────────────────────────────────────────────────
class TestBulkDelete:
    def test_bulk_soft_archive(self, super_admin_token):
        ids = [_create_app(super_admin_token, name=f"TEST_Bulk_{i}") for i in range(3)]
        r = requests.post(f"{BASE_URL}/api/visa/applications/bulk-delete",
                          json={"token": super_admin_token, "application_ids": ids},
                          timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["mode"] == "soft"
        assert body["archived"] == 3, f"Expected 3 archived, got {body}"

        # all gone from default list
        r2 = requests.get(f"{BASE_URL}/api/visa/applications",
                          params={"token": super_admin_token}, timeout=15)
        visible = {a["application_id"] for a in r2.json()["applications"]}
        assert not (set(ids) & visible), "Bulk-archived apps still visible"
        # cleanup hard
        requests.post(f"{BASE_URL}/api/visa/applications/bulk-delete",
                      json={"token": super_admin_token,
                            "application_ids": ids, "hard": True},
                      timeout=20)

    def test_bulk_empty_400(self, super_admin_token):
        r = requests.post(f"{BASE_URL}/api/visa/applications/bulk-delete",
                          json={"token": super_admin_token, "application_ids": []},
                          timeout=10)
        assert r.status_code == 400


# ─── generate-letters scope=selected_pathway ────────────────────────────────
class TestGenerateLettersSelectedPathway:
    def test_au400_returns_total_7(self, super_admin_token):
        aid = _create_app(super_admin_token, pathway_id="AU-400",
                          name="TEST_GenLetters_AU400")
        try:
            payload = {"token": super_admin_token, "application_id": aid, "scope": "selected_pathway"}
            r = requests.post(
                f"{BASE_URL}/api/visa/application/{aid}/generate-letters",
                json=payload, timeout=30)
            assert r.status_code == 200, r.text
            body = r.json()
            assert body.get("success") is True
            # selected_pathway scope should use AU-400's 7 required_letters
            assert body.get("total") == 7, \
                f"Expected total=7 for AU-400 selected_pathway, got {body.get('total')}: {body}"
            assert body.get("status") == "running"
        finally:
            requests.delete(f"{BASE_URL}/api/visa/application/{aid}",
                            params={"token": super_admin_token, "hard": "true"},
                            timeout=10)


# ─── Admin pathway upsert round-trip ────────────────────────────────────────
class TestAdminPathwayUpsert:
    def test_round_trip_required_letters_documents(self, super_admin_token):
        # Read original AU-407
        r = requests.get(f"{BASE_URL}/api/visa/pathways",
                         params={"token": super_admin_token, "country_code": "AU"},
                         timeout=15)
        pws = r.json()["pathways"]
        au407 = next((p for p in pws if p["id"] == "AU-407"), None)
        assert au407, "AU-407 not seeded"
        original_letters = list(au407.get("required_letters") or [])
        original_docs = list(au407.get("required_documents") or [])

        # Upsert with new arrays
        new_letters = ["employment_offer", "training_plan", "personal_statement"]
        new_docs = [
            {"name": "TEST_DOC_A", "source": "Applicant"},
            {"name": "TEST_DOC_B", "source": "Bank"},
        ]
        payload = {
            "token": super_admin_token,
            **au407,
            "required_letters": new_letters,
            "required_documents": new_docs,
        }
        rp = requests.post(f"{BASE_URL}/api/visa/admin/pathway",
                           json=payload, timeout=20)
        assert rp.status_code == 200, rp.text

        # GET and verify persisted
        r2 = requests.get(f"{BASE_URL}/api/visa/pathways",
                          params={"token": super_admin_token, "country_code": "AU"},
                          timeout=15)
        au407b = next((p for p in r2.json()["pathways"] if p["id"] == "AU-407"), None)
        assert au407b
        assert au407b.get("required_letters") == new_letters, \
            f"letters not persisted: {au407b.get('required_letters')}"
        # docs may be returned in same order
        assert au407b.get("required_documents") == new_docs, \
            f"docs not persisted: {au407b.get('required_documents')}"

        # Restore original
        restore_payload = {
            "token": super_admin_token,
            **au407,
            "required_letters": original_letters,
            "required_documents": original_docs,
        }
        rr = requests.post(f"{BASE_URL}/api/visa/admin/pathway",
                           json=restore_payload, timeout=20)
        assert rr.status_code == 200
