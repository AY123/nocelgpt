"""Source-bound genre rules, not a claim of automatic prose understanding.

Chinese examples use explicit supplied interpretations. These controls validate
the deterministic policy boundary and do not certify an extractor, whole-chapter
coverage, factual truth, reading quality, or Canon acceptance.
"""

import json
import shutil
from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
from itertools import permutations
from pathlib import Path

import pytest

from anovel.canon.identity import canonical_bytes
from anovel.domain.events import Occurrence
from anovel.domain.identity import EntityId
from anovel.genre.policy import (
    ClaimContext,
    EvidenceSpan,
    GenrePolicy,
    Mechanism,
    PolicyDiagnostic,
    PolicyError,
    PolicyStatus,
    SemanticClaim,
    SourceDocument,
)
from anovel.genre.registry import GenreRegistry, PackRef

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "specs/genres"
URBAN = "urban.business.realistic"
FANTASY = "fantasy.eastern.progression"
PROJECT = "novel-policy"


def binding(anchor=URBAN, project=PROJECT, directory=SOURCE):
    catalog = json.loads((directory / "registry.yaml").read_text())
    row = next(row for row in catalog["packs"] if row["id"] == anchor)
    ref = PackRef(row["id"], row["version"], row["content_hash"])
    return GenreRegistry.from_directory(directory).bind(project, ref)


def source(
    text="她借助修炼凭空获得了超自然力量。", local_id="candidate", project=PROJECT
):
    return SourceDocument(EntityId(project, local_id), text)


def claim(
    document,
    mechanism=Mechanism.CULTIVATION,
    context=ClaimContext.WORLD,
    occurrence=Occurrence.OCCURRED,
    *,
    quote=None,
    claim_id="claim-1",
):
    quote = document.text if quote is None else quote
    start = document.text.index(quote)
    return SemanticClaim(
        claim_id,
        mechanism,
        context,
        occurrence,
        EvidenceSpan(
            document.id, document.content_hash, start, start + len(quote), quote
        ),
        "fixture:supplied-interpretation/" + claim_id,
    )


def verify_result(result, expected, bound, document):
    assert result.status is expected
    assert result.binding == bound
    assert result.document == document
    assert result.scope == "STRUCTURED_CLAIMS_ONLY"
    assert result.prose_coverage == "NOT_VERIFIED"
    assert len(result.policy_hash) == 64
    assert int(result.policy_hash, 16) >= 0
    assert result.policy_version
    exported = result.to_dict()
    assert exported["status"] == expected.value
    assert exported["binding"]["pack_ref"] == bound.ref.to_dict()
    assert exported["document"]["content_hash"] == document.content_hash
    assert exported["scope"] == "STRUCTURED_CLAIMS_ONLY"
    assert exported["prose_coverage"] == "NOT_VERIFIED"


@pytest.mark.parametrize(
    ("mechanism", "text"),
    [
        (Mechanism.ORDINARY_ACTION, "她失去订单后主动向合伙人说明了原因。"),
        (Mechanism.LOCAL_TRADE, "她用库存换取现金，并承担更低利润的代价。"),
        (Mechanism.MODERN_CORPORATE_SCHEMA, "董事依章程表决，股权变化影响控制权。"),
    ],
)
def test_realistic_world_ordinary_trade_and_company_facts_are_allowed(mechanism, text):
    bound = binding()
    document = source(text)
    annotated = claim(document, mechanism)
    result = GenrePolicy(bound).check(document, (annotated,))
    verify_result(result, PolicyStatus.PASS, bound, document)
    assert result.diagnostics[0].claim == annotated
    assert result.diagnostics[0].code == "MECHANISM_ALLOWED"


@pytest.mark.parametrize(
    ("mechanism", "text"),
    [
        (Mechanism.CULTIVATION, "她闭关修炼后，确实以灵力隔空取走了合同。"),
        (Mechanism.MAGIC, "他实际施展法术，在账户中凭空复制了一笔资金。"),
        (Mechanism.REBIRTH, "她确实回到十年前，带着上一世记忆改变了交易。"),
        (Mechanism.SYSTEM, "无来源的系统实际向他发放了超现实奖励。"),
        (
            Mechanism.COST_FREE_CULTIVATION_ADVANCE,
            "他没有任何代价便实际突破了修炼境界。",
        ),
    ],
)
def test_realistic_actual_supernatural_world_facts_fail(mechanism, text):
    bound = binding()
    document = source(text)
    result = GenrePolicy(bound).check(document, (claim(document, mechanism),))
    verify_result(result, PolicyStatus.FAIL, bound, document)
    assert result.diagnostics[0].code == "WORLD_MECHANISM_CONFLICT"


