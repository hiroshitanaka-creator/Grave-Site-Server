from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_gpts_actions_openapi_spec_exists():
    spec_path = ROOT / "openapi" / "gpts_actions.yaml"
    assert spec_path.exists()


def test_gpts_actions_openapi_spec_contains_save_message_contract():
    spec = (ROOT / "openapi" / "gpts_actions.yaml").read_text(encoding="utf-8")

    assert "openapi: 3.1.0" in spec
    assert "/actions/save-message:" in spec
    assert "operationId: saveMessage" in spec
    assert "SaveMessageRequest" in spec
    assert "SaveMessageResponse" in spec
    assert "ApiKeyAuth" in spec
