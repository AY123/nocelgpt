# V2-017：Planning 与 Contract 的实施分解

此执行包细化现有 V2-017，不新增任务身份、阶段、依赖，也不代表实现完成。最晚决定为 ADR-008；变化操作继续消费 ADR-004。验收以任务清单和测试目录同步断言为准。

## 最小职责

| 工作部分 | 输入与输出 | 建议归属 |
|---|---|---|
| 计划数据 | 人工 SeriesVision、Arc/Chapter/Scene 意图；ID、版本、parent 与作用域 | `src/anovel/planning/models.py` |
| 版本与冻结 | revision、superseded_by、冻结范围、失效原因及影响范围 | `src/anovel/planning/versions.py` |
| 修订提议 | Canon/Pack/目标变更与不可满足合约 → 有理由的 PlanDiff/ReplanProposal | `src/anovel/planning/replanning.py` |
| 合约数据 | 必需/禁止转移、保护事实、知识/揭示边界、接续证据 | `src/anovel/contracts/models.py` |
| 编译 | 指定计划版本 + frozen Canon + Pack/政策 → Contract 或诊断 | `src/anovel/contracts/compiler.py` |

目录为建议分工，不要求每个计划层都先创建独立文件；不要把版本管理、自动循环和数据库写入全部塞进 compiler。

## 必须决定的语义

1. 接受历史不能由计划改写；未来意图可修订，草稿与已冻结执行输入不同。
2. Freeze horizon 指定哪些候选章节/场景输入已绑定、哪些未来计划可调整；不把整本未来大纲永久冻结。
3. PlanVersion/PlanDiff 表达身份、理由、前后版本及 supersession。重规划提议没有 Canon 写权。
4. Canon、Pack、角色知识或前章正文变化后，标出受影响计划/合约/Context；未受影响内容可有依据地保留，禁止静默复用过期绑定。
5. 不可满足要求返回诊断和提议；授权采用新版本后重新编译、重验，不无限自动重规划，也不提前依赖 P10 Genesis。

## 顺序与验收

先定义计划/版本与失效，再定义 Contract 数据与编译，最后用两类人工 fixture 验证：合法初次编译、同输入结果绑定一致、冲突被诊断、旧版本失效、合法未来修订、已接受历史不变、错误信念和安静章节不被机械排除。正文接续和角色意图继续使用现有 AT-V2-017 场景。

P4 只完成最小受控规划和修订能力。自动滚动策略优化、复杂规划 Agent、全书自主重排属于后续真实需求决策，不由本包提前引入。
