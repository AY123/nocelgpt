# 真人评审操作手册（CLOSE-05 / CLOSE-08~11）

本手册给两位真人评审照做。所有命令在 `AI-Novel-Runtime/` 目录下运行，前缀 `PYTHONPATH=.`。
API key 无需配置——CLI 自动从仓库根 `.env` 读取 `DEEPSEEK_API_KEY`（真人评审这两步其实不调用模型）。

## 铁律（否则前功尽弃）

- **两个不同的真人**：`editor_a` 和 `editor_b` 必须由两个人独立打分。工具会拒绝同一 `--reviewer`
  同时填两个槽。绝不能用 AI 代填——那正是刚修掉的 W9 自我指涉/同源虚高问题。
- **量表 1-5**：见 `AI-Novel-Runtime/quality-golden-set/metadata/editor-guide.md`。5=极强，1=维度失败。
- **盲评看不到来源**：只看 A/B 正文，不去查哪个是原稿/自动修订。

---

## 第一步：金样集双评（CLOSE-05）

43 条有正文的样本，每条要两个人各打一次 12 维分。

评审者甲（比如你）：
```
PYTHONPATH=. python3 scripts/human_score.py --reviewer 甲 --slot editor_a --all
```
评审者乙（第二个人）：
```
PYTHONPATH=. python3 scripts/human_score.py --reviewer 乙 --slot editor_b --all
```

工具会逐样本显示正文 + notes.md，然后逐维度提示输入 1-5。写入
`samples/QGS-000XX/human_scores.json` 的对应槽，带 `_reviewer` + `_scored_at`（满足可审计）。

- 单条评审：把 `--all` 换成 `QGS-00001 QGS-00002`。
- 中途退出（Ctrl-C）会保存已完成的样本，下次接着评未评的。
- 重评某槽：加 `--force`。
- 7 条 skeleton seed（QGS-00004~00010）无正文，工具自动跳过——它们属于 CLOSE-04，需先补正文。

两人都评完后，仲裁分歧（在 human_scores.json 的 `consensus` / `disagreement_notes` 记录），
然后重跑 W9 校准（此时 reviewer 侧仍是 AI 判官，人类是真值）：
```
PYTHONPATH=. python3 -c "from runtime.serialize.reviewer_calibration_cli import backfill_all; backfill_all('..')"
PYTHONPATH=. python3 -c "from runtime.serialize.reviewer_calibration_report import write_w9_summary_markdown; write_w9_summary_markdown('..')"
```
查看 `metadata/w9-calibration-summary.md` 的相关性/MAE/定级。

---

## 第二步：双臂盲评（CLOSE-08~11）

22 个 packet（原稿 vs 自动修订，来源隐藏）。先跑小批次校验流程，再全量。

先试 B01（3 个）：
```
PYTHONPATH=. python3 scripts/blind_review.py --reviewer 甲 --batch W10-B01
```
确认盲法/理由码顺手后，全量：
```
PYTHONPATH=. python3 scripts/blind_review.py --reviewer 甲 --all
```

每个 packet 显示 version_A / version_B，逐项提示：winner(A/B/tie)、confidence(low/medium/high)、
理由码（编号多选）、备注。写入 packet 的 `human_result`。

---

## 第三步：揭盲聚合（CLOSE-10）

盲评填完后，揭盲并算自动修订净胜率/回归率，得出 retain/restrict/disable：
```
PYTHONPATH=. python3 scripts/blind_unblind.py --dry-run   # 先看结果
PYTHONPATH=. python3 scripts/blind_unblind.py             # 写入决策记录
```
结论写进 `metadata/w10-blind-review-comparison-results.json` 的 `decision_record`。
阈值：净胜率 ≥15% → retain；非负但弱 → restrict；为负 → disable；回归率 >20% → restrict。

---

## 工具清单

| 工具 | 用途 | 谁跑 |
|---|---|---|
| `scripts/human_score.py` | 金样集 12 维打分 → human_scores.json | 两个真人各一次 |
| `scripts/blind_review.py` | 双臂盲评 → packet.human_result | 真人 |
| `scripts/blind_unblind.py` | 揭盲聚合 → 策略结论 | 评完后任一人 |