@pytest.mark.parametrize(
    ("mechanism", "text", "status"),
    [
        (Mechanism.ORDINARY_ACTION, "弟子决定先找回失散的同伴。", PolicyStatus.PASS),
        (
            Mechanism.LOCAL_TRADE,
            "弟子向商会交换药草，代价是交出秘密情报。",
            PolicyStatus.PASS,
        ),
        (
            Mechanism.CULTIVATION,
            "弟子按已声明的世界机制修炼，耗尽灵石后获得突破。",
            PolicyStatus.PASS,
        ),
        (
            Mechanism.MODERN_CORPORATE_SCHEMA,
            "未声明现代公司制度的宗门，直接按现代股权会计决定掌门归属。",
            PolicyStatus.FAIL,
        ),
        (
            Mechanism.COST_FREE_CULTIVATION_ADVANCE,
            "没有资源、前提和代价，弟子直接跨越全部境界。",
            PolicyStatus.FAIL,
        ),
        (Mechanism.MAGIC, "他使用了本书尚未声明的法术机制。", PolicyStatus.UNKNOWN),
        (
            Mechanism.REBIRTH,
            "故事声称他重生了，但没有声明此世界具备这一机制。",
            PolicyStatus.UNKNOWN,
        ),
        (
            Mechanism.SYSTEM,
            "他收到一个未建立世界依据的系统奖励。",
            PolicyStatus.UNKNOWN,
        ),
    ],
)
def test_fantasy_rules_allow_local_trade_but_not_undeclared_systems(
    mechanism, text, status
):
    bound = binding(FANTASY)
    document = source(text)
    result = GenrePolicy(bound).check(document, (claim(document, mechanism),))
    verify_result(result, status, bound, document)


@pytest.mark.parametrize("anchor", [URBAN, FANTASY])
@pytest.mark.parametrize(
    ("context", "text"),
    [
        (ClaimContext.QUOTATION, "她正在读小说，书中写道：主角以法术复制了金钱。"),
        (ClaimContext.DREAM, "他梦见自己以法术复制金钱，醒来账户仍空。"),
        (ClaimContext.METAPHOR, "他把谈判形容为施法，这只是比喻，并无超自然事件。"),
        (ClaimContext.BELIEF, "她误以为对手会法术，但故事没有确认这个信念。"),
        (ClaimContext.HYPOTHESIS, "假如有人能施法复制金钱，银行将如何应对？"),
        (ClaimContext.LIE, "骗子谎称自己会施法，实际只是为了索取钱款。"),
    ],
)
def test_known_non_world_context_never_promotes_inner_claim_to_fact(
    anchor, context, text
):
    bound = binding(anchor)
    document = source(text)
    annotated = claim(document, Mechanism.MAGIC, context)
    result = GenrePolicy(bound).check(document, (annotated,))
    verify_result(result, PolicyStatus.PASS, bound, document)
    assert result.diagnostics[0].code == "NOT_WORLD_FACT"
    assert result.diagnostics[0].claim.context is context
    assert result.diagnostics[0].claim.occurrence is Occurrence.OCCURRED


@pytest.mark.parametrize("anchor", [URBAN, FANTASY])
def test_explicitly_not_occurred_is_not_a_world_violation(anchor):
    bound = binding(anchor)
    document = source("没有任何法术发生；传言被当事人否认。")
    result = GenrePolicy(bound).check(
        document,
        (claim(document, Mechanism.MAGIC, occurrence=Occurrence.NOT_OCCURRED),),
    )
    verify_result(result, PolicyStatus.PASS, bound, document)
    assert result.diagnostics[0].code == "NOT_OCCURRED"


@pytest.mark.parametrize("anchor", [URBAN, FANTASY])
@pytest.mark.parametrize("field", ["mechanism", "context", "occurrence"])
def test_any_unresolved_interpretation_is_unknown_not_pass_or_conflict(anchor, field):
    bound = binding(anchor)
    document = source("他仿佛知道一切，但究竟发生了什么尚不清楚。")
    item = claim(document, Mechanism.CULTIVATION)
    unknown = {
        "mechanism": Mechanism.UNKNOWN,
        "context": ClaimContext.UNKNOWN,
        "occurrence": Occurrence.UNKNOWN,
    }[field]
    item = replace(item, **{field: unknown})
    result = GenrePolicy(bound).check(document, (item,))
    verify_result(result, PolicyStatus.UNKNOWN, bound, document)
    assert result.diagnostics[0].code.startswith("UNKNOWN_")


