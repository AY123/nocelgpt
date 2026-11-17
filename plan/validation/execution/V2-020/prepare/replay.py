"""Offline PREPARE experiment: checked prose + reviewed mapping -> draft handoff.

Not the Chapter Workflow application service, a semantic extractor, approval
validator or Canon writer. A mapping review binds bytes; it cannot establish that
its claims about prose are true. No model, database or acceptance API is used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from anovel.canon.identity import canonical_bytes
from anovel.domain.delta import FactBaseline, NarrativeDelta, preview_delta
from anovel.domain.identity import EntityId
from anovel.genre.extensions.registration import registered_extensions
from anovel.planning.models import StoryFixture

PREVIEW_REF = "user-authorized-local-preview-not-commit"


class ReplayError(ValueError):
    """A source, mapping or domain precondition is no longer satisfied."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReplayError(message)


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def byte_digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, value in pairs:
        require(name not in result, f"duplicate JSON field: {name}")
        result[name] = value
    return result


def _constant(value: str) -> None:
    raise ReplayError(f"nonfinite JSON constant: {value}")


def _decode(raw: bytes) -> Any:
    value = json.loads(
        raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant
    )
    # json.loads also accepts finite-looking exponents that overflow to inf.
    # Validate the complete tree, including nesting and Unicode scalars.
    canonical_bytes(value)
    return value


def load_json(path: Path) -> Any:
    return _decode(path.read_bytes())


def record(value: Any, keys: set[str], field: str) -> dict[str, Any]:
    require(type(value) is dict and set(value) == keys, f"malformed {field}")
    return value


def text(value: Any, field: str) -> str:
    require(type(value) is str and bool(value.strip()), f"missing {field}")
    return value


def sha(value: Any, field: str) -> str:
    require(
        type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
        f"malformed {field}",
    )
    return value


def items(value: Any, field: str) -> list[Any]:
    require(type(value) is list, f"malformed {field}")
    return value


def notes(value: Any) -> dict[str, str]:
    require(type(value) is dict and 0 < len(value) <= 64, "malformed notes")
    for key, item in value.items():
        text(key, "note name")
        text(item, "note value")
        require(len(item) <= 4000, "note too long")
    return value


def source(base: Path, ref: Any) -> Path:
    ref = record(ref, {"path", "sha256"}, "source")
    path = Path(text(ref["path"], "source path"))
    require(
        not path.is_absolute() and ".." not in path.parts, "source path must stay local"
    )
    result = (base / path).resolve()
    require(result.is_relative_to(base.resolve()), "source escapes its root")
    return result


def checked_bytes(base: Path, ref: Any) -> bytes:
    path = source(base, ref)
    raw = path.read_bytes()
    require(
        byte_digest(raw) == sha(ref["sha256"], "source hash"),
        f"stale source: {ref['path']}",
    )
    return raw


def span(value: Any, body: str, *, extra: set[str] | None = None) -> dict[str, Any]:
    value = record(value, {"start", "end", "quote"} | (extra or set()), "prose span")
    start, end = value["start"], value["end"]
    require(
        type(start) is int and type(end) is int and 0 <= start < end <= len(body),
        "invalid Unicode codepoint span",
    )
    quote = text(value["quote"], "prose quote")
    require(body[start:end] == quote, "prose quote does not match source")
    return value


def _review(raw: bytes, value: Any) -> None:
    value = record(
        value,
        {
            "kind",
            "schema_version",
            "sample_sha256",
            "reviewer",
            "review_basis",
            "decision",
            "limitations",
        },
        "mapping review",
    )
    require(
        value["kind"] == "PREPARE_MAPPING_REVIEW" and value["schema_version"] == "1.0",
        "unknown review format",
    )
    require(
        value["review_basis"] == "AI_TECHNICAL_REVIEW_NOT_HUMAN_GOLD"
        and value["decision"] == "SUITABLE_FOR_OFFLINE_REPLAY",
        "not a preparation mapping review",
    )
    text(value["reviewer"], "reviewer")
    require(
        bool(items(value["limitations"], "review limitations")),
        "review limitations missing",
    )
    for limitation in value["limitations"]:
        text(limitation, "review limitation")
    require(
        byte_digest(raw) == sha(value["sample_sha256"], "review sample hash"),
        "mapping changed; new review required",
    )


