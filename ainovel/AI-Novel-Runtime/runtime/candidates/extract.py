"""extract.py — extraction seam for the Fact Candidate Pipeline.

Extraction reads a produced ChapterDraft (derived prose) and proposes RAW
candidate facts — the assertions the prose makes about entities. This is the
ONE evaluative step in the pipeline (a model reading natural language); it never
gates. The deterministic reconciler (reconcile.py) is what turns raw candidates
into a governable, reproducible classification.

DISCIPLINE — mirrors runtime/scene/llm_planner.py and runtime/market/analyzer.py:
  - A DeterministicExtractor gives the pipeline a non-network, byte-reproducible
    default so CI proves the extract→reconcile→stage loop closes without secrets.
    It draws candidates ONLY from the draft's own provenance pins and structured
    metadata — it does NOT parse prose (that is the LLM's job), so it never
    fabricates a fact the artifact doesn't already carry.
  - An LLMExtractor drops in behind the same `extract(draft) -> [RawCandidate]`
    shape. It reads the prose body and proposes candidates with evidence spans.
    On any model failure it degrades to zero candidates (advisory, never gates).
  - Neither writes anything. Both return raw candidates for the reconciler.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from ..execution.quality_center import _extract_json
from .reconcile import RawCandidate


class DeterministicExtractor:
    """CI-runnable, no network, byte-reproducible.

    It proposes one `consistent`-seeking candidate per entity the draft was
    derived from: 'the prose used CHR-00001, so its declared identity is
    re-asserted.' This exercises the whole loop deterministically and, once
    reconciled, yields `consistent`/`additive` items — never a fabricated
    `conflicting`, because a stub must not invent contradictions it cannot read.
    """

    model_id = "deterministic-extractor-v1"

    def extract(self, draft: dict, known_entities=None,
                declared_fields=None) -> List[RawCandidate]:
        # known_entities / declared_fields are accepted for a uniform call
        # signature with LLMExtractor; the deterministic path draws only from
        # provenance pins and asserts 'status', always a declared field.
        pins = draft.get("provenance", {}).get("derived_from", []) or []
        out: List[RawCandidate] = []
        for pin in pins:
            entity_id = pin.split("@", 1)[0]
            type_code = entity_id.split("-", 1)[0]
            out.append(RawCandidate(
                target_type=_TYPE_BY_CODE.get(type_code, type_code),
                field="status",
                value="active",
                evidence=f"draft {draft.get('task_id', '?')} was derived from {pin}",
                matched_entity_id=entity_id,
                confidence=1.0,
                reason="deterministic re-assertion from draft provenance pin",
            ))
        return out


# Minimal code→type map for the stub's provenance-only candidates. The LLM
# extractor names its own target_type; this is only for the deterministic path.
_TYPE_BY_CODE = {
    "CHR": "Character",
    "EVT": "Event",
    "TML": "Timeline",
    "MAG": "WorldRule",
    "ITM": "Item",
    "REL": "Relationship",
}


_EXTRACT_TEMPLATE = """# 角色
你是一名严谨的网文设定编辑。你的任务是从一章正文里，抽取正文明确断言的、关于已知
角色/事件/世界规则的【事实候选】，交给人工核对是否写入设定库。你只抽取正文明确写出
的内容，绝不推测、绝不脑补。

# 本章正文
{body}

# 本章涉及的已知实体（正文里出现同一人/物/事时，务必回填其编号）
下面每行是一个已入库的实体：`编号 | 类型 | 名称（及别名）`。
正文里的人物/事物若与某个已知实体是【同一个】（哪怕名字是中译名、简称、别称、
译法不同），都必须把该断言的 matched_entity_id 填成对应编号——这是最重要的一步。
只有当正文引入的对象在下表中确实【找不到】对应实体时，matched_entity_id 才留空。
{entities}

# 各类型允许的字段（务必只用下列字段名，禁止自造）
每个 target_type 只能断言下列已声明字段之一；不要发明新字段名（例如用
`possessions` 而非 `possession`、`summary` 而非 `description`、`statement` 而非
`rule`）。若正文写的内容找不到对应的合法字段，就【不要抽取】该条。
`physical_facts` 这类字段可按具体属性写成 `physical_facts.<属性名>`。
{declared_fields}

# 任务
逐条抽取正文明确断言的事实，每条包含：
  - target_type：Character / Event / WorldRule / Item / Relationship 之一
  - matched_entity_id：若与上表某实体是同一个，填其编号（务必回填，勿因中译名/
    别称不同而漏填）；正文引入的、上表确实没有的新对象才留空
  - field：断言的字段，【必须】取自上面该类型的允许字段清单
  - value：正文断言的值
  - evidence：支撑该断言的正文原句（简短引用）
  - confidence：0-1，你对“正文确实这样写”的把握
