"""Minimal type-specific contract requirements for registered capabilities."""

REQUIRED_CONTRACT_FIELDS = {
    "cli_script": {"purpose", "entrypoint", "inputs", "outputs", "platform"},
    "library": {"purpose", "import_name", "inputs", "outputs", "platform"},
    "application_service": {"purpose", "endpoint", "authentication", "inputs", "outputs"},
    "agent": {"purpose", "compatible_roles", "inputs", "outputs", "authority_boundary"},
    "agent_skill": {
        "purpose", "compatible_roles", "inputs", "outputs", "usage_limits",
    },
    "knowledge_procedure": {"purpose", "procedure", "inputs", "outputs", "applicability"},
    "workflow": {"purpose", "trigger", "steps", "inputs", "outputs"},
}


def missing_contract_fields(capability_type: str, contract: dict) -> set[str]:
    """Return fields absent from a type's minimum contract; does not assess truth."""
    required = REQUIRED_CONTRACT_FIELDS.get(capability_type)
    if required is None:
        return {"<known capability type>"}
    return {field for field in required if field not in contract or contract[field] is None}