@pytest.mark.parametrize(
    ("context", "occurrence", "mechanism"),
    [
        (ClaimContext.DREAM, Occurrence.UNKNOWN, Mechanism.MAGIC),
        (ClaimContext.QUOTATION, Occurrence.OCCURRED, Mechanism.UNKNOWN),
        (ClaimContext.UNKNOWN, Occurrence.NOT_OCCURRED, Mechanism.ORDINARY_ACTION),
    ],
)
def test_unresolved_annotation_is_not_exempted_by_another_safe_field(
    context, occurrence, mechanism
):
    bound = binding()
    document = source("梦境或引述的具体意义仍未核实。")
    item = claim(document, mechanism, context, occurrence)
    assert GenrePolicy(bound).check(document, (item,)).status is PolicyStatus.UNKNOWN


@pytest.mark.parametrize("anchor", [URBAN, FANTASY])
def test_no_extracted_claims_reports_unknown_and_unverified_prose_coverage(anchor):
    bound = binding(anchor)
    document = source("她挥手令整座城市飞上天空。")
    result = GenrePolicy(bound).check(document, ())
    verify_result(result, PolicyStatus.UNKNOWN, bound, document)
    assert result.diagnostics[0].claim is None
    assert result.diagnostics[0].code == "NO_CLAIMS"


@pytest.mark.parametrize(
    "text",
    [
        "公司终于实现了技术突破，但没有获得超自然力量。",
        "创业者给普通记账系统起名叫修仙助手。",
        "商会讨论资本与未来，真实行动只是签订交易合同。",
    ],
)
def test_words_do_not_replace_supplied_fact_semantics(text):
    bound = binding()
    document = source(text)
    ordinary = claim(document, Mechanism.ORDINARY_ACTION)
    result = GenrePolicy(bound).check(document, (ordinary,))
    assert result.status is PolicyStatus.PASS
    assert result.diagnostics[0].claim.mechanism is Mechanism.ORDINARY_ACTION


def test_same_text_yields_different_decisions_only_with_explicit_interpretations():
    bound = binding()
    document = source("他一步登天。")
    metaphor = claim(document, Mechanism.MAGIC, ClaimContext.METAPHOR)
    supernatural = replace(metaphor, context=ClaimContext.WORLD)
    assert GenrePolicy(bound).check(document, (metaphor,)).status is PolicyStatus.PASS
    assert (
        GenrePolicy(bound).check(document, (supernatural,)).status is PolicyStatus.FAIL
    )


@pytest.mark.parametrize("field", ["context", "occurrence"])
def test_contradictory_same_span_annotations_are_unknown_in_any_order(field):
    bound = binding()
    document = source("她在梦中还是现实中施法，现有叙述互相冲突。")
    first = claim(document, Mechanism.MAGIC)
    other = replace(
        first,
        id="second",
        **{
            field: ClaimContext.DREAM if field == "context" else Occurrence.NOT_OCCURRED
        },
    )
    for items in [(first, other), (other, first)]:
        result = GenrePolicy(bound).check(document, items)
        assert result.status is PolicyStatus.UNKNOWN
        assert len(result.diagnostics) == 2
        assert all(d.status is PolicyStatus.UNKNOWN for d in result.diagnostics)
        assert all(d.code == "CONTRADICTORY_ANNOTATION" for d in result.diagnostics)


def test_identical_interpretations_with_distinct_claim_ids_are_not_contradictions():
    bound = binding()
    document = source()
    first = claim(document)
    result = GenrePolicy(bound).check(document, (first, replace(first, id="second")))
    assert result.status is PolicyStatus.FAIL
    assert len(result.diagnostics) == 2
    assert all(d.code == "WORLD_MECHANISM_CONFLICT" for d in result.diagnostics)


