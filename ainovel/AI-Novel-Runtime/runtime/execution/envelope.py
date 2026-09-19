"""envelope.py — Runtime-level draft envelope (ANES v2).

The Standard's ChapterDraft Artifact Contract seals every object with
`additionalProperties: false` (chapter-draft.schema.json), and ADR-007 freezes
the Standard. There is therefore NO schema-legal slot inside the draft for a
prompt-provenance block.

So evolution lives in the Runtime layer (per the architecture decision): on disk
we wrap the *unmodified* ChapterDraft in an envelope that also carries the
PromptManifest projection. The inner draft's bytes — and thus its `content_hash`
— are never touched, so:

  - Stage-3 output-contract validation still runs against the INNER draft and
    passes against the frozen schema.
  - Byte-reproducibility of the draft is preserved (live == replay).
  - The Standard is not edited and no registry hash is invalidated.

The envelope is a Runtime artifact, not a Standard contract. Consumers read
`envelope["draft"]` for the contract-conformant artifact and
`envelope["prompt_provenance"]` for the manifest linkage.
"""
from __future__ import annotations

from typing import Optional

ENVELOPE_FORMAT = "runtime-draft/1.0"


def prompt_provenance_block(manifest) -> dict:
    """Project a PromptManifest into the STABLE-hash provenance block.

    Only reproducible fields enter here (the three hashes + ids). Volatile
    manifest fields (rendered_at, cache_hit, replay_ref) are deliberately
    excluded so the envelope's prompt block is itself replay-stable, mirroring
    the inner draft's hash discipline. The full manifest is still persisted
    separately as its own derived artifact (run.py), and is linked by id here.
    """
    manifest_id = (
        f"{manifest.prompt_id}-{manifest.version}-"
        f"{manifest.rendered_hash.split(':', 1)[1][:16]}"
    )
    block = {
        "prompt_id": manifest.prompt_id,
        "version": manifest.version,
        "rendered_hash": manifest.rendered_hash,
        "template_hash": manifest.template_hash,
        "binding_hash": manifest.binding_hash,
        "manifest_id": manifest_id,
    }
    if getattr(manifest, "route_summary", None) is not None:
        block["route_summary"] = manifest.route_summary
    return block


def wrap(draft: dict, manifest, qa_review: Optional[dict] = None,
         revision_session: Optional[dict] = None,
         commercial_session: Optional[dict] = None,
         publish_readiness: Optional[dict] = None,
         director: Optional[dict] = None,
         hygiene_session: Optional[dict] = None,
         m7: Optional[dict] = None) -> dict:
    """Wrap an unmodified inner ChapterDraft + its manifest into an envelope.

    `draft` is passed through byte-for-byte (same dict identity of fields); the
    envelope adds sibling keys only. If `manifest` is None (no prompt runtime),
    prompt_provenance is null and the envelope still carries the draft.

    `qa_review` is the EVALUATIVE QA report (execution.draft_review), advisory and
    non-gating (ADR-003). It rides here, beside the draft, because the frozen
    Standard schema seals `produced_by` and has no slot for an evaluative block.

    `revision_session` is the Revision Controller's optimization record
    (execution.revision). Like qa_review it is advisory/non-gating and rides the
    envelope, never inside the frozen ChapterDraft schema. Absent for a plain
    (non-refined) draft.

    `commercial_session` is the Commercial Optimization Loop's record
    (execution.commercial) — reader-reaction-driven, comparison-only, non-gating
    (roadmap P16). Rides the envelope like the others; absent unless the
    commercial loop ran.

    `publish_readiness` is the 'Build Gate ≠ Publish Readiness' verdict
    (execution.publish_readiness, Phase 4.1) — a human-authority (ADR-009)
    production decision that NEVER gates the build (gates_build=false). Rides the
    envelope like the others; absent if publish readiness was not assessed.

    `hygiene_session` is the Prose Hygiene correction record (execution.prose_hygiene,
    §14.5) — deterministic density/ai_taste warnings driving a targeted rewrite,
    advisory and non-gating. Rides the envelope like the others; absent unless the
    hygiene loop ran.

    `director` is the Narrative Director audit block (execution._director_audit,
    Phase 6/7) — the objective/brief/critique/rewrite/selection provenance for the
    chapter. It is advisory and human-authority (ADR-009); it rides the envelope
    like the others and MUST NOT be injected into the inner ChapterDraft, whose
    frozen schema is additionalProperties:false (see the frozen-schema-envelope
    convention). Absent if the director audit was not produced.

    `m7` is the M7 originality + platform red-line assessment (execution.m7,
    M8-01) — the raw M7Result the publish decision consumed. It rides HERE as its
    own sibling rather than inside `publish_readiness`, because the frozen
    publish-readiness.schema.json is additionalProperties:false and has no `m7`
    slot; nesting it there would leave a schema-invalid readiness block on disk.
    publish_readiness still FOLDS the M7 verdict into its recommendation; this is
    the un-collapsed detail (similarity matches, red-line hits) for audit. Absent
    unless originality was assessed.
    """
    env = {
        "envelope_format": ENVELOPE_FORMAT,
        "prompt_provenance": prompt_provenance_block(manifest) if manifest else None,
        "qa_review": qa_review,
        "draft": draft,
    }
    if revision_session is not None:
        env["revision_session"] = revision_session
    if commercial_session is not None:
        env["commercial_session"] = commercial_session
    if publish_readiness is not None:
        env["publish_readiness"] = publish_readiness
    if director is not None:
        env["director"] = director
    if hygiene_session is not None:
        env["hygiene_session"] = hygiene_session
    if m7 is not None:
        env["m7"] = m7
    return env


def unwrap(obj: dict) -> dict:
    """Return the inner ChapterDraft from an envelope, or `obj` itself if it is
    already a bare draft (back-compat for pre-envelope files on disk)."""
    if isinstance(obj, dict) and obj.get("envelope_format") == ENVELOPE_FORMAT:
        return obj["draft"]
    return obj
