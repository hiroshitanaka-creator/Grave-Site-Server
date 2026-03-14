from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_spec_text() -> str:
    return (ROOT / "openapi" / "gpts_actions.yaml").read_text(encoding="utf-8")


def test_gpts_actions_openapi_spec_exists():
    spec_path = ROOT / "openapi" / "gpts_actions.yaml"
    assert spec_path.exists()


def test_gpts_actions_openapi_spec_contains_save_message_contract():
    spec = _load_spec_text()

    assert "openapi: 3.1.0" in spec
    assert "/actions/save-message:" in spec
    assert "operationId: saveMessage" in spec
    assert "ApiKeyAuth" in spec


def test_gpts_actions_openapi_spec_defines_required_http_responses():
    spec = _load_spec_text()

    for status in ("'200':", "'400':", "'401':", "'500':"):
        assert status in spec


def test_gpts_actions_openapi_spec_defines_request_and_response_schemas():
    spec = _load_spec_text()

    assert "SaveMessageRequest:" in spec
    assert "SaveMessageResponse:" in spec
    assert "ErrorResponse:" in spec

    # SaveMessageRequest fields
    assert "- recipient" in spec
    assert "- message" in spec
    assert "- date" in spec

    # SaveMessageResponse fields
    assert "- saved" in spec
    assert "- storage_type" in spec
    assert "- record_id" in spec
