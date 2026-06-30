"""Integration tests for report chat API endpoints.

Requires PostgreSQL running:
  docker compose -f docker-compose.local.yml up -d
"""

import uuid
from unittest.mock import patch

import pytest

# ── helpers ──────────────────────────────────────────────────────────────────

_AI_REWRITE_RESPONSE = {
    "intent": {"intent": "rewrite_section", "target_section": "A", "requires_patch": True},
    "assistant_message": "A 섹션 수정 제안입니다.",
    "patch_proposal": {
        "target_section": "A",
        "original_text": "기존 내용",
        "proposed_text": "수정된 내용",
        "rationale": "임상 표현 강화",
        "evidence_refs": [],
    },
}

_AI_OFF_TOPIC_RESPONSE = {
    "intent": {"intent": "off_topic", "target_section": None, "requires_patch": False},
    "assistant_message": "이 챗봇은 SOAP 리포트 수정만 지원합니다.",
    "patch_proposal": None,
}


def _register_and_login(client) -> dict:
    email = f"slp_{uuid.uuid4().hex[:8]}@test.com"
    client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "Test1234!", "name": "Test SLP"},
    )
    res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Test1234!"},
    )
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


# ── auth guard ────────────────────────────────────────────────────────────────

class TestChatAuthGuard:
    def test_send_message_requires_auth(self, client):
        res = client.post(
            f"/api/v1/reports/{uuid.uuid4()}/chat/messages",
            json={"message": "테스트"},
        )
        assert res.status_code == 401

    def test_apply_patch_requires_auth(self, client):
        res = client.post(f"/api/v1/reports/patch-proposals/{uuid.uuid4()}/apply")
        assert res.status_code == 401

    def test_evidence_requires_auth(self, client):
        res = client.get(f"/api/v1/reports/{uuid.uuid4()}/chat/evidence")
        assert res.status_code == 401


# ── 404 guard (존재하지 않는 report/patch) ──────────────────────────────────

class TestChatNotFound:
    def test_send_message_to_nonexistent_report_returns_404(self, client):
        headers = _register_and_login(client)
        res = client.post(
            f"/api/v1/reports/{uuid.uuid4()}/chat/messages",
            json={"message": "테스트"},
            headers=headers,
        )
        assert res.status_code == 404

    def test_apply_nonexistent_patch_returns_404(self, client):
        headers = _register_and_login(client)
        res = client.post(
            f"/api/v1/reports/patch-proposals/{uuid.uuid4()}/apply",
            headers=headers,
        )
        assert res.status_code == 404

    def test_evidence_for_nonexistent_report_returns_404(self, client):
        headers = _register_and_login(client)
        res = client.get(
            f"/api/v1/reports/{uuid.uuid4()}/chat/evidence",
            headers=headers,
        )
        assert res.status_code == 404


# ── full flow ─────────────────────────────────────────────────────────────────

class TestChatFlow:
    def _create_report_fixture(self, client, headers: dict) -> dict:
        """환자 → 세션 → 분석 완료까지 픽스처 데이터를 생성한다."""
        patient_ref_res = client.post("/api/v1/patients/", json={}, headers=headers)
        if patient_ref_res.status_code not in (200, 201):
            pytest.skip("환자 생성 API 미지원 — full-flow 테스트 skip")

        patient_ref_id = patient_ref_res.json()["id"]

        session_res = client.post(
            "/api/v1/sessions/",
            json={"patient_ref_id": patient_ref_id, "session_date": "2025-01-01"},
            headers=headers,
        )
        if session_res.status_code not in (200, 201):
            pytest.skip("세션 생성 API 미지원 — full-flow 테스트 skip")

        session_id = session_res.json()["id"]

        reports = client.get(
            f"/api/v1/reports/?session_id={session_id}", headers=headers
        ).json()
        if not reports:
            pytest.skip("리포트가 없음 — full-flow 테스트 skip")

        return {"report_id": reports[0]["id"]}

    def test_off_topic_message_returns_no_patch(self, client):
        headers = _register_and_login(client)
        fixture = self._create_report_fixture(client, headers)
        report_id = fixture["report_id"]

        with patch(
            "app.services.report_chat.ReportChatService._call_ai_service",
            return_value=_AI_OFF_TOPIC_RESPONSE,
        ):
            res = client.post(
                f"/api/v1/reports/{report_id}/chat/messages",
                json={"message": "저녁 뭐 먹을까?"},
                headers=headers,
            )

        assert res.status_code == 200
        body = res.json()
        assert body["intent"]["intent"] == "off_topic"
        assert body["patch_proposal"] is None

    def test_rewrite_message_returns_patch_and_apply_increments_version(self, client):
        headers = _register_and_login(client)
        fixture = self._create_report_fixture(client, headers)
        report_id = fixture["report_id"]

        with patch(
            "app.services.report_chat.ReportChatService._call_ai_service",
            return_value=_AI_REWRITE_RESPONSE,
        ):
            msg_res = client.post(
                f"/api/v1/reports/{report_id}/chat/messages",
                json={"message": "A 섹션 더 전문적으로 써줘"},
                headers=headers,
            )

        assert msg_res.status_code == 200
        body = msg_res.json()
        assert body["patch_proposal"] is not None
        patch_id = body["patch_proposal"]["patch_id"]

        report_before = client.get(f"/api/v1/reports/{report_id}", headers=headers).json()
        version_before = report_before.get("version", 1)

        apply_res = client.post(
            f"/api/v1/reports/patch-proposals/{patch_id}/apply",
            headers=headers,
        )
        assert apply_res.status_code == 200
        apply_body = apply_res.json()
        assert apply_body["version"] == version_before + 1
        assert "A" in apply_body["updated_sections"]

    def test_apply_same_patch_twice_returns_409(self, client):
        headers = _register_and_login(client)
        fixture = self._create_report_fixture(client, headers)
        report_id = fixture["report_id"]

        with patch(
            "app.services.report_chat.ReportChatService._call_ai_service",
            return_value=_AI_REWRITE_RESPONSE,
        ):
            msg_res = client.post(
                f"/api/v1/reports/{report_id}/chat/messages",
                json={"message": "A 섹션 수정"},
                headers=headers,
            )
        patch_id = msg_res.json()["patch_proposal"]["patch_id"]

        client.post(f"/api/v1/reports/patch-proposals/{patch_id}/apply", headers=headers)

        second = client.post(
            f"/api/v1/reports/patch-proposals/{patch_id}/apply", headers=headers
        )
        assert second.status_code == 409

    def test_other_user_cannot_apply_patch(self, client):
        headers_owner = _register_and_login(client)
        fixture = self._create_report_fixture(client, headers_owner)
        report_id = fixture["report_id"]

        with patch(
            "app.services.report_chat.ReportChatService._call_ai_service",
            return_value=_AI_REWRITE_RESPONSE,
        ):
            msg_res = client.post(
                f"/api/v1/reports/{report_id}/chat/messages",
                json={"message": "A 섹션 수정"},
                headers=headers_owner,
            )
        patch_id = msg_res.json()["patch_proposal"]["patch_id"]

        headers_other = _register_and_login(client)
        res = client.post(
            f"/api/v1/reports/patch-proposals/{patch_id}/apply",
            headers=headers_other,
        )
        assert res.status_code in (403, 404)