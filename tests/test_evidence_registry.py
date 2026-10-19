import hashlib

import pytest

from aao.evidence_registry import EvidenceDenied, verify_evidence_references


class EvidenceDb:
    def __init__(self, content, media_type="text/plain"):
        self.content = content
        self.media_type = media_type

    def execute(self, query, params):
        assert "project_id=%s AND digest=%s" in query
        assert params[0] == "project-1"
        if params[1] != hashlib.sha256(self.content).hexdigest():
            return Result(None)
        return Result((self.content, self.media_type))


class Result:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


def test_verifies_project_scoped_artifact_bytes_and_returns_descriptor():
    content = b"evidence bytes"
    reference = "sha256:" + hashlib.sha256(content).hexdigest()

    assert verify_evidence_references(EvidenceDb(content), "project-1", [reference]) == [
        {"reference": reference, "size_bytes": len(content), "media_type": "text/plain"}
    ]


@pytest.mark.parametrize(
    "references", [[], ["operator checked"], [None], [["nested"]], ["sha256:" + "a" * 64] * 33]
)
def test_rejects_missing_or_malformed_evidence_references(references):
    with pytest.raises(EvidenceDenied):
        verify_evidence_references(EvidenceDb(b"evidence bytes"), "project-1", references)


def test_rejects_duplicate_evidence_references():
    content = b"evidence bytes"
    reference = "sha256:" + hashlib.sha256(content).hexdigest()
    with pytest.raises(EvidenceDenied, match="Unique"):
        verify_evidence_references(EvidenceDb(content), "project-1", [reference, reference])