def test_independent_failure_dominates_unknown_and_pass_without_losing_diagnostics():
    bound = binding()
    document = source("她施法令纸张燃烧。他似乎预知结局。店员递来合同。")
    items = (
        claim(
            document, Mechanism.MAGIC, quote="她施法令纸张燃烧。", claim_id="violation"
        ),
        claim(
            document, Mechanism.UNKNOWN, quote="他似乎预知结局。", claim_id="unknown"
        ),
        claim(
            document,
            Mechanism.ORDINARY_ACTION,
            quote="店员递来合同。",
            claim_id="ordinary",
        ),
    )
    expected = {item.id for item in items}
    for order in permutations(items):
        result = GenrePolicy(bound).check(document, order)
        assert result.status is PolicyStatus.FAIL
        assert {d.claim.id for d in result.diagnostics} == expected
        assert {d.status for d in result.diagnostics} == set(PolicyStatus)


def test_contradiction_does_not_hide_a_separate_confirmed_violation():
    bound = binding()
    document = source("他在梦中施法。她在现实中修炼成仙。")
    ambiguous = claim(
        document, Mechanism.MAGIC, quote="他在梦中施法。", claim_id="ambiguous"
    )
    alternate = replace(ambiguous, id="alternate", context=ClaimContext.DREAM)
    violation = claim(document, quote="她在现实中修炼成仙。", claim_id="violation")
    result = GenrePolicy(bound).check(document, (ambiguous, alternate, violation))
    assert result.status is PolicyStatus.FAIL
    assert [d.status for d in result.diagnostics] == [
        PolicyStatus.UNKNOWN,
        PolicyStatus.UNKNOWN,
        PolicyStatus.FAIL,
    ]


def test_evidence_uses_unicode_character_offsets_and_full_utf8_document_hash():
    bound = binding()
    document = source("开场🙂：她完成谈判。尾声。")
    item = claim(document, Mechanism.ORDINARY_ACTION, quote="她完成谈判。")
    assert item.evidence.start == 4
    assert item.evidence.end == 10
    assert (
        item.evidence.source_sha256 == sha256(document.text.encode("utf-8")).hexdigest()
    )
    result = GenrePolicy(bound).check(document, (item,))
    assert result.status is PolicyStatus.PASS
    assert result.diagnostics[0].claim.evidence.quote == "她完成谈判。"


@pytest.mark.parametrize(
    "change", ["hash", "other-source", "other-project", "quote", "range"]
)
def test_mismatched_or_stale_evidence_cannot_be_checked(change):
    bound = binding()
    document = source()
    item = claim(document)
    updates = {
        "hash": {"source_sha256": "0" * 64},
        "other-source": {"source_id": EntityId(PROJECT, "other-candidate")},
        "other-project": {"source_id": EntityId("other-project", "candidate")},
        "quote": {"quote": "她根本没有修炼。"},
        "range": {"end": len(document.text) + 1},
    }[change]
    invalid = replace(item, evidence=replace(item.evidence, **updates))
    with pytest.raises(PolicyError):
        GenrePolicy(bound).check(document, (invalid,))


def test_editing_text_outside_claim_span_invalidates_old_evidence():
    bound = binding()
    document = source("前言。她修炼成仙。后记。")
    item = claim(document, quote="她修炼成仙。")
    revised = replace(document, text="前言。她修炼成仙。后记改变。")
    assert revised.content_hash != document.content_hash
    with pytest.raises(PolicyError):
        GenrePolicy(bound).check(revised, (item,))


@pytest.mark.parametrize(
    "start,end", [(True, 4), (0, True), (-1, 4), (0, 0), (4, 3), (0.0, 4), (0, 4.0)]
)
def test_evidence_requires_strict_nonempty_character_interval(start, end):
    document = source()
    with pytest.raises(PolicyError):
        EvidenceSpan(document.id, document.content_hash, start, end, "修炼")


@pytest.mark.parametrize("digest", ["", "a" * 63, "A" * 64, "z" * 64, None])
def test_evidence_rejects_malformed_source_hash(digest):
    document = source()
    with pytest.raises(PolicyError):
        EvidenceSpan(document.id, digest, 0, 2, document.text[:2])


@pytest.mark.parametrize(
    "field,value",
    [
        ("mechanism", "MAGIC"),
        ("context", "WORLD"),
        ("occurrence", "OCCURRED"),
        ("evidence", {}),
        ("id", ""),
        ("interpretation_ref", " "),
    ],
)
def test_claim_requires_strict_typed_interpretation_and_source(field, value):
    item = claim(source())
    with pytest.raises(PolicyError):
        replace(item, **{field: value})


