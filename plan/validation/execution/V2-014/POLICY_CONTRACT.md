# V2-014 有界规则契约

本轮复用已接受ADR-007，只新增policy.py及当前任务测试，不改变既有Pack、Canon、CI或依赖。本文是任务内接口决定，不声称已验证运行。

## 输入与API

- `SourceDocument(id: EntityId, text: str)`：原始文本，SHA256绑定完整UTF-8字节；不得跨项目。
- `EvidenceSpan(source_id: EntityId, source_sha256: str, start: int, end: int, quote: str)`：Python Unicode字符半开区间[start,end)，索引严格整数且非bool；check时绑定同一原文、范围及逐字quote。
- `SemanticClaim(id: str, mechanism: Mechanism, context: ClaimContext, occurrence: Occurrence, evidence: EvidenceSpan, interpretation_ref: str)`：不可变、严格枚举；解释来源是可追溯输入，不是语义正确性证明。Occurrence复用domain.events，描述内层命题，不能把“确实做梦/确实说话”提升为梦/话中事件在真实世界发生。
- `GenrePolicy(binding: ProjectGenreBinding).check(document, claims: tuple[SemanticClaim,...])`：对全部输入求值，无claims为UNKNOWN；无自动关键词判决或语义抽取。
- `check_strategy(selection: StrategySelection, proposal: SourceDocument|None=None, claims=())`：校验完整原binding一致；MATCH需本次策略提案及同源claims，缺失为UNKNOWN；NO_MATCH只在无提案/claims时返回“无可选策略”的适用性PASS，原binding不变；不能夹带提案。
- `PolicyResult`含原binding、candidate ID/hash、政策version/hash、每条claim及rule/code/status诊断，status由诊断派生，不平均分或先遇PASS就返回；支持to_dict独立导出。scope为STRUCTURED_CLAIMS_ONLY或OPTIONAL_STRATEGY，`prose_coverage=NOT_VERIFIED`始终保留。政策hash绑定规则表、支持PackRef及version。结果不是CheckExecution、CommitPermit、Canon事实或整章Q2通过。

## 明确的有界规则

只支持已交付两Pack的精确ID/version/content_hash，不仅看anchor名称；新增或变更Pack须显式重新绑定规则、影响分析及重验。不从中文规则文本或文件名猜测政策。

`Mechanism`为ORDINARY_ACTION、LOCAL_TRADE、CULTIVATION、MAGIC、REBIRTH、SYSTEM、MODERN_CORPORATE_SCHEMA、COST_FREE_CULTIVATION_ADVANCE、UNKNOWN。

- 都市现实：普通现实行动/交易/现代公司制度在题材层允许；实际修炼、法术、重生、系统、无代价修炼进阶拒绝。
- 东方玄幻：普通行动、本世界交易、修炼在题材层允许；未声明现代公司股权财务制度、无代价修炼进阶拒绝；MAGIC/REBIRTH/SYSTEM在本有界政策未得到具体机制依据，返回UNKNOWN。
- 题材层允许不证明金额、境界、资源或合法转移已通过；这些仍属015/016等后续能力。

`ClaimContext`为WORLD、QUOTATION、DREAM、METAPHOR、BELIEF、HYPOTHESIS、LIE、UNKNOWN。上下文/机制/发生状态UNKNOWN则UNKNOWN；明确非世界上下文仅返回NOT_WORLD_FACT；明确NOT_OCCURRED仅返回NOT_OCCURRED；都不生成任何世界事实。剩余明确世界中已发生的命题才应用上列规则。

同一span/机制出现互相矛盾的context或occurrence时相关诊断为UNKNOWN，不让调用者用随便排列记录制造PASS/FAIL。独立明确违规的FAIL优先UNKNOWN，但保留全部诊断。重复claim ID、坏类型、错hash/quote、跨项目、错selection绑定等无效输入抛出PolicyError，不记录为PASS。

## 真实能力边界

本轮不验证上游语义标注的正确性或完整性，不以一个hash/span/interpretation_ref存在就宣称正文安全。遗漏或错误标注仍是已知上游风险，正文覆盖与真实模型/人工语义证据由后续Extractor/Q2及ADR-011负责。无claims即UNKNOWN；已知梦境内规则通过也不放行整个章节。未来消费者必须保留这些结果范围。

四项原验收保持不变，另覆盖现实合法样本、玄幻交易合法样本、近义/误导词不影响结果、证据篡改、未知语义、冲突标注、错Pack/项目、策略冲突/无命中和顺序无关性。P3/015/016、自动写作、小说阅读质量、外部备份不据此完成。
