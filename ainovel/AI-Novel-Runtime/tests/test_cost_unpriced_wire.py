"""test_cost_unpriced_wire.py — 未定价告警在活路径上真的会出现。

`tests/test_cost_fold_unpriced.py` 测的是 CostFold 模块本身;这里测的是它
**接进了生产路径**。区分很重要:本仓库反复出现"造好却从未在生产路径运行"的
缺陷,一个只在单测里绿的判别器挡不住任何事故。

钉住两件事:
  1. 确定性 stub 跑仍然 cost=null 且 rationale 说 "no live-model cost"
     —— 行为不变,不伪造成本(schema description 要求)
  2. 有真实调用却没有定价时,manifest 的 rationale **不再谎称无成本**,
     而是明确 "cost UNKNOWN ... not free"

第 2 条是防回归的关键:把 `cost_fold.add(llm)` 改回 `or 0` 会让它变红。
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from runtime import derived
from runtime.serialize import run_serial, write_run_manifest

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"


def _write(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False),
                    encoding="utf-8")


def _scaffold(root: Path, *, n_events: int = 2):
    facts = root / "registry" / "facts"
    meta = root / "registry" / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "registry-version").write_text("1\n", encoding="utf-8")
    (meta / "standard.pin").write_text("2.0.0\n", encoding="utf-8")
    _write(facts / "timelines" / "TML-00001.yaml", {
        "id": "TML-00001", "name": "主线", "status": "active",
        "fact_version": 1, "kind": "main"})
    _write(facts / "characters" / "CHR-00001.yaml", {
        "id": "CHR-00001", "name": "主角", "status": "active", "fact_version": 1})
    for i in range(1, n_events + 1):
        _write(facts / "events" / f"EVT-{i:05d}.yaml", {
            "id": f"EVT-{i:05d}", "name": f"事件{i}", "status": "active",
            "fact_version": 1, "timeline": "TML-00001", "sequence_index": i,
            "participants": ["CHR-00001"],
            "causes": ([f"EVT-{i-1:05d}"] if i > 1 else []),
            "effects": ([f"EVT-{i+1:05d}"] if i < n_events else []),
            "summary": f"第{i}章的核心事件"})


def _draft_paths(project: Path):
    return [project / e["path"]
            for e in derived._load_index(project).get("artifacts", [])
            if e.get("category") == "drafts"]


def _inject_unpriced_llm(project: Path):
    """把已落盘的 draft envelope 改成"真实调用但未定价"的形状。

    这正是 92code:gpt-5.6-sol 缺计价键时的真实产物形状:token_usage 齐全,
    cost 为 None(CostCalculator 对未知模型返回 None,cost.py:14-15)。
    """
    touched = 0
    for path in _draft_paths(project):
        payload = json.loads(path.read_text(encoding="utf-8"))
        draft = payload.get("draft")
        if not isinstance(draft, dict):
            continue
        draft.setdefault("produced_by", {})["llm"] = {
            "provider": "92code",
            "model": "gpt-5.6-sol",
            "token_usage": {"input_tokens": 7964, "output_tokens": 1930,
                            "total_tokens": 9894},
            "cost": None,               # 未定价 => 钱花了但折不出金额
            "latency_ms": 1234,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        touched += 1
    return touched


def test_deterministic_run_still_reports_no_cost_honestly(tmp_path):
    """行为不变:没调用模型 => cost=null,且如实说"无成本"(不是"未知")。"""
    _scaffold(tmp_path)
    result = run_serial(project_path=tmp_path, standard_root=STANDARD,
                        schema_dir=SCHEMA, out_dir=tmp_path / "build-serial")
    manifest, _ = write_run_manifest(project_path=tmp_path, result=result)

    assert manifest["totals"]["live_calls"] == 0
    assert manifest["totals"]["cost"] is None
    assert "no live-model cost" in manifest["rationale"]
    assert "UNKNOWN" not in manifest["rationale"]
    # SerialResult 侧也不应误报
    assert result.cost_warning is None
    assert result.llm_cost["unpriced_calls"] == 0
    assert result.llm_cost["understated"] is False


def test_unpriced_live_call_is_not_reported_as_free(tmp_path):
    """活路径回归:有真实调用却没定价时,manifest 必须说 UNKNOWN 而非"无成本"。

    把 run_manifest.py 里的 `cost_fold.add(llm)` 改回
    `cost_total += float(cst.get("total_cost", 0) or 0)` 会让这条变红 ——
    那正是让 18 元在零预算保护下花掉的写法。
    """
    _scaffold(tmp_path)
    result = run_serial(project_path=tmp_path, standard_root=STANDARD,
                        schema_dir=SCHEMA, out_dir=tmp_path / "build-serial")
    assert _inject_unpriced_llm(tmp_path) > 0, "未能注入 llm 元数据"

    manifest, _ = write_run_manifest(project_path=tmp_path, result=result)

    # 有真实调用被记录
    assert manifest["totals"]["live_calls"] > 0
    # 折不出金额 => cost 仍是 null(不伪造)
    assert manifest["totals"]["cost"] is None
    # 但 rationale 不再谎称免费
    assert "UNKNOWN" in manifest["rationale"], manifest["rationale"]
    assert "not free" in manifest["rationale"], manifest["rationale"]
    assert "92code:gpt-5.6-sol" in manifest["rationale"], manifest["rationale"]
    # token 用量照常记录,证明这确实是真实调用
    assert manifest["totals"]["token_usage"]["total"] > 0


def test_manifest_stays_schema_valid_when_cost_is_unknown(tmp_path):
    """告警走 rationale 文案,不得给冻结的 totals/cost 加字段(§1 Schema-First)。

    totals 与 totals.cost 都是 additionalProperties:false,所以未定价计数只能
    住在 rationale + SerialResult(内存对象,不受校验)。
    """
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(json.loads(
        (STANDARD / "contracts" / "production-run-manifest.schema.json")
        .read_text(encoding="utf-8")))

    _scaffold(tmp_path)
    result = run_serial(project_path=tmp_path, standard_root=STANDARD,
                        schema_dir=SCHEMA, out_dir=tmp_path / "build-serial")
    _inject_unpriced_llm(tmp_path)
    manifest, _ = write_run_manifest(project_path=tmp_path, result=result)

    errors = [f"{'/'.join(str(p) for p in e.path) or '(root)'}: {e.message}"
              for e in validator.iter_errors(manifest)]
    assert errors == [], errors
    assert set(manifest["totals"]) == {
        "planned", "produced", "skipped", "final_state_hash",
        "live_calls", "token_usage", "cost",
    }
