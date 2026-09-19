# W9 Reviewer Calibration Report

- Status: `uncalibrated_insufficient_real_samples`
- Real samples (正文 ≥200 字): `3`
- Label-only samples (no prose body): `40`
- Scored rows: `43`
- Skeleton seeds: `7`
- Skipped samples: `0`
- Boundary samples: `5`

> **降级**：以下维度原标为 `decision`，但支撑它们的样本多为缺陷标签而非正文，已降为 `diagnostic`（可诊断、不可驱动自动选择）：
> `conflict_progression`, `continue_intent`, `opening_hook`, `paying_intent`
> 真实样本 3 个，低于下限 5。

## Dimension Stats
- `opening_hook`: level=diagnostic, scored_rows=43, real_samples=3, r=0.9220158685451215, mae=0.4883720930232558, ci95=0.25364023613941644
- `chapter_goal`: level=diagnostic, scored_rows=43, real_samples=3, r=0.794236897300607, mae=0.4069767441860465, ci95=0.24676979314625724
- `conflict_progression`: level=diagnostic, scored_rows=43, real_samples=3, r=0.8473846390777743, mae=0.4418604651162791, ci95=0.18508569729081215
- `character_motivation`: level=diagnostic, scored_rows=43, real_samples=3, r=0.7473856327402053, mae=0.4418604651162791, ci95=0.2192785259225658
- `emotion_flow`: level=diagnostic, scored_rows=43, real_samples=3, r=0.7835952654973312, mae=0.313953488372093, ci95=0.21638307076873106
- `information_density`: level=diagnostic, scored_rows=43, real_samples=3, r=0.6296084861106532, mae=0.6046511627906976, ci95=0.2364297877353318
- `payoff_delivery`: level=diagnostic, scored_rows=43, real_samples=3, r=0.7813776332388114, mae=0.5348837209302325, ci95=0.18561947113818927
- `ending_hook`: level=diagnostic, scored_rows=43, real_samples=3, r=0.8503850990436814, mae=0.5581395348837209, ci95=0.22877354632182628
- `continuity`: level=diagnostic, scored_rows=43, real_samples=3, r=0.7679807834113174, mae=0.7441860465116279, ci95=0.26966317150872676
- `ai_voice_risk`: level=diagnostic, scored_rows=43, real_samples=3, r=0.5283064784496544, mae=0.6395348837209303, ci95=0.328277980232837
- `paying_intent`: level=diagnostic, scored_rows=43, real_samples=3, r=0.8672243110837119, mae=0.686046511627907, ci95=0.17264002737412795
- `continue_intent`: level=diagnostic, scored_rows=43, real_samples=3, r=0.8686986353646816, mae=0.47674418604651164, ci95=0.22346840653261513

## Boundary Summary
- Mean continue probability: `0.5`
- Has evidence spans: `False`
- Has uncertainty: `True`

- Content hash: `2084a3bb76a26cbc806ba6b13407b0373e2adc67e79a034bd09fe8855531bb46`