@pytest.mark.parametrize("text", ["", " ", b"bytes", None, "\ud800"])
def test_source_text_must_be_nonempty_valid_unicode(text):
    with pytest.raises(PolicyError):
        SourceDocument(EntityId(PROJECT, "candidate"), text)


def test_policy_rejects_source_from_another_project_even_without_claims():
    bound = binding()
    with pytest.raises(PolicyError):
        GenrePolicy(bound).check(source(project="foreign"), ())


@pytest.mark.parametrize("invalid", [[], [None], (None,), "claims", None])
def test_claim_collection_is_strict_immutable_and_typed(invalid):
    with pytest.raises(PolicyError):
        GenrePolicy(binding()).check(source(), invalid)


def test_duplicate_claim_ids_are_rejected_even_for_identical_evidence():
    document = source()
    item = claim(document)
    with pytest.raises(PolicyError):
        GenrePolicy(binding()).check(document, (item, item))


@pytest.mark.parametrize("anchor", [URBAN, FANTASY])
def test_exact_strategy_conflict_uses_actual_proposal_and_preserves_pack(anchor):
    bound = binding(anchor)
    selection = bound.select_strategy(bound.pack.strategies[0].id)
    document = source(
        "这个创作提案要求主角无成本直接获得全部修炼境界。", local_id="proposal"
    )
    annotated = claim(document, Mechanism.COST_FREE_CULTIVATION_ADVANCE)
    result = GenrePolicy(bound).check_strategy(selection, document, (annotated,))
    assert result.status is PolicyStatus.FAIL
    assert result.binding == bound
    assert result.document == document
    assert result.selection == selection
    assert result.selection.strategy.id == selection.strategy.id
    assert result.scope == "OPTIONAL_STRATEGY"
    assert result.prose_coverage == "NOT_VERIFIED"


def test_compatible_strategy_proposal_is_allowed_without_switching_genre():
    bound = binding()
    selected = bound.select_strategy(bound.pack.strategies[0].id)
    proposal = source("谈判失败后，她付出让价代价维持合作。", local_id="proposal")
    result = GenrePolicy(bound).check_strategy(
        selected, proposal, (claim(proposal, Mechanism.ORDINARY_ACTION),)
    )
    assert result.status is PolicyStatus.PASS
    assert result.selection == selected
    assert result.to_dict()["selection"] is not None
    assert result.binding.ref == bound.ref


@pytest.mark.parametrize(
    "strategy_id",
    [None, "missing-strategy", "business.negotiation", "progression.costly_choice"],
)
def test_no_optional_strategy_is_only_applicability_pass_and_retains_binding(
    strategy_id,
):
    bound = binding()
    selected = bound.select_strategy(strategy_id)
    result = GenrePolicy(bound).check_strategy(selected)
    assert result.status is PolicyStatus.PASS
    assert result.binding == bound
    assert result.binding.ref == bound.ref
    assert result.document is None
    assert result.selection == selected
    assert result.selection.strategy is None
    assert result.scope == "OPTIONAL_STRATEGY"
    assert result.prose_coverage == "NOT_VERIFIED"
    assert result.diagnostics[0].code == "NO_OPTIONAL_STRATEGY"
    assert result.diagnostics[0].claim is None


@pytest.mark.parametrize("with_claim", [False, True])
def test_no_match_cannot_inject_optional_strategy_proposal_or_claims(with_claim):
    bound = binding()
    document = source(local_id="proposal")
    selected = bound.select_strategy("not-found")
    with pytest.raises(PolicyError):
        GenrePolicy(bound).check_strategy(
            selected, document, (claim(document),) if with_claim else ()
        )


def test_strategy_match_without_proposal_or_without_claims_is_unknown():
    bound = binding()
    selected = bound.select_strategy(bound.pack.strategies[0].id)
    without_proposal = GenrePolicy(bound).check_strategy(selected)
    assert without_proposal.status is PolicyStatus.UNKNOWN
    assert without_proposal.selection == selected
    assert without_proposal.diagnostics[0].code == "MISSING_STRATEGY_PROPOSAL"
    document = source("计划写一场谈判。", local_id="proposal")
    without_claims = GenrePolicy(bound).check_strategy(selected, document)
    assert without_claims.status is PolicyStatus.UNKNOWN
    assert without_claims.diagnostics[0].code == "NO_CLAIMS"


