"""Evidence readback for the author’s saved whole-chapter Drafts."""

from __future__ import annotations

import re
from base64 import b64encode
from dataclasses import dataclass, field
from hashlib import sha256

from anovel.canon.identity import canonical_bytes
from anovel.domain.identity import EntityId

from .extractor import (
    POLICY_HASH,
    ExactSpan,
    ExtractionDiagnostic,
    ExtractionObservation,
    ExtractionSegment,
    audit_extraction_evidence,
    discover_extraction_evidence,
)
from .models import WorkflowError
from .written_draft import WrittenDraftRevision

# A cue brings the full surrounding paragraph to the author for review. It
# never confirms an event, a belief's truth, or an operation on a world fact.
_CUE_PATTERNS = {
    "RUMOR": r"听说|据说|传闻",
    "BELIEF": r"以为|误信|误以为",
    "INTENTION": r"打算|原本想|本来想|准备|刚要",
    "CALL_RESPONSE": r"一接(?:起)?(?:电话)?就(?:问|说)|挂了电话",
    "CALL_DEFERRAL": r"(?:回|打|拨)[^。！？\r\n]{0,8}电话[^。！？\r\n]{0,16}(?:拖到|推迟|没拨|还没回)",
}
_CUES = {kind: re.compile(pattern) for kind, pattern in _CUE_PATTERNS.items()}
_WRITTEN_POLICY_HASH = sha256(
    canonical_bytes(
        {
            "profile": "written-draft-extraction/1.0",
            "finite_extraction_policy": POLICY_HASH,
            "cue_scope": "NONEMPTY_RAW_LINES_FOR_EDITORIAL_REVIEW",
            "cue_patterns": _CUE_PATTERNS,
        }
    )
).hexdigest()


@dataclass(frozen=True, slots=True)
class WrittenDraftExtraction:
    """Finite facts and editorial evidence traced to one immutable revision."""

    revision: WrittenDraftRevision = field(repr=False)
    root_observation_hash: str
    proposal_raw: bytes = field(repr=False)
    inventory_raw: bytes = field(repr=False)
    coverage: tuple[ExtractionSegment, ...] = field(repr=False)
    diagnostics: tuple[ExtractionDiagnostic, ...] = field(repr=False)
    facts: tuple[ExtractionSegment, ...] = field(repr=False)
    cues: tuple[ExtractionDiagnostic, ...] = field(repr=False)

    @property
    def inventory_hash(self) -> str:
        return sha256(self.inventory_raw).hexdigest()

    @property
    def correspondence_status(self) -> str:
        states = {item.state for item in self.diagnostics}
        return next(
            (state for state in ("ERROR", "FAIL", "UNKNOWN") if state in states), "PASS"
        )

    def _metadata(self) -> dict[str, object]:
        source = self.revision
        return {
            "record_type": "written_draft_extraction",
            "schema_version": "1.0",
            "state": "WRITTEN_DRAFT_EXTRACTION_INSPECTED",
            "artifact_state": "DRAFT",
            "project": source.project,
            "branch": source.branch,
            "run_id": source.run_id,
            "chapter_id": source.chapter_id.to_dict(),
            "version": source.version,
            "source_revision_hash": source.record_hash,
            "prose_hash": source.prose_hash,
            "input_hash": source.input_hash,
            "root_observation_hash": self.root_observation_hash,
            "policy_hash": _WRITTEN_POLICY_HASH,
            "inventory_hash": self.inventory_hash,
            "proposal_hash": sha256(self.proposal_raw).hexdigest(),
            "correspondence_status": self.correspondence_status,
            "semantic_status": "UNKNOWN",
            "segment_count": len(self.coverage),
            "fact_count": len(self.facts),
            "cue_count": len(self.cues),
            "diagnostic_count": len(self.diagnostics),
            "can_commit": False,
            "can_issue_permit": False,
            "can_dispatch": False,
            "accepted": False,
            "published": False,
        }

    def _detail(self) -> dict[str, object]:
        source = self.revision
        choice = source.choice
        return {
            "coverage": [item.to_dict() for item in self.coverage],
            "diagnostics": [item.to_dict() for item in self.diagnostics],
            "facts": [item.to_dict() for item in self.facts],
            "cues": [
                {"kind": item.code, "state": item.state, "span": item.span.to_dict()}
                for item in self.cues
                if item.span is not None
            ],
            "editorial_evidence": {
                "choice": None
                if choice is None
                else ExactSpan.from_source(
                    source.prose, choice.start, choice.end
                ).to_dict(),
                "continuity": [
                    note.to_dict()
                    | {
                        "span": ExactSpan.from_source(
                            source.prose, note.span.start, note.span.end
                        ).to_dict()
                    }
                    for note in source.continuity
                ],
            },
            "proposal_raw_base64": b64encode(self.proposal_raw).decode("ascii"),
            "inventory_raw_base64": b64encode(self.inventory_raw).decode("ascii"),
        }

    def to_dict(self) -> dict[str, object]:
        record = self._metadata() | self._detail()
        return record | {
            "observation_hash": sha256(canonical_bytes(record)).hexdigest()
        }

    def summary(self) -> dict[str, object]:
        metadata = self._metadata()
        observation_hash = sha256(
            canonical_bytes(metadata | self._detail())
        ).hexdigest()
        return metadata | {"observation_hash": observation_hash}

    def payload_bytes(self) -> bytes:
        return canonical_bytes(self.to_dict())


def extract_written_draft(
    revision: WrittenDraftRevision, root: ExtractionObservation
) -> WrittenDraftExtraction:
    """Audit the original UTF-8 independently of author notes and chapter plans."""
    prose, catalog = revision.prose, root.catalog
    try:
        proposal, inventory = discover_extraction_evidence(prose, catalog)
        coverage, diagnostics = audit_extraction_evidence(
            prose, catalog, proposal, inventory
        )
    except (KeyError, TypeError, ValueError) as error:
        raise WorkflowError("INVALID_WRITTEN_DRAFT_EXTRACTION") from error
    latest_facts: dict[EntityId, ExtractionSegment] = {}
    if not any(item.state in {"FAIL", "ERROR"} for item in diagnostics):
        # Preserve all operations in coverage. Adjacent Draft generation uses
        # the last observed value only, never a committed world state.
        for item in coverage:
            if item.kind == "ACTUAL" and item.fact_id is not None:
                latest_facts[item.fact_id] = item
    cues: list[ExtractionDiagnostic] = []
    for line in re.finditer(r"[^\r\n]+", prose.decode("utf-8")):
        kinds = [kind for kind, pattern in _CUES.items() if pattern.search(line[0])]
        if kinds:
            span = ExactSpan.from_source(prose, line.start(), line.end())
            cues.extend(ExtractionDiagnostic(kind, "UNKNOWN", span) for kind in kinds)
    return WrittenDraftExtraction(
        revision,
        root.record_hash,
        proposal,
        inventory,
        coverage,
        diagnostics,
        tuple(latest_facts.values()),
        tuple(cues),
    )
