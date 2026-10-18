# V2-006 本地领域实现

本轮实现人物、关系和角色知识投影，推进小说连续性所需的“谁知道什么、为什么这样行动”。状态为IMPLEMENTED；没有远程CI、任务验收或P1完成声明。实施与验证为同一Codex操作者，子代理只提供技术分工，不构成独立人员审核。

## 已实现和复现

- `src/anovel/domain/character.py`：Character继承稳定Entity身份，完整保留identity、生命周期、描述和别名；Relationship独立保存双方身份、类型集合及信任值。
- `src/anovel/domain/knowledge.py`：WorldFact、Observation、Belief、Goal和Intent独立建模；KnowledgeState仅通过匹配事实且包含该人物的观察记录显式取得知识。未取得的世界事实不泄漏给人物；误信允许继续存在并用于计划；计划不能被事实接口接受。
- 两份封闭JSON Schema与领域解析器使用共享正反例对账；整体快照恢复重放引用/取得检查，拒绝额外字段、未知类型、重复ID、跨书引用和伪造知识来源。
- 根目录`demo_v2_006.py`可直接运行：钥匙客观在东库，周宁误信西库，林岚观察后才知情，西库取钥匙计划不移动钥匙，完整快照往返不丢字段。

```bash
.venv/bin/python -B demo_v2_006.py
.venv/bin/python -B -m pytest -q -p no:cacheprovider tests/contract/test_v2_005.py tests/contract/test_v2_006.py
.venv/bin/python -B scripts/ci/run_gate.py arch_fitness --output-dir dist/validation/v2006-arch-new
.venv/bin/python -B scripts/check_governance.py --output-dir dist/validation/v2006-governance-new
```

四条AT-V2-006断言均有实际正负测试。非默认字段、合法非活动生命周期、改名保留派生字段、错误类型/来源、误信并存与计划分离分别受测；V2-006新增101项领域测试，连同V2-005共198项通过，0skip。首次完整UNIT保留742通过/3失败：一处旧夹具前提失效、两处本机uv缓存沙箱拒绝。夹具已最小修复，原断言保留并加强，专项15项通过；以净化环境获准重跑安装/构建，5项通过。最终固定提交的完整复核结果另外保存在dist/validation，不把不同工作区结果冒称为同一提交CI。

## 已知边界

这是内存领域能力；Observation只验证结构和关联，不认证正文语义。没有数据库、JSONB/API、Canon写入、事件发生/reducer、模型或正文生产实现。关系快照单独往返，不作为知识取得来源。

通用字符串谓词不假设单值函数关系；不同地点值不自动产生通用逻辑冲突。CONTRADICTORY目前只识别人物可见的同一主语/谓词布尔正反命题，作者可见但人物未取得的真相不参与判断。更复杂时态和推理留给真实后续消费者。

标准JSON Schema校验结构；跨记录项目一致性、ID唯一及观察取得关联由领域恢复器进一步校验。Schema的integer接受数学整数1.0，Python解析器对Goal.priority要求严格int；NaN/Infinity也不属于合法JSON，代码主动拒绝。测试明确区分这些表达边界，不声称Schema可以证明全部领域约束。

## 下一步

保留本地固定提交和真实测试结果，复核后再决定关键交付CI；本轮不push、不创建远程流水线。当前V2-006尚未VERIFIED/CLOSED，不能据本地PASS启动依赖其验收的后续任务。后续V2-007负责事件/时间线/Promise，V2-008负责增量/状态转移，正文知识检查属于后续质量消费者，本轮不提前扩建。
