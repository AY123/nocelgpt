# W8/W9 AI 模拟评分流程走通报告

- **目的**: 用 AI 扮演评分者，把 W8-03 双评+仲裁 → W9 校准整条流程端到端跑通一遍（**流程闭环验证，不是真值**）。
- **日期**: 2026-07-22
- **脚本**: `scripts/w8_ai_scoring.py`（AI 双评+仲裁）、`scripts/w9_ai_calibration.py`（喂进真实校准代码）
- **模型**: deepseek-chat, temp=0, replay-cached（`serial-replay-w8score-gen`）

## 硬红线（已守住）

- AI 分只写 `samples/*/ai_scores.json`，**从未触碰** `human_scores.json`（真人真值位）。
- W9 结果只写 `metadata/w9-ai-calibration-results.json`，**未覆盖**真实的 `w9-calibration-results.json` / `w9-calibration-summary.json`。
- git 已确认：43 个 human_scores.json 与两份真实校准产物零改动。

## 流程

1. **W8-03 双评**：AI 扮两个 persona（严格商业主编 / 资深文学编辑），各就 12 维 1–5 独立打分。
2. **仲裁**：任一维度分差 ≥2 记为 disputed，取四舍五入均值为 consensus（第三方仲裁的替身）。
3. **W9 校准**：AI consensus 作为「自动 reviewer 侧」，喂进**真实的** `build_calibration_row` / `build_calibration_summary`，对比每个样本**真实的 human_mean**，算每维相关性 / MAE / 定级。

覆盖 43 个有正文的样本（QGS-004~010 是空 seed，跳过）。

## 结果（对比真实 human_mean）

| 维度 | corr | MAE | level |
|---|---|---|---|
| opening_hook | 0.92 | 0.49 | decision |
| conflict_progression | 0.85 | 0.44 | decision |
| paying_intent | 0.87 | 0.69 | decision |
| continue_intent | 0.87 | 0.48 | decision |
| ending_hook | 0.85 | 0.56 | diagnostic |
| chapter_goal | 0.79 | 0.41 | diagnostic |
| payoff_delivery | 0.78 | 0.53 | diagnostic |
| emotion_flow | 0.78 | 0.31 | diagnostic |
| continuity | 0.77 | 0.74 | diagnostic |
| character_motivation | 0.75 | 0.44 | diagnostic |
| information_density | 0.63 | 0.60 | diagnostic |
| ai_voice_risk | 0.53 | 0.64 | diagnostic |

trusted（n≥5, corr≥0.6）：12 维中 11 维；唯一落选是 **ai_voice_risk（corr 0.53）**。

## 诚实结论：流程通了，但相关性是虚高的，不能当校准真值

1. **流程闭环成立**：双评→仲裁→喂真实校准代码→每维相关性/MAE/定级，全链路端到端跑通，复用真实校准代码零改动。这证明 W8-03→W9 的**管道是通的**。
2. **相关性大概率虚高，不可当真值**：
   - AI 两个"编辑"是**同一个 temp=0 模型换 persona**，自我一致率 95%（43 中 41 个零分歧），仲裁几乎没被触发——真人双评不会这么一致（现有真人样本就有 borderline / strong_negative 分歧）。
   - AI reviewer 与被评对象**同源**，共享偏置，相关性天然偏高。
   - 因此「11/12 维 trusted」是**流程演练的产物**，不是「reviewer 已校准」的结论。
3. **唯一仍需真人的动作没变**：真正的 W9 校准要真人双评的 human_scores 作真值。本次只证明「一旦有真值，管道能算出定级」。**ai_voice_risk 即使在虚高环境下仍最弱（0.53）**，是一个真实信号：这个维度最难自动对齐，真人校准时应重点关注。

## 对周计划 §15.6 判据的影响

- 「人工真值闭环补齐」**判据未变（仍 🟡）**：本次是 AI 替身流程验证，不是真人真值。
- **增量**：W8-03→W9 管道已证明可端到端运行；真人评分一旦落到 human_scores.json，`reviewer-calibration backfill` + summary 即可直接产出定级。剩余纯属真人动作。
