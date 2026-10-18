from aao.pg_effects import EffectConflict, canonical_digest
import pytest


def test_digest_is_canonical():
    assert canonical_digest({"a": 1, "b": 2}) == canonical_digest({"b": 2, "a": 1})
    assert canonical_digest({"a": 1}) != canonical_digest({"a": 2})


def test_effect_conflict_type():
    assert isinstance(EffectConflict("blocked"), ValueError)