def test_strategy_claims_require_their_exact_proposal_document():
    bound = binding()
    selected = bound.select_strategy(bound.pack.strategies[0].id)
    document = source(local_id="proposal")
    with pytest.raises(PolicyError):
        GenrePolicy(bound).check_strategy(selected, claims=(claim(document),))


@pytest.mark.parametrize(
    "anchor,project", [(FANTASY, PROJECT), (URBAN, "other-project")]
)
def test_strategy_selection_from_another_pack_or_project_is_rejected(anchor, project):
    selected_from = binding(anchor, project)
    selection = selected_from.select_strategy(selected_from.pack.strategies[0].id)
    with pytest.raises(PolicyError):
        GenrePolicy(binding()).check_strategy(selection)


def test_strategy_proposal_from_another_project_is_rejected():
    bound = binding()
    selected = bound.select_strategy(bound.pack.strategies[0].id)
    document = source(project="foreign", local_id="proposal")
    with pytest.raises(PolicyError):
        GenrePolicy(bound).check_strategy(selected, document, (claim(document),))


@pytest.mark.parametrize("change", ["version", "mechanics", "strategy"])
def test_new_loaded_pack_identity_cannot_implicitly_reuse_existing_policy(
    tmp_path, change
):
    directory = tmp_path / "genres"
    shutil.copytree(SOURCE, directory)
    catalog_path = directory / "registry.yaml"
    catalog = json.loads(catalog_path.read_text())
    row = next(row for row in catalog["packs"] if row["id"] == URBAN)
    manifest_path = directory / row["path"]
    manifest = json.loads(manifest_path.read_text())
    if change == "version":
        row["version"] = manifest["version"] = "1.0.1"
    elif change == "mechanics":
        manifest["profile"]["forbidden_mechanics"].append("新的显式世界限制。")
    else:
        manifest["strategies"][0]["purpose"] = "经修改的创作策略。"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    row["content_hash"] = sha256(canonical_bytes(manifest)).hexdigest()
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
    updated = binding(directory=directory)
    assert updated.ref != binding().ref
    assert updated.profile.anchor == URBAN
    with pytest.raises(PolicyError):
        GenrePolicy(updated)


def test_policy_decisions_are_immutable_and_exported_results_are_independent():
    bound = binding()
    document = source()
    item = claim(document)
    result = GenrePolicy(bound).check(document, (item,))
    before = result.to_dict()
    exported = result.to_dict()
    exported["binding"]["pack_ref"]["id"] = "tampered"
    exported["document"]["text"] = "另一个正文。"
    exported["diagnostics"][0]["claim"]["context"] = "DREAM"
    exported["diagnostics"].clear()
    assert result.to_dict() == before
    assert result.status is PolicyStatus.FAIL
    for value, field, replacement in [
        (document, "text", "changed"),
        (item.evidence, "start", 1),
        (item, "context", ClaimContext.DREAM),
        (result, "diagnostics", ()),
    ]:
        with pytest.raises((FrozenInstanceError, AttributeError)):
            setattr(value, field, replacement)


def test_result_cannot_replace_confirmed_conflict_with_a_forged_pass():
    bound = binding()
    document = source()
    result = GenrePolicy(bound).check(document, (claim(document),))
    diagnostic = result.diagnostics[0]
    forged = replace(diagnostic, status=PolicyStatus.PASS)
    with pytest.raises(PolicyError):
        replace(result, diagnostics=(forged,))
    with pytest.raises(PolicyError):
        replace(result, diagnostics=(replace(diagnostic, rule_id="unrelated-rule"),))


def test_empty_interpretation_result_cannot_be_recast_as_pass():
    result = GenrePolicy(binding()).check(source(), ())
    fake = PolicyDiagnostic(None, PolicyStatus.PASS, "NO_CLAIMS", "GENRE-EMPTY-1")
    with pytest.raises(PolicyError):
        replace(result, diagnostics=(fake,))


@pytest.mark.parametrize(
    "change",
    [
        {"policy_hash": "0" * 64},
        {"policy_version": "0.0.0"},
        {"prose_coverage": "VERIFIED"},
        {"scope": "WHOLE_CHAPTER"},
    ],
)
def test_result_cannot_change_policy_identity_or_claim_full_prose_coverage(change):
    document = source()
    result = GenrePolicy(binding()).check(document, (claim(document),))
    with pytest.raises(PolicyError):
        replace(result, **change)
