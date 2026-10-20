import pytest

from aao.capability_contracts import REQUIRED_CONTRACT_FIELDS, missing_contract_fields


@pytest.mark.parametrize("capability_type,required", REQUIRED_CONTRACT_FIELDS.items())
def test_each_capability_type_has_a_distinct_minimum_contract(capability_type, required):
    assert missing_contract_fields(capability_type, {field: "declared" for field in required}) == set()
    assert missing_contract_fields(capability_type, {}) == required


def test_unknown_type_fails_closed():
    assert missing_contract_fields("unknown", {}) == {"<known capability type>"}


def test_empty_contract_values_are_not_treated_as_declarations():
    assert missing_contract_fields(
        "agent_skill",
        {
            "purpose": "skill",
            "compatible_roles": [],
            "inputs": ["task"],
            "outputs": ["evidence"],
            "usage_limits": ["project scope"],
        },
    ) == {"compatible_roles"}
