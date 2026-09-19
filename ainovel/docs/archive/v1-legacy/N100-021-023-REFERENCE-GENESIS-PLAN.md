# N100-021 / N100-022 / N100-023 作品 Genesis 与百章规划冻结

## 目标

将通用 Long-Arc 投影器收敛到一部具体作品，冻结参考输入边界、开书 Constitution 与作品级 100 章 Long-Arc。

## N100-021 冻结参考输入边界

### 约束

- 只允许使用有合法依据的参考小说。
- 只抽象卖点、节奏、钩子、冲突结构与读者预期。
- 不保留可识别表达、人物名、独特桥段和可回溯文本。
- 参考输入必须可追溯到来源与授权说明。

### 推荐产物

- `reference-pack.json`
- `originality-boundary.md`
- `source-provenance-index.json`

## N100-022 冻结开书 Constitution

### Constitution 必备字段

- 题材
- 目标读者
- 核心卖点
- 主角欲望
- 核心冲突
- 世界规则
- 风格边界
- 禁区

### 验收标准

- Market Position 与 Novel Brain 不冲突。
- 角色核心与世界规则没有结构性矛盾。
- Constitution 可直接喂给作品级 Long-Arc。

### 推荐产物

- `book-constitution.json`
- `book-constitution-notes.md`

## N100-023 建作品级 100 章 Long-Arc

### 与通用 Long-Arc 的区别

通用版 Long-Arc 只是阶段模板；作品级 Long-Arc 必须绑定到具体题材、人物、世界规则与冲突梯度。

### 必须包含的内容

- 每 10 章一个 band
- 每个 band 的状态变化
- 每个 band 的 payoff
- 每个 band 的商业目标
- 每个 band 的换地图条件
- 每个 band 的目标与 Constitution 的可追溯关系

### 推荐产物

- `work-scoped-long-arc.json`
- `long-arc-crosswalk.json`
- `map-change-conditions.json`

## 现阶段结论

- 通用 `runtime/long_arc/plan.py` 已存在，且为纯 derived 投影器。
- 需要在 `N100-021 ~ N100-023` 中把具体作品输入边界和 Constitution 冻结，再用它生成作品级 Long-Arc。
- 当前仓库已具备把这条线继续做下去的结构，但还没有把某一部作品正式冻结成最终 Constitution。
