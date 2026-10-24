from __future__ import annotations

import copy
import json

import pytest

from aao import protected_routes, r1_pipeline


@pytest.fixture
def normative():
    return protected_routes.load_document()


def _copy(routes):
    routes = dict(routes)
    return {"protected_routes": routes, "protected_routes_sha256": protected_routes.routes_digest(routes)}


@pytest.mark.nt("NT-01-1")
def test_added_route_divergence_rejects(normative):
    base = _copy(protected_routes.route_map(normative))
    registry = copy.deepcopy(base)
    registry["protected_routes"]["new-policy-file"] = "R3"
    registry["protected_routes_sha256"] = protected_routes.routes_digest(registry["protected_routes"])
    with pytest.raises(ValueError, match="protected routes digest mismatch: registry"):
        protected_routes.compare_copies(normative, registry, base)


@pytest.mark.nt("NT-01-2")
def test_removed_route_divergence_rejects(normative):
    base = _copy(protected_routes.route_map(normative))
    operational = copy.deepcopy(base)
    operational["protected_routes"].pop(next(iter(operational["protected_routes"])))
    operational["protected_routes_sha256"] = protected_routes.routes_digest(operational["protected_routes"])
    with pytest.raises(ValueError, match="protected routes digest mismatch: operational"):
        protected_routes.compare_copies(normative, base, operational)


@pytest.mark.nt("NT-01-3")
def test_changed_class_divergence_rejects(normative):
    base = _copy(protected_routes.route_map(normative))
    changed = copy.deepcopy(base)
    path = next(iter(changed["protected_routes"]))
    changed["protected_routes"][path] = "R1"
    changed["protected_routes_sha256"] = protected_routes.routes_digest(changed["protected_routes"])
    with pytest.raises(ValueError, match="protected routes digest mismatch: registry"):
        protected_routes.compare_copies(normative, changed, base)


@pytest.mark.nt("NT-01-4")
def test_overlapping_higher_pattern_controls_classification():
    assert protected_routes.classify(["docs/GOV-REV-002x"], {
        "docs/GOV-REV-002*": "R3", "*": "R2",
    }) == "R3"
    assert protected_routes.classify(["docs/GOV-REV-002x"], {"*": "R2"}) == "R2"


@pytest.mark.nt("NT-01-4")
def test_overlapping_route_added_to_only_one_copy_fails_closed(normative):
    registry = _copy(protected_routes.route_map(normative))
    operational = _copy(protected_routes.route_map(normative))
    changed = copy.deepcopy(normative)
    changed["routes"].append({"path": "docs/GOV-REV-*", "minimum_risk_class": "R3"})
    with pytest.raises(ValueError, match="protected routes digest mismatch: registry"):
        protected_routes.compare_copies(changed, registry, operational)


@pytest.mark.nt("NT-01-5")
@pytest.mark.parametrize("divergent_copy,reason", [
    ("registry", "registry"), ("operational", "operational"), ("normative", "registry"),
])
def test_every_pairwise_copy_divergence_rejects(normative, divergent_copy, reason):
    routes = protected_routes.route_map(normative)
    registry, operational = _copy(routes), _copy(routes)
    candidate_normative = copy.deepcopy(normative)
    if divergent_copy == "registry":
        registry["protected_routes_sha256"] = "0" * 64
    elif divergent_copy == "operational":
        operational["protected_routes"]["extra"] = "R3"
    else:
        candidate_normative["routes"].append({"path": "extra-route", "minimum_risk_class": "R3"})
    with pytest.raises(ValueError, match=f"protected routes digest mismatch: {reason}"):
        protected_routes.compare_copies(candidate_normative, registry, operational)


class _CheckClient:
    def __init__(self, app_id):
        self.app_id = app_id

    def request(self, method, path, body=None):
        return {"check_runs": [{"id": 1, "name": "test", "status": "completed", "conclusion": "success",
                                "app": {"id": self.app_id}}]}


@pytest.mark.nt("NT-02-5")
def test_production_required_check_requires_authorized_publisher():
    allowed = {"test": [15368]}
    assert r1_pipeline._check_passed(_CheckClient(999), "org/repo", "a" * 40, "test", allowed) == (
        False, "required check publisher is unauthorized: test")
    assert r1_pipeline._check_passed(_CheckClient(15368), "org/repo", "a" * 40, "test", allowed) == (True, "passed")


class _AttributionClient:
    def __init__(self, events):
        self.events = events

    def installation_token(self, *_args):
        return "opaque-test-token"

    def request(self, method, path):
        return self.events


@pytest.mark.nt("NT-02-3")
@pytest.mark.nt("NT-02-10")
def test_supervisor_resolves_only_unique_exact_push_principals(tmp_path):
    from aao.supervisor_service import attribution

    known_sha, other_sha = "a" * 40, "b" * 40
    events = [
        {"type": "PushEvent", "actor": {"login": "aao-impl-codex[bot]"},
         "payload": {"commits": [{"sha": known_sha}]}},
        {"type": "PushEvent", "actor": {"login": "aao-pm[bot]"},
         "payload": {"commits": [{"sha": other_sha}]}},
    ]
    path = tmp_path / "attribution.json"
    config = {"repository": "org/repo", "attribution_path": str(path),
              "push_principals": {"aao-impl-codex[bot]": "codex", "aao-impl-claude[bot]": "claude"}}
    assert attribution(config, _AttributionClient(events)) == 1
    data = json.loads(path.read_text())
    assert data["candidates"] == {known_sha: ["aao-impl-codex[bot]"]}
    assert "aao-pm[bot]" not in json.dumps(data)

