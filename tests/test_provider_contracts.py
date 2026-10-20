import io
import json

import pytest

from src.llm_batch import OpenAIResponsesClient, GeminiClient, analyze_entry, create_client


def test_openai_raw_http_output_not_sdk_convenience_property(monkeypatch):
    response = {
        "status": "completed",
        "output": [
            {"type": "reasoning", "summary": []},
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": '{"mood_tag":"neutral",'},
                    {"type": "output_text", "text": '"topic_tag":"health","summary":"散歩"}'},
                ],
            },
        ],
    }
    monkeypatch.setattr(
        "src.llm_batch.request.urlopen", lambda *a, **kw: io.BytesIO(json.dumps(response).encode())
    )
    result = analyze_entry("散歩", OpenAIResponsesClient("test", "test-model"))
    assert result.summary == "散歩"


def test_openai_incomplete_is_rejected(monkeypatch):
    monkeypatch.setattr(
        "src.llm_batch.request.urlopen",
        lambda *a, **kw: io.BytesIO(b'{"status":"incomplete","output":[]}'),
    )
    with pytest.raises(ValueError, match="not completed"):
        OpenAIResponsesClient("test", "test-model").complete_json("JSON test")


def test_gemini_header_and_thought_filter(monkeypatch):
    def respond(request, **kwargs):
        assert "key=" not in request.full_url
        assert request.get_header("X-goog-api-key") == "test-secret"
        payload = {
            "candidates": [
                {
                    "finishReason": "STOP",
                    "content": {
                        "parts": [
                            {"thought": True, "text": "ignored"},
                            {
                                "text": '{"mood_tag":"neutral","topic_tag":"health","summary":"散歩"}'
                            },
                        ]
                    },
                }
            ]
        }
        return io.BytesIO(json.dumps(payload).encode())

    monkeypatch.setattr("src.llm_batch.request.urlopen", respond)
    assert analyze_entry("散歩", GeminiClient("test-secret", "gemini-test")).summary == "散歩"


@pytest.mark.parametrize(
    "provider,model", [("openai", "gemini-test"), ("gemini", "gpt-test"), ("openai", "../bad")]
)
def test_provider_model_mismatch(provider, model):
    with pytest.raises(ValueError):
        create_client(provider, model)


def test_analysis_rejects_nonobject():
    class Client:
        def complete_json(self, prompt):
            return []

    with pytest.raises(ValueError, match="JSON object"):
        analyze_entry("test", Client())
