"""redline_rules.py — the real default platform redline seed (ANES v2, Phase 4.1 / M1-B1).

This is DATA, not engine. `redline.py` stays the deterministic matcher; this file
holds the built-in seed ruleset that a Chinese web-novel publishing gate needs so
the gate is not inert (previously three placeholder patterns that never fired).

Design:
  - hard / action=block  -> DETERMINISTIC gate: blocks build AND publish (ADR-003).
    Only objective, platform-illegal content lives here (色情露骨 / 政治红线 /
    未成年人不当 / 违法犯罪教学 / 暴恐), where a match is compliance-fatal.
  - soft / action=review -> advisory only; rides the envelope, never gates
    (擦边低俗 / 极端血腥 / 平台标题违规). Sensitive, editor-review-worthy, not fatal.

These are content-moderation filters for a publishing safety gate — the defensive,
compliance use case. Patterns are conservative seeds; a Project overrides them with
its own versioned ruleset via `save_ruleset(..., rule_set_id=...)`.

RULESET_VERSION bumps whenever the seed changes, so a run manifest can record which
redline policy version admitted a chapter.
"""
from __future__ import annotations

RULESET_VERSION = "2026.07.1"

# Each entry mirrors RedlineRule fields; redline.py builds RedlineRule from these.
# Kept as plain dicts so the same seed can be dumped to a YAML ruleset verbatim.
SEED_RULES: tuple[dict, ...] = (
    # ---- HARD / BLOCK: objective platform red lines (compliance-fatal) ----
    {
        "rule_id": "explicit-sexual",
        "pattern": r"(阴茎|阴道|肉棒|抽插|射精|龟头|淫水|骚穴|口交|肛交|自慰高潮)",
        "severity": "hard", "action": "block", "scope": "body", "priority": 1,
        "note": "露骨性器官/性行为描写 — 平台硬红线（色情）",
    },
    {
        "rule_id": "minor-sexual",
        "pattern": r"(幼女|萝莉|未成年|小学生|初中生)[^。！？\n]{0,12}(裸|胸|下体|发育|性|做爱|上床|诱奸|侵犯)",
        "severity": "hard", "action": "block", "scope": "body", "priority": 1,
        "note": "涉未成年人性化内容 — 平台硬红线（未成年人保护）",
    },
    {
        "rule_id": "political-redline",
        "pattern": r"(颠覆国家政权|分裂国家|煽动分裂|法轮功|颠覆政府|武装叛乱|藏独|疆独|港独|台独建国)",
        "severity": "hard", "action": "block", "scope": "any", "priority": 1,
        "note": "政治敏感/危害国家安全 — 平台硬红线",
    },
    {
        "rule_id": "crime-instruction",
        "pattern": r"(制造|制作|合成|提炼)[^。！？\n]{0,8}(冰毒|海洛因|甲基苯丙胺|炸弹|炸药|雷管|tnt|毒气)|(制毒|制爆)教程",
        "severity": "hard", "action": "block", "scope": "body", "priority": 2,
        "note": "违法犯罪方法教学（制毒/制爆） — 平台硬红线",
    },
    {
        "rule_id": "terror-extremism",
        "pattern": r"(恐怖袭击|恐怖组织|圣战|自杀式袭击|极端组织招募|东突厥斯坦)",
        "severity": "hard", "action": "block", "scope": "any", "priority": 2,
        "note": "暴恐/极端主义宣扬 — 平台硬红线",
    },
    # ---- SOFT / REVIEW: sensitive, advisory only (never gates) ----
    {
        "rule_id": "graphic-violence",
        "pattern": r"(挖出内脏|割下|剖开肚子|血肉模糊|碎尸|凌迟|活活烧死)",
        "severity": "soft", "action": "review", "scope": "body", "priority": 20,
        "note": "极端血腥描写 — 敏感，建议编辑复核",
    },
    {
        "rule_id": "vulgar-borderline",
        "pattern": r"(约炮|一夜情|裸露诱惑|情色擦边|软色情)",
        "severity": "soft", "action": "review", "scope": "body", "priority": 30,
        "note": "低俗擦边 — 敏感，建议编辑复核",
    },
    {
        "rule_id": "title-violation",
        "pattern": r"(色情|裸|约炮|一夜情|禁书)",
        "severity": "soft", "action": "review", "scope": "title", "priority": 25,
        "note": "标题违规风险词 — 平台推荐分发不友好，建议复核",
    },
)
