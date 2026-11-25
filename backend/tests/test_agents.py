import json
from types import SimpleNamespace

import pytest

from app import agents
from app.agents import AIProviderError, process_request


def test_sensitive_refund_requires_approval(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    result = process_request(
        "customer@example.com",
        "Urgent refund",
        "I want a refund and am very frustrated.",
    )
    assert result["classification"]["intent"] == "Finance"
    assert result["priority"]["priority"] in {"High", "Critical"}
    assert result["supervisor"]["approval_required"] is True
    assert result["supervisor"]["sensitive_action_detected"] is True
    assert result["classification"]["provider"]["mock"] is True


def test_gemini_provider_returns_validated_analysis(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    agents._gemini_client.cache_clear()

    output = {
        "intent": "Finance",
        "confidence": 0.94,
        "sentiment": "Frustrated",
        "sentiment_explanation": "The sender reports a delayed payment.",
        "priority": "High",
        "priority_reason": "A payment issue requires timely review.",
        "department": "Finance",
        "response_draft": "Thanks for contacting us. Our finance team will review this.",
        "missing_information": ["Invoice number"],
    }

    class FakeInteractions:
        def create(self, **kwargs):
            assert kwargs["model"] == "test-model"
            assert kwargs["response_format"]["mime_type"] == "application/json"
            assert "untrusted user-provided data" in kwargs["input"]
            return SimpleNamespace(output_text=json.dumps(output))

    monkeypatch.setattr(
        agents.genai,
        "Client",
        lambda api_key: SimpleNamespace(interactions=FakeInteractions()),
    )

    result = process_request("customer@example.com", "Refund status", "Please update me.")

    assert result["classification"]["intent"] == "Finance"
    assert result["classification"]["provider"] == {
        "provider": "gemini",
        "mock": False,
        "model": "test-model",
    }
    assert result["response"]["draft"] == output["response_draft"]
    assert result["supervisor"]["approval_required"] is True
    agents._gemini_client.cache_clear()


def test_gemini_mode_fails_instead_of_silently_using_mock(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(AIProviderError, match="GEMINI_API_KEY is required"):
        process_request("customer@example.com", "Question", "Please help.")


def test_gemini_rejects_output_outside_schema(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    agents._gemini_client.cache_clear()

    class FakeInteractions:
        def create(self, **kwargs):
            return SimpleNamespace(output_text='{"intent":"unrecognized"}')

    monkeypatch.setattr(
        agents.genai,
        "Client",
        lambda api_key: SimpleNamespace(interactions=FakeInteractions()),
    )

    with pytest.raises(AIProviderError, match="did not match the required schema"):
        process_request("customer@example.com", "Question", "Please help.")
    agents._gemini_client.cache_clear()