def replay(
    sample_path: Path, review_path: Path, *, repository_root: Path
) -> dict[str, Any]:
    """Replay an explicit reviewed mapping; never generate or re-approve one."""
    try:
        return _replay(sample_path, review_path, repository_root=repository_root)
    except ReplayError:
        raise
    except (ValueError, TypeError, KeyError, OSError) as exc:
        raise ReplayError(str(exc)) from exc


def _replay(
    sample_path: Path, review_path: Path, *, repository_root: Path
) -> dict[str, Any]:
    raw = sample_path.read_bytes()
    _review(raw, load_json(review_path))
    sample = record(
        _decode(raw),
        {
            "kind",
            "schema_version",
            "story",
            "branch",
            "parent_ref",
            "initial_notes",
            "steps",
        },
        "replay sample",
    )
    require(
        sample["kind"] == "DRAFT_REPLAY_SAMPLE" and sample["schema_version"] == "1.0",
        "unknown sample format",
    )
    story_path = source(repository_root, sample["story"])
    require(
        story_path.is_relative_to(
            (repository_root / "specs/fixtures/stories").resolve()
        ),
        "story must be a registered local story fixture",
    )
    fixture = StoryFixture.from_dict(
        _decode(checked_bytes(repository_root, sample["story"]))
    )
    root = fixture.root_seed
    baseline = FactBaseline.from_world_facts(
        fixture.project,
        text(sample["branch"], "branch"),
        text(sample["parent_ref"], "component parent"),
        root.facts,
        extensions=root.extensions,
    )
    registry = registered_extensions()
    registry.validate_baseline(baseline)
    current_notes = notes(sample["initial_notes"])
    boundaries = {
        boundary.fact_id: boundary.not_before for boundary in fixture.reader_boundaries
    }
    revealed: set[EntityId] = set()
    previous: str | None = None
    results: list[dict[str, Any]] = []
    last_ending: dict[str, Any] = {}
    for number, value in enumerate(items(sample["steps"], "steps"), start=1):
        step = record(
            value,
            {
                "chapter",
                "body",
                "previous_body_sha256",
                "before_sha256",
                "after_sha256",
                "delta",
                "operation_evidence",
                "notes_after",
                "notes_evidence",
                "ending",
                "revealed_facts",
            },
            "chapter step",
        )
        require(
            type(step["chapter"]) is int and step["chapter"] == number,
            "chapter order mismatch",
        )
        require(
            step["previous_body_sha256"] == previous,
            "previous candidate identity mismatch",
        )
        body_bytes = checked_bytes(sample_path.parent, step["body"])
        body = body_bytes.decode("utf-8")
        require(
            digest(baseline.to_dict()) == sha(step["before_sha256"], "before hash"),
            f"chapter {number}: complete preceding draft state mismatch",
        )
        evidence = items(step["operation_evidence"], "operation evidence")
        changes = 0
        if step["delta"] is None:
            require(not evidence, "carry step cannot have operation evidence")
        else:
            delta = NarrativeDelta.from_dict(step["delta"])
            by_operation: dict[str, Any] = {}
            for item in evidence:
                item = span(item, body, extra={"operation_id"})
                identity = text(item["operation_id"], "operation identity")
                require(identity not in by_operation, "duplicate operation evidence")
                by_operation[identity] = item
            require(
                set(by_operation) == {op.meta.id.local_id for op in delta.operations},
                "missing or extra operation evidence",
            )
            for operation in delta.operations:
                meta = operation.meta
                require(
                    meta.evidence.source_id == delta.source_id
                    and meta.evidence.position.chapter == number,
                    "operation prose source/chapter mismatch",
                )
                require(
                    meta.authorization_ref == PREVIEW_REF,
                    "not an isolated draft preview reference",
                )
            candidate = preview_delta(
                baseline,
                delta,
                source_id=delta.source_id,
                authorization_refs=frozenset({PREVIEW_REF}),
                extension_registry=registry,
            )
            baseline, changes = candidate.candidate, len(candidate.changes)
        require(
            digest(baseline.to_dict()) == sha(step["after_sha256"], "after hash"),
            f"chapter {number}: returned candidate state mismatch",
        )
        after_notes = notes(step["notes_after"])
        require(set(after_notes) == set(current_notes), "note fields must be preserved")
        changed_notes = {
            field
            for field in current_notes
            if current_notes[field] != after_notes[field]
        }
        covered: set[str] = set()
        for item in items(step["notes_evidence"], "note evidence"):
            item = span(item, body, extra={"field"})
            field = text(item["field"], "note field")
            require(field not in covered, "duplicate note evidence")
            covered.add(field)
        require(
            covered == changed_notes,
            "changed notes require exactly matching current prose evidence",
        )
        for item in items(step["revealed_facts"], "revealed facts"):
            item = span(item, body, extra={"fact_id"})
            fact_id = EntityId.from_dict(item["fact_id"])
            require(
                fact_id in boundaries and fact_id not in revealed,
                "unknown or repeated reveal",
            )
            require(
                (number, 1) >= (boundaries[fact_id].chapter, boundaries[fact_id].order),
                "fact revealed before reader boundary",
            )
            revealed.add(fact_id)
        ending = span(step["ending"], body)
        require(
            ending["end"] == len(body), "ending must be the actual candidate suffix"
        )
        previous = byte_digest(body_bytes)
        last_ending = {**ending, "body_sha256": previous}
        current_notes = after_notes
        results.append(
            {
                "chapter": number,
                "body_sha256": previous,
                "before_sha256": step["before_sha256"],
                "after_sha256": step["after_sha256"],
                "changed_fact_count": changes,
                "notes": dict(current_notes),
            }
        )
    require(bool(results), "at least one completed draft step is required")
    visible = [
        {
            "id": item.seed_fact.id.to_dict(),
            "subject": item.seed_fact.proposition.subject.to_dict(),
            "predicate": item.seed_fact.proposition.predicate,
            "state": item.state.to_dict(),
            "revision": item.revision,
        }
        for item in baseline.facts
        if item.seed_fact.id not in boundaries or item.seed_fact.id in revealed
    ]
    return {
        "kind": "OFFLINE_DRAFT_REPLAY",
        "status": "STRUCTURAL_REPLAY_PASS",
        "sample_sha256": byte_digest(raw),
        "project": fixture.project,
        "steps": results,
        "limitations": [
            "Explicit reviewed mapping, not automatic prose verification or human reading evidence.",
            "Draft candidate only; no accepted chapter, Canon commit, Permit or Provider execution.",
        ],
        "next_writer_input": {
            "kind": "WINDOW_DRAFT_CONTEXT",
            "chapter": len(results) + 1,
            "notes": current_notes,
            "actual_ending": last_ending,
            "visible_facts": visible,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    here = Path(__file__).resolve().parent
    parser.add_argument(
        "--sample", type=Path, default=here / "samples/urban/replay.json"
    )
    parser.add_argument(
        "--review", type=Path, default=here / "samples/urban/review.json"
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="New directory outside plan/src/.git"
    )
    args = parser.parse_args()
    repository_root = here.parents[4]
    try:
        destination = args.output.resolve()
        require(
            not any(
                destination.is_relative_to(repository_root / part)
                for part in ("plan", "src", ".git")
            ),
            "output must stay outside plan/src/.git",
        )
        require(not destination.exists(), "output directory already exists")
        result = replay(args.sample, args.review, repository_root=repository_root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.mkdir()
        for name, value in (
            ("replay-report.json", result),
            ("next-writer-input.json", result["next_writer_input"]),
        ):
            (destination / name).write_bytes(canonical_bytes(value))
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "chapters": len(result["steps"]),
                    "output": str(destination),
                },
                ensure_ascii=False,
            )
        )
        return 0
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(
            json.dumps(
                {"status": "REPLAY_REJECTED", "reason": str(exc)}, ensure_ascii=False
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
