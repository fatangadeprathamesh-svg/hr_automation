import pytest
from starlette.requests import Request
from starlette.datastructures import Headers
from fastapi import HTTPException
from app.api.consent import record_consent, get_latest_consent, ConsentRequest, ConsentChoices
from app.models.consent import ConsentLog


def make_mock_request(user_agent: str = "TestBrowser/1.0", client_host: str = "127.0.0.1"):
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/consent",
        "headers": [(b"user-agent", user_agent.encode("utf-8"))],
        "client": (client_host, 12345),
    }
    return Request(scope)


def test_post_consent_reject_non_essential(db_session):
    req = make_mock_request()
    payload = ConsentRequest(
        anonymous_id="anon-uuid-test-001",
        policy_version="2026.1",
        choices=ConsentChoices(
            necessary=True,
            preferences=False,
            analytics=False,
        ),
    )

    data = record_consent(payload=payload, request=req, db=db_session)
    assert data["status"] == "recorded"
    assert data["anonymous_id"] == "anon-uuid-test-001"
    assert data["policy_version"] == "2026.1"
    assert data["choices"]["necessary"] is True
    assert data["choices"]["preferences"] is False
    assert data["choices"]["analytics"] is False

    # Verify retrieval via get_latest_consent
    retrieved = get_latest_consent(anonymous_id="anon-uuid-test-001", db=db_session)
    assert retrieved["anonymous_id"] == "anon-uuid-test-001"
    assert retrieved["choices"]["preferences"] is False
    assert retrieved["choices"]["analytics"] is False


def test_post_consent_accept_all(db_session):
    req = make_mock_request(user_agent="Mozilla/5.0 AcceptAllClient")
    payload = ConsentRequest(
        anonymous_id="anon-uuid-test-002",
        policy_version="2026.1",
        choices=ConsentChoices(
            necessary=True,
            preferences=True,
            analytics=True,
        ),
    )

    data = record_consent(payload=payload, request=req, db=db_session)
    assert data["choices"]["necessary"] is True
    assert data["choices"]["preferences"] is True
    assert data["choices"]["analytics"] is True

    # Retrieve and verify
    retrieved = get_latest_consent(anonymous_id="anon-uuid-test-002", db=db_session)
    assert retrieved["choices"]["preferences"] is True
    assert retrieved["choices"]["analytics"] is True


def test_get_consent_not_found(db_session):
    with pytest.raises(HTTPException) as exc_info:
        get_latest_consent(anonymous_id="non-existent-uuid-9999", db=db_session)
    assert exc_info.value.status_code == 404