只抽取正文明确写出的事实。正文没写的，一律不抽。宁可少抽，不可编造。
字段名不在允许清单里的，一律不要抽取（宁可漏，不可造字段）。
注意：只判断“正文写的对象是不是上表里的实体”，不要判断该字段的值是否与设定库一致——
值的比对由系统完成，你只负责如实抽取正文写了什么、并正确回填编号。

# 输出
严格只输出一个 JSON 对象，不要解释、不要 markdown 代码块：
{{
  "candidates": [
    {{"target_type": "Character", "matched_entity_id": "CHR-xxxxx 或空",
      "field": "physical_facts.eye_color", "value": "amber",
      "evidence": "……原句……", "confidence": 0.0}}
  ]
}}

# 失败兜底
无法处理时输出 {{"candidates": []}}，系统会当作本章无候选。"""


# structural/meta fields prose never asserts as a fact — excluded from the
# "allowed fields" the extractor may target.
_NON_ASSERTABLE_FIELDS = frozenset({"id", "fact_version", "certainty"})


def declared_fields_by_type(schema_dir, catalog=None) -> dict:
    """Read each entity schema's ASSERTABLE property names into
    {type_name: [fields]}. I/O helper (kept out of the pure extract path — the
    caller builds it once and threads it into build_extract_prompt), mirroring
    reconcile.build_field_constraints / normalize._field_shapes.

    Why this exists: without a declared-field list the LLM invents near-miss
    field names (possessions→possession, summary→description, statement→rule),
    which frozen `additionalProperties:false` schemas reject at mint — the
    dominant un-mintable cause the CLOSE-15 real run found. Handing the model the
    real slot names steers it onto them (prevention, not post-hoc dropping)."""
    from ..catalog import Catalog
    cat = catalog if isinstance(catalog, Catalog) else Catalog.load(schema_dir)
    out: dict = {}
    for type_code in cat.type_codes():
        entity = cat.entity_name(type_code)
        if entity in out:
            continue
        schema_path = Path(schema_dir) / cat.schema_file(type_code)
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        fields = [f for f in (schema.get("properties") or {})
                  if f not in _NON_ASSERTABLE_FIELDS]
        if fields:
            out[entity] = fields
    return out


def _render_declared_fields(declared: dict) -> str:
    """One line per entity type: `Type：field1, field2, …`. Object-typed fields
    (physical_facts) may also be asserted per-key as `physical_facts.<key>`."""
    if not declared:
        return "（未提供字段约束；沿用示例字段）"
    lines = []
    for entity in sorted(declared):
        lines.append(f"- {entity}：{', '.join(declared[entity])}")
    return "\n".join(lines)


def entity_roster(reg, entity_ids: List[str]) -> List[dict]:
    """Build the extractor's view of known entities: IDENTITY only (id, type,
    name, aliases) — deliberately NOT the declared field values.

    This is the load-bearing discipline of the fix. The model needs names to
    resolve '埃德里克·万斯' back to CHR-00001 (the roster gives it that), but it
    must NOT see the declared eye_color/age/etc., because value comparison is the
    deterministic reconciler's job. Leaking declared values into the prompt would
    let the model pre-judge consistent/conflicting and destroy the pipeline's
    reproducibility (same prose + same registry ⇒ same classification)."""
    roster: List[dict] = []
    for eid in entity_ids:
        rec = reg.get(eid) if hasattr(reg, "get") else None
        if not rec:
            roster.append({"id": eid, "type": eid.split("-", 1)[0], "name": None,
                           "aliases": []})
            continue
        aliases = [a for a in (rec.get("aliases") or []) if isinstance(a, str)]
        roster.append({
            "id": eid,
            "type": eid.split("-", 1)[0],
            "name": rec.get("name"),
            "aliases": aliases,
        })
    return roster


def _render_roster(roster: List[dict]) -> str:
    """One line per entity: `编号 | 类型 | 名称（别名1、别名2）`. Identity only."""
    if not roster:
        return "（无）"
    lines = []
    for e in roster:
        name = e.get("name") or "（未命名）"
        aliases = e.get("aliases") or []
        alias_str = f"（别名：{'、'.join(aliases)}）" if aliases else ""
        lines.append(f"{e['id']} | {e['type']} | {name}{alias_str}")
    return "\n".join(lines)


def build_extract_prompt(draft: dict, known_entities=None, declared_fields=None) -> str:
    """Render a draft body + its known entities into the extraction prompt.

    `known_entities` may be a roster (list of {id,name,aliases,type} dicts, the
    intended form — carries names so the model can resolve them) or, for backward
    compatibility, a plain list of id strings. When absent, it falls back to the
    draft's provenance-pin ids (id-only, the old behavior — a degraded view).

    `declared_fields` ({type_name: [fields]}, from declared_fields_by_type)
    constrains the model to real schema slots so it stops inventing near-miss
    field names. Absent, the prompt keeps the old example-only guidance
    (backward-compatible; the block reads '未提供字段约束')."""
    if known_entities is None:
        pins = draft.get("provenance", {}).get("derived_from", []) or []
        roster = [{"id": p.split("@", 1)[0], "type": p.split("-", 1)[0],
                   "name": None, "aliases": []} for p in pins]
    elif known_entities and isinstance(known_entities[0], dict):
        roster = known_entities
    else:  # legacy: list of id strings
        roster = [{"id": e, "type": e.split("-", 1)[0], "name": None, "aliases": []}
                  for e in known_entities]
    return _EXTRACT_TEMPLATE.format(
        body=draft.get("body", "") or "（无正文）",
        entities=_render_roster(roster),
        declared_fields=_render_declared_fields(declared_fields or {}),
    )


class LLMExtractor:
    """Reads the prose body and proposes candidate facts with evidence spans.

    Depends only on the execution Model protocol (model.generate(prompt) -> obj
    with .text/.model_id), same seam as LLMScenePlanner. On any failure it
    degrades to zero candidates — the pipeline stays advisory and never gates.
    """

    def __init__(self, model, *, extractor_id: str = "fact-extractor-v1"):
        self.model = model
        self.extractor_id = extractor_id

    @property
    def model_id(self) -> str:
        return getattr(self.model, "model_id", self.extractor_id)

    def extract(self, draft: dict, known_entities=None,
                declared_fields=None) -> List[RawCandidate]:
        # last_error lets a caller tell a swallowed failure (timeout, 4xx, bad
        # JSON) apart from a genuine empty extraction — both still return [] so
        # the reflow stays advisory and never gates (ADR-003), but the reason is
        # no longer invisible (the timeout-as-0-candidates trap CLOSE-15 hit).
        self.last_error = None
        try:
            output = self.model.generate(
                build_extract_prompt(draft, known_entities, declared_fields))
            parsed = _extract_json(getattr(output, "text", "")) or {}
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            return []

        out: List[RawCandidate] = []
        for c in parsed.get("candidates", []):
            if not isinstance(c, dict):
                continue
            field = c.get("field")
            target_type = c.get("target_type")
            if not (isinstance(field, str) and field.strip()
                    and isinstance(target_type, str) and target_type.strip()):
                continue
            # belt-and-suspenders on top of the declared-field prompt block: for
            # a near-miss field name (singular/plural, a known synonym) map it
            # onto the real schema slot; only DROP when no declared field matches
            # at all. Correcting rather than dropping keeps the outcome robust to
            # temp=0 nondeterminism (the model occasionally emits `possession`
            # instead of `possessions`) — an invented field still never reaches mint.
            field = field.strip()
            if declared_fields:
                allowed = declared_fields.get(target_type.strip())
                if allowed is not None:
                    corrected = _coerce_field(field, allowed)
                    if corrected is None:
                        continue
                    field = corrected
            matched = c.get("matched_entity_id")
            out.append(RawCandidate(
                target_type=target_type.strip(),
                field=field,
                value=c.get("value"),
                evidence=(c.get("evidence") or "").strip(),
                matched_entity_id=matched.strip() if isinstance(matched, str) and matched.strip() else None,
                confidence=_confidence(c.get("confidence")),
                reason="extracted from prose by model",
            ))
        return out


def _coerce_field(field: str, allowed: List[str]) -> Optional[str]:
    """Map a model-supplied field onto a real declared slot, or None if none fits.

    Preserves a dotted leaf's suffix (physical_facts.eye_color) as long as the
    object prefix is declared. Matching order: exact top-level → case-insensitive
    → singular/plural near-miss (possession↔possessions). Deterministic; never
    invents a slot the schema does not declare."""
    top, _, leaf = field.partition(".")
    allowed_set = set(allowed)
    if top in allowed_set:
        return field
    lower = {a.lower(): a for a in allowed}
    if top.lower() in lower:
        real = lower[top.lower()]
        return f"{real}.{leaf}" if leaf else real
    # singular/plural near-miss in either direction: -s, y→ies (ability→abilities)
    variants = [top + "s", top.rstrip("s")]
    if top.endswith("y"):
        variants.append(top[:-1] + "ies")
    if top.endswith("ies"):
        variants.append(top[:-3] + "y")
    for cand in variants:
        if cand in allowed_set:
            return f"{cand}.{leaf}" if leaf else cand
        if cand.lower() in lower:
            real = lower[cand.lower()]
            return f"{real}.{leaf}" if leaf else real
    return None


def _confidence(raw) -> float:
    """Coerce a model-supplied confidence to [0,1]. Accepts a 0-1 float or a
    0-100 score (a common model habit); anything unparseable is 0.0."""
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return 0.0
    if v > 1.0:
        v = v / 100.0
    return max(0.0, min(1.0, v))
