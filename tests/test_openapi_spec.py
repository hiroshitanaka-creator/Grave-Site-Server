from pathlib import Path

import yaml

from src.api.schema import contract


def test_committed_contract_matches_actual_application():
    stored = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / "openapi/gpts_actions.yaml").read_text()
    )
    assert stored == contract()


def test_all_message_endpoints_require_key_and_typed_errors():
    schema = contract()
    for path in schema["paths"].values():
        for operation in path.values():
            assert operation["security"] == [{"ApiKeyAuth": []}]
            for code in ("401", "409", "422", "500"):
                assert operation["responses"][code]["content"]["application/json"]["schema"] == {
                    "$ref": "#/components/schemas/ErrorResponse"
                }
