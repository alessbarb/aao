"""Canonical loading and classification for the CEO-approved protected routes."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "aao.protected-routes.v1"
ORDER = {"R1": 1, "R2": 2, "R3": 3}
NORMATIVE_PATH = Path(__file__).resolve().parents[2] / "docs/protected-routes.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def validate_document(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        raise ValueError("protected routes schema is invalid")
    routes = document.get("routes")
    if not isinstance(routes, list) or not routes:
        raise ValueError("protected routes list is invalid")
    seen: set[str] = set()
    for entry in routes:
        if (not isinstance(entry, dict) or set(entry) != {"path", "minimum_risk_class"}
                or not isinstance(entry["path"], str) or not entry["path"]
                or entry["minimum_risk_class"] not in ORDER or entry["path"] in seen):
            raise ValueError("protected route entry is invalid")
        seen.add(entry["path"])
    if document.get("semantics") != {
        "directory": "entry ending in '/' covers everything below it",
        "exact": "any other entry is an exact path unless it contains '*'",
        "glob": "'*' matches any sequence without '/'; a pattern without '/' matches the basename in any directory",
        "paths_considered": "added, modified, deleted and both sides of renamed files",
        "overlap": "highest class wins; overlaps never lower a class",
    }:
        raise ValueError("protected routes semantics are invalid")
    return document


def load_document(path: Path = NORMATIVE_PATH) -> dict[str, Any]:
    return validate_document(json.loads(Path(path).read_text(encoding="utf-8")))


def route_map(document: dict[str, Any]) -> dict[str, str]:
    return {entry["path"]: entry["minimum_risk_class"] for entry in validate_document(document)["routes"]}


def routes_digest(routes: list[dict[str, str]] | dict[str, str]) -> str:
    if isinstance(routes, dict):
        values = [{"path": path, "minimum_risk_class": routes[path]} for path in sorted(routes)]
    else:
        values = sorted(routes, key=lambda entry: entry["path"])
    return hashlib.sha256(canonical(values)).hexdigest()


def compare_copies(normative: dict[str, Any], registry: dict[str, Any], operational: dict[str, Any]) -> None:
    """Raise a diagnostic naming the first divergent material copy."""
    expected = routes_digest(normative["routes"])
    for which, copy in (("registry", registry), ("operational", operational)):
        copied_routes = copy.get("protected_routes")
        digest = copy.get("protected_routes_sha256")
        if (not isinstance(copied_routes, dict) or copied_routes != route_map(normative)
                or digest != expected or routes_digest(copied_routes) != expected):
            raise ValueError(f"protected routes digest mismatch: {which}")


def matches(path: str, pattern: str) -> bool:
    if pattern.endswith("/"):
        return path.startswith(pattern)
    if "*" not in pattern:
        return path == pattern
    # The contract defines only '*'; do not accidentally enable fnmatch's '?'/class syntax.
    target = path.rsplit("/", 1)[-1] if "/" not in pattern else path
    expression = "".join("[^/]*" if char == "*" else re.escape(char) for char in pattern)
    return re.fullmatch(expression, target) is not None


def classify(paths: list[str], routes: dict[str, str]) -> str:
    level = "R1"
    for path in paths:
        for pattern, minimum in routes.items():
            if matches(path, pattern) and ORDER[minimum] > ORDER[level]:
                level = minimum
    return level
