# N100-024 Rolling 10-Chapter Plan

## 目标

将作品级 Long-Arc 细化为只覆盖未来 10–20 章的滚动计划，并把 checkpoint 之后的变更以记录方式保存。

## 适用原则

- 只规划未来章节，不重写已完成事实。
- 已完成目标必须退出活跃列表。
- 重大方向变更必须人工批准。
- 任何计划调整都必须可追溯到 Long-Arc band 与 Constitution。

## 计划结构

### 1. 活跃区间

- 当前 checkpoint：`cp-000`
- 活跃窗口：未来 10 章
- 预备窗口：未来 20 章

### 2. 每章记录字段

- `chapter_no`
- `band_id`
- `active_goal`
- `commercial_goal`
- `status`
- `risk_notes`
- `depends_on`
- `change_type`

### 3. 变更记录字段

- `change_id`
- `chapter_no`
- `before`
- `after`
- `reason`
- `approved_by`
- `approval_timestamp`
- `requires_recompute`

## 写回规则

- 完成的章节目标移出 `active_goals`。
- 仅允许向前推进，不允许回写历史事实。
- 若出现重大方向变更，必须先记录再执行。
- checkpoint 后只允许滚动更新未来 10–20 章。

## 推荐产物

- `rolling-10-chapter-plan.json`
- `rolling-change-records.json`
- `rolling-plan-crosswalk.json`

## 与 Long-Arc 的关系

滚动计划不是新规划层，而是 Long-Arc 的执行层投影：

- `Long-Arc` 提供 band 级目标与换地图条件。
- `Rolling Plan` 只负责把当前 band 展开成可执行的未来章节任务。
- checkpoint 之后重新折叠，保留历史连续性。

## 现阶段结论

`N100-024` 可被视为规划完成，但仍需要在真实作品冻结后接入实际章节数据，才能成为正式运行产物。
