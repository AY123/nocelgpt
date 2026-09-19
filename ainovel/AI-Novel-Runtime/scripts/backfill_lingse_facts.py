"""backfill_lingse_facts.py — 追补 novel-lingse Chapter 34-100 的事实循环

基于 w12_mint_walkthrough.py，但针对真实 registry（非 sandbox），用于修复 P0-2。

执行流程：
1. 为每章从 chapter-final 读取正文
2. 运行 W12 fact extraction（LLM）
3. AI 自动审批（采用 w12 的保守策略）
4. execute_mint 写入 facts/
5. recompute 更新投影

用法：
  PYTHONPATH=. python3 scripts/backfill_lingse_facts.py --start 34 --end 36  # 先跑 3 章测试
  PYTHONPATH=. python3 scripts/backfill_lingse_facts.py --start 34 --end 100 # 完整追补
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

RT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = RT.parent / "AI-Novel-Standard" / "phase-1" / "generated" / "json-schema"
NOVEL_DIR = RT.parent / "novel-lingse"  # 真实 registry
ACTOR = "AI-backfill-agent"  # ADR-009 audit trail

# 可 mint 的类型和字段（与 w12_mint_walkthrough.py 一致）
_MINTABLE_NEW_TYPES = {"Character", "Item", "CHR", "ITM"}
_DIRECT_ADDITIVE_PREFIXES = ("physical_facts.",)


def _load_env() -> None:
    """加载 .env 配置（Claude 中转优先）"""
    for f in (RT.parent / ".env", RT / ".env"):
        if f.is_file():
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

    # 映射 CC_VIBE_ANTHROPIC_* 到 ANTHROPIC_* (factory.py 使用后者)
    if os.environ.get("CC_VIBE_ANTHROPIC_AUTH_TOKEN"):
        os.environ.setdefault("ANTHROPIC_AUTH_TOKEN",
                             os.environ["CC_VIBE_ANTHROPIC_AUTH_TOKEN"])
    if os.environ.get("CC_VIBE_ANTHROPIC_BASE_URL"):
        os.environ.setdefault("ANTHROPIC_BASE_URL",
                             os.environ["CC_VIBE_ANTHROPIC_BASE_URL"])
    if os.environ.get("CC_VIBE_ANTHROPIC_MODEL"):
        os.environ.setdefault("ANTHROPIC_MODEL",
                             os.environ["CC_VIBE_ANTHROPIC_MODEL"])


def _ai_approve(plan_items: list[dict]) -> list[str]:
    """AI 审批策略（追补模式）：接受可 mint 的 new/additive

    追补修复模式下，目标是恢复事实循环，不是追求完美质量。
    - new: 只接受 field='name' 的（mint 要求）
    - additive: 接受所有增量字段（包括 abilities）
    - conflicting: 拒绝，需要人工判断
    """
    accepted = []
    for it in plan_items:
        cls = it.get("classification")
        field = it.get("field") or ""

        # new 候选必须是 name 字段（mint 的硬性要求）
        if cls == "new" and field == "name":
            accepted.append(it["candidate_id"])
        # additive 接受所有字段
        elif cls == "additive":
            accepted.append(it["candidate_id"])

    return accepted


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="追补 novel-lingse 事实循环")
    parser.add_argument("--start", type=int, required=True, help="起始章节号")
    parser.add_argument("--end", type=int, required=True, help="结束章节号")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划，不写入")
    args = parser.parse_args()

    _load_env()

    # 检查 API key（按优先级）
    if os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        provider = "claude"
        model_id = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4")
        print(f"✓ 使用 Claude 中转: {model_id}")
    elif os.environ.get("CC_VIBE_OPENAI_AUTH_TOKEN"):
        provider = "cc-vibe-openai"
        model_id = os.environ.get("CC_VIBE_OPENAI_MODEL", "gpt-5.6-sol")
        print(f"✓ 使用 GPT 中转: {model_id}")
    elif os.environ.get("MOONSHOT_API_KEY"):
        provider = "kimi"
        model_id = os.environ.get("KIMI_MODEL", "moonshot-v1-128k")
        print(f"✓ 使用 Kimi: {model_id}")
    else:
        raise SystemExit("❌ 未配置任何 API key")

    if not NOVEL_DIR.exists():
        raise SystemExit(f"❌ Novel directory not found: {NOVEL_DIR}")

    from runtime.candidates.plan import run_w12_fact_reflow
    from runtime.execution.llm_model import LLMExecutionModel
    from runtime.mint import execute_mint
    from runtime.mint.executor import MintRefused
    from runtime import recompute
    from runtime.registry_loader import load as load_registry

    # LLM 模型（使用 replay 缓存避免重复调用）
    replay = str(NOVEL_DIR / "registry" / "derived" / "serial-replay-backfill")
    model = LLMExecutionModel(provider=provider, model_id=model_id,
                              temperature=0.0, replay_dir=replay)

    print(f"\n=== 追补事实循环 ===")
    print(f"Novel: {NOVEL_DIR}")
    print(f"范围: Chapter {args.start} - {args.end}")
    print(f"模式: {'DRY-RUN' if args.dry_run else 'LIVE (真实写入)'}\n")

    totals = Counter()
    minted_facts = 0
    refused = 0
    receipts = []

    for i in range(args.start, args.end + 1):
        task_id = f"TASK-{i:05d}"

        # 1. 读取 chapter-final
        final_path = NOVEL_DIR / "registry" / "derived" / "chapter-final" / f"final-{task_id}.json"
        if not final_path.exists():
            print(f"  {task_id}: ❌ chapter-final not found, skip")
            continue

        draft_data = json.loads(final_path.read_text())
        draft = {
            "task_id": task_id,
            "body": draft_data["final_text"],
            "hash": draft_data.get("final_hash", ""),
        }

        # 2. 运行 W12 fact extraction
        try:
            res = run_w12_fact_reflow(
                project_path=str(NOVEL_DIR),
                plan_id=f"W12-{task_id}",
                draft=draft,
                model=model
            )
        except Exception as e:
            print(f"  {task_id}: ❌ W12 extraction failed: {e}")
            continue

        plan = res["plan"]
        counts = res["reconciled_counts"]
        for k, v in counts.items():
            totals[k] += v

        # 3. AI 自动审批
        accepted = _ai_approve(plan["items"])
        if not accepted:
            print(f"  {task_id}: no mintable candidates (counts={counts})")
            continue

        if args.dry_run:
            print(f"  {task_id}: [DRY-RUN] would mint {len(accepted)} candidates (counts={counts})")
            continue

        # 4. execute_mint
        try:
            receipt = execute_mint(
                project_path=str(NOVEL_DIR),
                plan=plan,
                accepted=accepted,
                schema_dir=str(SCHEMA_DIR),
                confirmed=True,
                actor=ACTOR
            )

            # 5. recompute
            reg = load_registry(str(NOVEL_DIR), schema_dir=str(SCHEMA_DIR))
            rec = recompute.execute_recompute(reg, str(NOVEL_DIR), mint_receipt=receipt)

            minted_facts += len(receipt["minted"])
            receipts.append(receipt["id"])
            print(f"  {task_id}: ✅ minted {len(receipt['minted'])}/{len(accepted)} "
                  f"(counts={counts}) → {receipt['id']}, recompute impacted={len(rec.get('impacted', []))}")

        except MintRefused as e:
            refused += 1
            print(f"  {task_id}: ⚠ REFUSED ({e.reason}) — {str(e.detail)[:80]}")
        except Exception as e:
            refused += 1
            print(f"  {task_id}: ❌ mint/recompute failed: {e}")

    # 总结
    print(f"\n=== 总结 ===")
    print(f"章节数          : {args.end - args.start + 1}")
    print(f"reconciled 总计 : {dict(totals)}")
    print(f"mint receipts   : {len(receipts)}")
    print(f"facts minted    : {minted_facts}")
    print(f"mints refused   : {refused}")
    print(f"conflicting (需人工处理): {totals['conflicting']}")

    if not args.dry_run:
        reg = load_registry(str(NOVEL_DIR), schema_dir=str(SCHEMA_DIR))
        print(f"registry 事实总数: {len(reg.all_ids())}")


if __name__ == "__main__":
    main()
