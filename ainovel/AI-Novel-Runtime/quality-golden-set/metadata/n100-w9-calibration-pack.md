# N100-013 W9 校准重跑包

## 来源

- `AI-Novel-Runtime/quality-golden-set/metadata/w9-calibration-results.json`
- `AI-Novel-Runtime/quality-golden-set/metadata/w9-calibration-summary.json`

## 结论

- 样本数：43
- skeleton seeds：7
- 校准状态：`complete_with_skeleton_seeds`
- 真人样本：43
- 被信任维度：11
- 决策维度：4
- 诊断维度：8

## 决策维度

- `opening_hook`
- `conflict_progression`
- `paying_intent`
- `continue_intent`

## 诊断维度

- `chapter_goal`
- `character_motivation`
- `emotion_flow`
- `information_density`
- `payoff_delivery`
- `ending_hook`
- `continuity`
- `ai_voice_risk`

## 关键阈值观察

- `opening_hook` correlation = 0.9220
- `conflict_progression` correlation = 0.8474
- `paying_intent` correlation = 0.8672
- `continue_intent` correlation = 0.8687

## 说明

- 这份包不是再训练模型，而是把已经完成的真人校准结果整理成可执行的重跑摘要。
- `N100-013` 在当前仓库中可视为已满足“重跑 + 汇总”的证据条件。
