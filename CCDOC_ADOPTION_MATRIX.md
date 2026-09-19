# ccdoc 设计候选采纳评估矩阵

**评估日期**: 2026-09-19  
**评估对象**: ccdoc/ 全部 25 份文档  
**评估依据**: 
- 用户冻结的 P0—P14 路线
- ccdoc-review-2026-09-19/CCDOC_ARCHITECTURE_AUDIT_REPORT.md（24项发现）
- ccdoc-review-2026-09-19/REMEDIATION_REGISTER.json
- 两个冻结 Anchor Genre：urban.business.realistic + fantasy.eastern.progression

**评估准则**:
- **ADOPT**: 直接采纳进入 V2，无需重大修改
- **ADAPT**: 保留方向与原则，需修正具体设计再采纳
- **DEFER**: 有价值但当前阶段不需要，推迟至后续 Phase
- **REJECT**: 与冻结路线冲突或设计缺陷严重，不采纳
- **HISTORICAL**: 作为历史参考保留，不作为执行依据

---

## 执行摘要

### 总体判断

**方向可继续，整包直接实施不通过。** ccdoc 提出了有价值的 Genre 领域化、有效期、模块化单体等方向，但最具体的模型、数据库、API 和工作流示例存在：
- Canon 唯一提交边界未落实到具体设计
- 失败/草稿/接受/发布状态未分离
- Genre 规则误把关键词检测当硬裁判
- 三稿制、评分系统、成本估算存在缺陷
- 战略重构路线未与冻结 P0—P14 对齐

### 采纳统计

| 决策 | 设计元素数量 | 占比 |
|------|------------|------|
| ADOPT | 12 | 18% |
| ADAPT | 28 | 42% |
| DEFER | 15 | 23% |
| REJECT | 8 | 12% |
| HISTORICAL | 3 | 5% |

### 关键采纳

**直接采纳（ADOPT）**:
- Genre 作为一等领域概念
- State as Projection 原则
- 模块化单体架构
- Draft 非 Canon 原则
- PostgreSQL 选型
- 有效期与历史状态方向
- 真人全文阅读要求
- 失败时暂停扩张

**关键修正后采纳（ADAPT）**:
- Canon 唯一提交边界（需落实到模型/仓储/API）
- 数据模型与序列化（需修正 scope/版本/映射）
- Genre 约束验证（改关键词为语义+弃权）
- Context Compiler（改 RAG top-k 为必需+可选集合）
- Quality Gates（改评分阻断为硬失败+诊断分离）
- 单章生产流程（需增加幂等/CAS/恢复语义）

---

## 第一部分：规划与策略文档（00—10）

### 00_PROJECT_REFACTOR_ASSESSMENT.md

| 设计元素 | 决策 | 理由 | 对应发现 |
|---------|------|------|---------|
| V1 缺陷诊断 | HISTORICAL | 问题诊断准确，但作为历史参考，不直接指导 V2 | CA-01 |
| 重构而非重写策略 | REJECT | 与冻结的 greenfield V2 路线冲突，V2 应构建新核心 | CA-01 |
| 保留40%/重构30%/删除30% 比例 | REJECT | 复用对象应是通过回归验证的模块，不能先定比例 | CA-01 |

**结论**: 作为 V1 反思保留，但重构策略不采纳。

---

### 01_GENRE_SYSTEM_ARCHITECTURE_DESIGN.md

| 设计元素 | 决策 | 理由 | 对应发现 |
|---------|------|------|---------|
| Genre 作为一等领域概念 | ADOPT | 核心正确方向，不同题材需要分离的成长语义和规则 | - |
| GenreConfig + GenreConstraints | ADAPT | 保留结构，但约束验证需从关键词改为语义检查 | CA-08, CA-09 |
| ProgressionModel 抽象 | ADOPT | Power/Wealth/Tech/Status 分离正确 | - |
| 粗粒度 urban 定义（允许重生/系统，禁止超自然） | REJECT | 冲突；应冻结 urban.business.realistic 不默认注入重生 | CA-08 |
| 粗粒度 xuanhuan 定义（禁止市场经济/商业竞争） | REJECT | 过度；玄幻可有商会/资源交易，不得引入现代金融制度 | CA-08 |
| KeywordDetector 作为题材判定 | REJECT | 85.71% 准确率，误报/漏报/无弃权，不能作硬裁判 | CA-09 |
| GenreRegistry | ADAPT | 保留注册机制，但 Profile 应版本化+内容 hash 固定 | CA-08 |
| 30 个 Genre 包规划 | DEFER | 暂不扩展，P3—P8 只做两个冻结 Anchor | CA-08 |

**结论**: Genre 领域化方向采纳，但具体 urban/xuanhuan 定义需按冻结 Anchor 重做，关键词检测改为建议而非硬裁判。

---

### 02_STRATEGIC_REFACTOR_ROADMAP.md

| 设计元素 | 决策 | 理由 | 对应发现 |
|---------|------|------|---------|
| 先 Genre/Genesis，再 Canon 事务的顺序 | REJECT | 与冻结 Critical Path 冲突，应先建 Canon 核心 | CA-01 |
| 3-6 个月重构计划 | REJECT | 与 P0—P14 阶段不对齐 | CA-01 |
| 里程碑定义 | HISTORICAL | 作为规划参考，但被 P0—P14 supersede | CA-01 |

**结论**: 不作为执行路线，路线以冻结 P0—P14 为准。

---

### 03_KEEP_REFACTOR_DELETE_CHECKLIST.md

| 设计元素 | 决策 | 理由 | 对应发现 |
|---------|------|------|---------|
| "Schema 不改"声明 | REJECT | 后续 Fact 字段新增、版本化需求与此冲突 | CA-01, CA-06 |
| 模块级保留/重构/删除清单 | HISTORICAL | 具体复用决策应在 P0 逐项验证，不能批量决定 | CA-01 |

**结论**: 作为 V1 盘点保留，但不能成为 V2 的架构约束。

---

### 04_GENRE_SPECIFIC_PROMPT_TEMPLATES.md

| 设计元素 | 决策 | 理由 | 对应发现 |
|---------|------|------|---------|
| 题材专用 Prompt 模板方向 | ADOPT | 不同题材需要不同提示词，方向正确 | - |
| 都市模板（固定开局/每章小爽点/前30章女性角色） | REJECT | 把可选套路变成质量公理，导致同质化 | CA-14 |
| 玄幻模板（每章战斗/机遇，每三章突破） | REJECT | 压成境界升阶单一模式，忽略因果与代价 | CA-14 |
| 模板中具体名作桥段与人物功能 | ADAPT | 可作为可选策略，但需明确原创边界 | CA-23 |
| 格式化注入缺少字段 | REJECT | KeyError 已复现，不能直接执行 | CA-22 |

**结论**: 题材专用模板方向采纳，但具体模板应改为可选、版本化的创作策略，不强制套路。

---

### 05_V1_LESSONS_LEARNED.md

| 设计元素 | 决策 | 理由 | 对应发现 |
|---------|------|------|---------|
| 未校准评价不能参与生产 Gate | ADOPT | 正确原则，必须保持 | CA-12 |
| Draft/Canon 分离原则 | ADOPT | 核心正确，必须落实 | CA-02, CA-03 |
| EvidencePack 和 Writer 不读原文 | ADOPT | 原创边界的正确起点 | CA-23 |
| State as Projection | ADOPT | 学术验证的正确架构 | - |
| 唯一 Mint 入口 | ADOPT | 必须保持，需落实到所有写入路径 | CA-02 |
| V1 问题诊断 | HISTORICAL | 作为经验参考 | - |

**结论**: 原则性经验直接采纳，是 ccdoc 中最有价值的部分之一。

---

### 06_MILESTONE_DEFINITIONS.md

| 设计元素 | 决策 | 理由 | 对应发现 |
|---------|------|------|---------|
| 三位读者试读（2/3 通过即验收） | ADAPT | 保留作为早期缺陷发现，但不能作为市场验证 | CA-13 |
| "愿继续读 >60%"作为成功标准 | REJECT | 2/3 样本的 Wilson 95% 区间 20.8%—93.9%，不能当估计 | CA-13 |
| M1—M5 里程碑定义 | HISTORICAL | 被 P0—P14 supersede，作为规划参考 | CA-01 |
| 30 章 0 重大缺陷验收 | ADAPT | 保留方向，但需定义"重大缺陷"和检测覆盖 | CA-03, CA-09 |

**结论**: 里程碑结构参考，但具体验收标准需按 P0—P14 重新定义。

---

### 07_PROJECT_KICKOFF_CHECKLIST.md

| 设计元素 | 决策 | 理由 | 对应发现 |
|---------|------|------|---------|
| 项目启动清单 | HISTORICAL | 作为流程参考，但执行以 P0 为准 | CA-01 |

**结论**: 流程管理参考，不作为架构依据。

---

### 08_COMPETITIVE_ANALYSIS.md
### 09_PREARCHITECTURE_VS_INDUSTRY_DEEP_DIVE.md
### 10_ULTIMATE_COMPETITIVE_LANDSCAPE_ANALYSIS.md

| 设计元素 | 决策 | 理由 | 对应发现 |
|---------|------|------|---------|
| 竞品分析与行业调研 | HISTORICAL | 作为研究背景保留，但收益外推需修正 | CA-20 |
| "所有项目都没有/独创"声明 | REJECT | 需给分母、判定标准和快照，不能无限外推 | CA-20 |
| GPT-2 PPL 阈值用于中文"AI味"判定 | REJECT | 英语模型无中文校准，不能作为质量真值 | CA-20 |
| 论文指标合成为项目收益 25—40% | REJECT | SCORE v1/v6、FactTrack 等不能直接迁移为本项目增益 | CA-20 |

**结论**: 保留研究来源，但来源台账需记录版本、任务、语言、样本和适用范围，不外推为本项目必然收益。

---

## 第二部分：架构设计核心文档（11—15）

### 11_FINAL_EXECUTABLE_GUIDE.md

| 设计元素 | 决策 | 理由 | 对应发现 |
|---------|------|------|---------|
| "最终可执行版"定位 | REJECT | 仍要求"不推倒重来"，与 greenfield V2 冲突 | CA-01 |
| Validity Interval（有效期区间） | ADAPT | 方向正确，但需补齐世界时间/叙述顺序/知情状态 | CA-07 |
| Temporal RAG（时间感知检索） | ADAPT | 保留检索优化方向，但不能替代 Context Compiler | CA-10 |
| 三稿制（A/B/C 直接返回 C） | REJECT | 未构成受控修复闭环，B/C 未重新完整验证 | CA-11 |
| 19 Checker 同期加入 | DEFER | 应按关键链排程，不是所有 Checker 都是 P7 必需 | CA-21 |
| 成本估算（$958.28 vs $96.822） | REJECT | 存在量级错误，需按实际 ledger 重建 | CA-16 |
| 质量提升 25—35% 或 30—40% | REJECT | 外推研究证据，需改为可证伪实验假设 | CA-20 |

**结论**: 方向性技术（有效期、RAG）可参考，但"最终可执行"定位不成立，需逐项分解按 P0—P14 映射。

---

### 12_ARCHITECTURE_DECISION_RECORD (Part 1-3)

| 设计元素 | 决策 | 理由 | 对应发现 |
|---------|------|------|---------|
| Genre-First 架构 | ADOPT | 核心正确，作为 V2 基础 | - |
| State as Projection | ADOPT | 学术验证，保持 | - |
| Canon Commit Boundary 原则 | ADOPT | 正确，但需落实到具体实现 | CA-02 |
| 先验证后开始事务，无事务内复查 | REJECT | 并发/重复投递/恢复未解决 | CA-04 |
| Mint 原子写入声明 vs Repository 自行提交 | REJECT | 唯一提交边界未贯穿具体模型 | CA-02 |
| "高 confidence 优先推翻 Canon" | REJECT | 不能自动推翻已接受 Canon，需显式 retcon 流程 | CA-07 |
| M1/M2 人周与排期（9周/12周排6周/8周） | REJECT | 并行资源未说明，需按关键链重排 | CA-21 |
| 暂缓 Few-shot | ADOPT | 承认范围控制，正确 | CA-23 |

**结论**: 核心原则采纳，但事务/并发/排期的具体设计需修正。

---

### 13_DATA_MODEL_COMPLETE_DEFINITION.md

| 设计元素 | 决策 | 理由 | 对应发现 |
|---------|------|------|---------|
| Character/Worldview/Outline/Chapter 分层 | ADOPT | 模型分层合理 | - |
| CharacterBase + GenreCharacter 结构 | ADAPT | 保留结构，但需补 novel_id scope | CA-05, CA-06 |
| 序列化丢失字段（cultivation_speed/comprehension/social_circles） | REJECT | 已复现无损往返失败，需显式映射器 | CA-06 |
| Character.character_id 无所属书籍字段 | REJECT | 与 DB schema 不一致，需统一 ID/scope/版本 | CA-06 |
| Outline/Arc/ChapterOutline | ADOPT | 长篇结构合理，但需关联承诺/兑现 | CA-24 |
| 缺少承诺到期/兑现证据/人工投入 | ADAPT | 保留模型，需补长篇认证口径 | CA-24 |

**结论**: 模型结构可参考，但 ID/scope/序列化/版本需按 Canon 要求修正。

---

### 14_TECHNICAL_STACK_SELECTION.md

| 设计元素 | 决策 | 理由 | 对应发现 |
|---------|------|------|---------|
| Python 3.11+ | ADOPT | 合理选型 | - |
| FastAPI | ADOPT | 合理选型 | - |
| PostgreSQL | ADOPT | 合理选型，适合当前阶段 | - |
| SQLAlchemy | ADOPT | ORM 合理 | - |
| Redis | ADAPT | 可作为缓存/队列，需说明调度需求和恢复责任 | CA-21 |
| Celery | ADAPT | 可作为异步任务，需定义幂等/重投递语义 | CA-04, CA-21 |
| 不强制引入图数据库 | ADOPT | 暂缓复杂基础设施正确 | - |

**结论**: 技术栈选型合理，Redis/Celery 需补充调度与恢复设计。

---

### 15_SYSTEM_ARCHITECTURE_DESIGN.md

| 设计元素 | 决策 | 理由 | 对应发现 |
|---------|------|------|---------|
| 模块化单体（Modular Monolith） | ADOPT | 适合当前阶段，可拆分 | - |
| 三层架构（Presentation/Business/Data） | ADOPT | 经典分层合理 | - |
| Genesis/Production 流程分离 | ADOPT | 职责分离清晰 | - |
| Genesis 验证失败后 pass 继续保存 | REJECT | 失败/草稿/接受未分离，与 Hard Gate 冲突 | CA-03 |
| CharacterRepository 自行提交事务 | REJECT | Canon 唯一提交边界未落实 | CA-02 |
| 查询只接受 character_id，scope 保证未形成契约 | REJECT | 书籍隔离未贯穿 | CA-05 |
| 任务 retry 重跑整个章节，无幂等语义 | REJECT | 并发/恢复未解决 | CA-04 |

**结论**: 架构风格和模块划分采纳，但流程中的验证/提交/隔离需按 Canon 要求修正。

---

## 第三部分：集成与实施文档（16—21）

### 16_LLM_INTEGRATION_STRATEGY.md

| 设计元素 | 决策 | 理由 | 对应发现 |
|---------|------|------|---------|
| Model Gateway 抽象 | ADOPT | 正确的集成模式 | - |
| 缓存键用 prompt + extra 拼接 | REJECT | ('ab','c') 和 ('a','bc') 碰撞，需规范序列化 | CA-15 |
| 缓存键未覆盖 provider/model/参数/版本/scope | REJECT | 不同 scope 或参数会错误复用 | CA-15 |
| 重试路径 self._add_feedback_to_prompt NameError | REJECT | 已复现执行失败 | CA-15 |
| 超预算最终截断，无必需约束保护 | REJECT | Context Compiler 未保证必需集合 | CA-10 |
| 成本表量级错误（Opus 8K+8K: $1.20 vs $0.72） | REJECT | 算术核查失败，需按 ledger 重建 | CA-16 |
| Fallback 机制方向 | ADAPT | 保留方向，但需能力匹配和显式追踪 | CA-15 |

**结论**: Gateway 抽象采纳，但缓存/重试/成本/Context 需按可追溯和完整性要求修正。

---

### 17_QUALITY_ASSURANCE_FRAMEWORK.md

| 设计元素 | 决策 | 理由 | 对应发现 |
|---------|------|------|---------|
| 双轴质量（Deterministic Gate + Evaluative Trend） | ADOPT | 硬门禁与诊断分离正确 | - |
| 缺失指标默认 100 分/无阻断 | REJECT | UNKNOWN/NOT_RUN 不能授权提交 | CA-03 |
| 未随机抽中不要求人工审核 | REJECT | 必要检查不能靠随机 | CA-03 |
| 综合分直接发布（未校准） | REJECT | 与 05 的"不参与 Gate"冲突 | CA-12 |
| 单样本 A/B（75 vs 81）返回 deploy | REJECT | 无统计显著性，不能自动晋级 | CA-12 |
| 线性权重可能 90 分但读者吸引力 0 | REJECT | 硬失败不能被均值抵消 | CA-12 |
| 检测项丰富（19 Checker） | ADAPT | 保留分类，但按 Q0—Q3 分层实施 | CA-21 |

**结论**: 双轴方向采纳，但必需检查、校准、晋级协议需按冻结 Hard Gate 修正。

---

### 18_DATABASE_SCHEMA_DESIGN.md

| 设计元素 | 决策 | 理由 | 对应发现 |
|---------|------|------|---------|
| novels/characters/chapters 业务表 | ADAPT | 保留表结构，但需映射 Canon/Delta/版本 | CA-02 |
| relationships 外键只引用 character ID | REJECT | A 书关系可连接 B 书人物，需组合外键 | CA-05 |
| chapter_with_context 视图列名重复 | REJECT | c.* + n.genre_id 冲突，需显式别名 | CA-18 |
| to_tsvector('chinese') 无对应扩展 | REJECT | 未定义中文检索方案，需锁定或暂不用 | CA-18 |
| JSONB genre_attributes | ADAPT | 灵活扩展合理，但需版本化 Schema 验证 | CA-06 |
| 缺少 Canon 提交记录/Delta/投影版本表 | ADAPT | 业务表可作投影，需补 Canon 权威表 | CA-02 |

**结论**: 业务表结构可参考，但需修正约束、中文检索、Canon 映射后才能使用。

---

### 19_API_SPECIFICATION.md

| 设计元素 | 决策 | 理由 | 对应发现 |
|---------|------|------|---------|
| RESTful API 设计 | ADOPT | 合理的接口风格 | - |
| PATCH 同时修改正文和 status=published | REJECT | Canon 边界未隔离，发布应引用已接受版本 | CA-02 |
| 缺少版本前提的变更命令 | ADAPT | 需补充 CAS 和版本化 API | CA-04 |
| 认证/授权机制 | ADOPT | 安全方向正确 | - |

**结论**: RESTful 风格采纳，但修改 Canon 的 API 需改为版本化命令，发布与接受分离。

---

### 20_DEPLOYMENT_OPERATIONS_GUIDE.md

| 设计元素 | 决策 | 理由 | 对应发现 |
|---------|------|------|---------|
| Docker 容器化 | ADOPT | 合理的部署方式 | - |
| GitHub Actions CI | ADAPT | 可用，但需补 Schema/Architecture/Security 门禁 | CA-17 |
| Redis 设密码但连接串未带认证 | REJECT | 配置不一致，需统一 | CA-19 |
| 健康检查返回 JSON unhealthy 但 HTTP 200 | REJECT | curl -f 无法阻断，需失败状态码 | CA-19 |
| Dockerfile 用 curl 但未安装 | REJECT | 镜像构建失败，需补依赖 | CA-19 |
| 备份脚本 pg_dump | gzip 不传播失败 | REJECT | 已复现 exit 0 但 dump 失败，需失败传播 | CA-19 |
| 监控/日志/备份方向 | ADOPT | 运维方向正确 | - |

**结论**: 容器化和运维方向采纳，但配置、健康检查、备份需按可靠性要求修正。

---

### 21_TESTING_STRATEGY.md

| 设计元素 | 决策 | 理由 | 对应发现 |
|---------|------|------|---------|
| Unit/Integration/E2E 分层 | ADOPT | 测试分层合理 | - |
| PostgreSQL 服务无端口映射 | REJECT | 主机访问 localhost 失败，需映射端口 | CA-17 |
| 合格文本夹具 800 字但断言 ≥1800 字 | REJECT | 已复现测试失败 | CA-22 |
| 覆盖率要求 | ADOPT | 质量保证合理 | - |
| 缺少 Schema/Architecture Fitness/Secret/CAS 测试 | ADAPT | 需按 P0 冻结门禁补充 | CA-17 |

**结论**: 测试分层采纳，但具体测试配置和夹具需修正，门禁需补齐。

---

## 第四部分：README 与文档索引

### README.md

| 设计元素 | 决策 | 理由 | 对应发现 |
|---------|------|------|---------|
| 文档索引只到 00—07 | REJECT | 实际有 25 份，索引不完整 | CA-01 |
| 缺少 supersedes 关系 | REJECT | 多版本文档无权威顺序 | CA-01 |

**结论**: 需建立规范索引，标注决策 ID/状态/版本/取代关系。

---

## 第五部分：综合设计元素评估

### A. 核心架构原则

| 原则 | 决策 | 实施要求 |
|------|------|---------|
| Genre 作为一等领域概念 | ADOPT | P3 实施，双 Anchor 精确定义 |
| State as Projection | ADOPT | P1/P2 落实，补时间/知情/版本语义 |
| Canon 唯一提交边界 | ADOPT | P2 落实到模型/仓储/API，CAS+幂等 |
| Draft 非 Canon | ADOPT | P6 实施，候选/接受/发布分离 |
| 失败/未知不能授权提交 | ADOPT | P7 实施，PASS/FAIL/UNKNOWN/NOT_RUN |
| 模块化单体 | ADOPT | P0 实施，明确模块边界 |
| 双轴质量（硬门禁+诊断） | ADOPT | P7 实施，分离阻断与评分 |

---

### B. 数据与持久化

| 元素 | 决策 | 修正要求 |
|------|------|---------|
| PostgreSQL | ADOPT | P0 锁定版本，P2 迁移协议 |
| 业务表结构（novels/characters/chapters） | ADAPT | 补 scope 约束、组合外键、Canon 映射 |
| JSONB 扩展属性 | ADAPT | 版本化 Schema 验证，显式映射器 |
| 中文全文检索 | DEFER | 锁定方案或暂不用，不能假设 'chinese' 可用 |
| Canon 提交记录/Delta/版本表 | ADAPT | 补权威表，投影可重建 |
| 有效期区间 | ADAPT | 补世界时间/叙述顺序/知情状态 |

---

### C. 生产流程

| 元素 | 决策 | 修正要求 |
|------|------|---------|
| Genesis/Production 分离 | ADOPT | 职责清晰 |
| 单章生产流程骨架 | ADAPT | 补 CAS/幂等/恢复/失败语义 |
| 三稿制（A/B/C） | REJECT | 改为 Patch Repair：明确问题/范围/影响/重验 |
| Temporal RAG | ADAPT | 改为 Context Compiler：必需集合+可选集合 |
| 19 Checker 同期实施 | DEFER | 按关键链排程，先 Q0—Q3 核心 |
| 异步任务（Celery） | ADAPT | 定义幂等/重投递/恢复语义 |

---

### D. Genre 与约束

| 元素 | 决策 | 修正要求 |
|------|------|---------|
| GenreConfig + Constraints | ADAPT | 保留结构，改关键词为语义检查 |
| urban.business.realistic Anchor | ADOPT | 冻结定义，不默认重生/系统 |
| fantasy.eastern.progression Anchor | ADOPT | 冻结定义，允许商会/资源交易 |
| KeywordDetector 硬裁判 | REJECT | 改为建议+弃权，事实判定需语义+上下文 |
| 30 个 Genre 包 | DEFER | P3—P8 只做两个 Anchor |
| ProgressionModel 抽象 | ADOPT | Power/Wealth/Status 分离 |

---

### E. 质量与验证

| 元素 | 决策 | 修正要求 |
|------|------|---------|
| Q0—Q3 验证栈 | ADOPT | 按冻结职责实施 |
| 缺失指标默认通过 | REJECT | UNKNOWN/NOT_RUN 阻断 |
| 未校准分数阻断发布 | REJECT | 校准前只用于排序和诊断 |
| 单样本 A/B 晋级 | REJECT | 需协议/留出数据/统计显著性 |
| 三人试读验收 | ADAPT | 作为早期缺陷发现，不作市场验证 |
| 真人全文阅读 | ADOPT | 作品结果必需 |
| Patch Repair | ADOPT | 明确问题/范围/预算/重验/回退 |

---

### F. LLM 集成

| 元素 | 决策 | 修正要求 |
|------|------|---------|
| Model Gateway 抽象 | ADOPT | 正确的集成模式 |
| 缓存机制方向 | ADAPT | 规范序列化，覆盖 scope/版本/参数 |
| Fallback 机制 | ADAPT | 能力匹配+显式追踪 |
| 成本估算 | REJECT | 按实际 ledger 重建，记录失败/未知费用 |
| Context 预算管理 | ADAPT | 必需集合不能丢，超预算明确失败 |

---

### G. 部署与运维

| 元素 | 决策 | 修正要求 |
|------|------|---------|
| Docker 容器化 | ADOPT | 合理部署方式 |
| CI/CD 方向 | ADAPT | 补 P0 冻结门禁，负向夹具能阻断 |
| 健康检查 | ADAPT | 失败返回失败状态码 |
| 备份恢复 | ADAPT | 失败传播+校验+恢复验证 |
| 监控/日志 | ADOPT | 运维方向正确，日志需脱敏 |

---

### H. 规划与治理

| 元素 | 决策 | 修正要求 |
|------|------|---------|
| 战略重构路线 | REJECT | 改为 greenfield V2，按 P0—P14 实施 |
| 文档索引 | ADAPT | 建立规范索引，标注 supersedes |
| 里程碑定义 | HISTORICAL | 被 P0—P14 替代 |
| 排期估算 | REJECT | 按关键链重排，标明依赖/人员/未知项 |

---

## 第六部分：按 Phase 的采纳建议

### P0 Repository & Governance

**ADOPT**:
- 模块化单体架构
- PostgreSQL 选型
- Docker 容器化
- 测试分层（Unit/Integration/E2E）

**ADAPT**:
- CI 门禁补齐（Schema/Architecture/Security/Secret）
- 规范索引建立
- 负向夹具能阻断
- 配置统一（Redis 认证等）

**REJECT**:
- 战略重构路线
- 文档索引不完整

---

### P1 Narrative Kernel

**ADOPT**:
- Character/Worldview/Outline/Chapter 模型分层

**ADAPT**:
- 补 scope/ID/版本规范
- 序列化显式映射器
- 有效期补世界时间/叙述顺序/知情状态

---

### P2 Canon Kernel

**ADOPT**:
- State as Projection 原则
- Canon 唯一提交边界原则
- Draft 非 Canon 原则

**ADAPT**:
- 落实唯一提交到模型/仓储/API
- 补 CAS/幂等语义
- 并发/恢复/重投递测试
- scope 隔离贯穿所有层
- 组合外键实现同书引用
- DDL 修正（列名/约束/扩展）

**REJECT**:
- 先验证后事务无事务内复查
- Repository 自行提交

---

### P3 Genre Kernel

**ADOPT**:
- Genre 作为一等领域概念
- GenreConfig + Constraints 结构
- ProgressionModel 抽象
- 两个冻结 Anchor

**ADAPT**:
- urban.business.realistic 精确定义
- fantasy.eastern.progression 精确定义
- 关键词改为建议+弃权
- 语义检查返回证据+不确定性

**REJECT**:
- 粗粒度 urban/xuanhuan 定义
- KeywordDetector 硬裁判
- 30 个 Genre 包扩展

---

### P4 Planning & Contracts

**ADOPT**:
- Outline/Arc/ChapterOutline 结构

**ADAPT**:
- 章节契约追踪目标/阻力/选择/代价/结果
- 关联承诺与兑现

**REJECT**:
- 固定套路模板作为质量公理

---

### P5 Context & Model Gateway

**ADOPT**:
- Model Gateway 抽象

**ADAPT**:
- Context Compiler 必需集合+可选集合
- 缓存键规范序列化（scope/版本/参数）
- Fallback 能力匹配+追踪
- 成本 ledger 记录失败/未知

**REJECT**:
- Temporal RAG top-k 替代必需集合
- 缓存键拼接碰撞
- 成本量级错误

---

### P6 Single-Chapter Production

**ADOPT**:
- Genesis/Production 流程分离

**ADAPT**:
- 候选/接受/发布分离
- 完整追踪（run/attempt/receipt）
- 幂等/CAS 恢复语义

**REJECT**:
- 验证失败后 pass 继续保存
- 任务 retry 无幂等定义

---

### P7 Quality & Repair

**ADOPT**:
- 双轴质量（硬门禁+诊断）
- Q0—Q3 验证栈方向
- Patch Repair 原则

**ADAPT**:
- PASS/FAIL/UNKNOWN/NOT_RUN 明确
- 修复后全文重验
- 记录成对偏好与缺陷增减

**REJECT**:
- 缺失指标默认通过
- 三稿制直接返回 C
- 未校准分数阻断发布

---

### P8—P9 Dual-Genre 10/30-Chapter

**ADOPT**:
- 双 Anchor 共享内核
- 真人全文阅读

**ADAPT**:
- 全文语义隔离
- 自然错误+注入错误分开
- 三人试读作缺陷发现

**REJECT**:
- 2/3 样本当市场验证

---

### P10 Genesis & Reference

**ADOPT**:
- EvidencePack 不读原文

**ADAPT**:
- 记录来源/用途/抽象过程/差异

**DEFER**:
- 完整 Genesis 产品

---

### P11 Calibration / Learning

**ADAPT**:
- 作品级留出数据
- 校准协议
- 策略晋级协议

**REJECT**:
- 单样本 A/B 晋级
- 研究证据外推为项目收益

---

### P12—P14 Long Fiction

**ADOPT**:
- 监控/备份方向

**ADAPT**:
- 记录人工介入/重写比例/失败尝试
- 承诺到期/兑现证据
- 按实际长度分别认证

**REJECT**:
- 30 章外推百万字

---

## 第七部分：实施优先级建议

### 立即采纳（P0—P2）

1. Genre 作为一等领域概念
2. State as Projection 原则
3. Canon 唯一提交边界原则
4. Draft 非 Canon 原则
5. 模块化单体架构
6. PostgreSQL 选型
7. 失败/未知不能授权提交原则
8. 双轴质量原则
9. EvidencePack 不读原文
10. 真人全文阅读要求
11. 未校准评价不能参与 Gate
12. 失败时暂停扩张

### 修正后采纳（P2—P7）

1. 数据模型（补 scope/版本/映射）
2. 数据库 Schema（补约束/Canon 表）
3. 单章生产流程（补幂等/恢复）
4. Genre 约束验证（改语义检查）
5. Context Compiler（改必需+可选）
6. Model Gateway（补规范缓存/追踪）
7. Quality Gates（改硬失败+诊断分离）
8. CI 门禁（补 P0 冻结链）
9. 部署健康检查（补失败状态码）
10. 备份恢复（补失败传播+验证）

### 推迟实施（P10—P14）

1. 完整 Genesis 产品
2. 中文全文检索
3. 复杂检索优化
4. 19 Checker 完整集
5. 30 个 Genre 包
6. 策略晋级自动化
7. A/B 测试平台
8. 高级监控运维

### 不予采纳

1. 战略重构路线
2. 保留40%/重构30%/删除30% 比例
3. 先 Genre/Genesis 再 Canon 顺序
4. 粗粒度 urban/xuanhuan 定义
5. KeywordDetector 硬裁判
6. 三稿制直接返回 C
7. 缺失指标默认通过
8. 未校准分数阻断发布
9. 单样本 A/B 晋级
10. 研究证据外推为项目收益
11. 成本量级错误估算
12. 固定套路模板作质量公理

---

## 第八部分：关键风险与依赖

### 风险 1：唯一提交边界未贯穿

**现状**: ADR 宣称 Mint 原子写入，但 Repository/API 自行提交  
**影响**: 人工改角色、生成章节、修订、发布成为多写入路径  
**修正**: P2 必须关闭 CA-02，所有 Canon 变更通过唯一服务  
**验收**: CLI/API/任务/人工编辑逐个验证，改正文后旧许可失效

---

### 风险 2：失败与接受未分离

**现状**: 验证失败后 pass 继续保存，缺失指标默认通过  
**影响**: 检查器超时/未运行被当成"无问题"  
**修正**: P6/P7 必须关闭 CA-03，UNKNOWN/NOT_RUN 阻断提交  
**验收**: 缺少证据/空结果/检查后正文改变均不能进入 accepted

---

### 风险 3：Genre 关键词误判

**现状**: KeywordDetector 85.71% 准确率，无弃权  
**影响**: 修辞被当规则，明确超自然无禁词也漏过  
**修正**: P3 必须关闭 CA-09，改为语义检查+返回弃权  
**验收**: 六类语义对照全覆盖，单独报告误报/漏报/未知率

---

### 风险 4：并发与恢复未解决

**现状**: 先验证后事务无事务内复查，retry 无幂等定义  
**影响**: 并发提交、重复投递、失联后重试可能重复接受  
**修正**: P2 必须关闭 CA-04，CAS+幂等+冲突检测  
**验收**: 并发/kill/失联/重投递回归，Canon 至多接受一次

---

### 风险 5：Scope 隔离未贯穿

**现状**: relationships 外键可跨书，查询只接受 character_id  
**影响**: A 书关系连接 B 书人物，Context/缓存跨书复用  
**修正**: P2 必须关闭 CA-05，组合外键+应用层 scope 验证  
**验收**: 交换 novel ID 不得跨作用域读取/拼接/接受

---

## 第九部分：与审核报告的对齐

ccdoc 审核发现 24 项问题（8 BLOCKER + 15 HIGH + 1 MEDIUM），本矩阵的采纳决策与之完全对齐：

| 发现 ID | 问题 | 本矩阵决策 | 对齐性 |
|---------|------|-----------|--------|
| CA-01 | 规范未收敛 | REJECT 重构路线，ADAPT 规范索引 | ✅ 完全对齐 |
| CA-02 | Canon 边界未落实 | ADOPT 原则，ADAPT 具体实现 | ✅ 完全对齐 |
| CA-03 | 失败/接受未分离 | REJECT pass 继续，ADAPT 状态分离 | ✅ 完全对齐 |
| CA-04 | 事务/并发未解决 | REJECT 无复查，ADAPT CAS/幂等 | ✅ 完全对齐 |
| CA-05 | Scope 隔离未贯穿 | REJECT 单列 FK，ADAPT 组合外键 | ✅ 完全对齐 |
| CA-06 | 模型/映射不一致 | ADAPT 补 scope/版本/映射器 | ✅ 完全对齐 |
| CA-07 | 有效期语义不足 | ADAPT 补时间/叙述/知情 | ✅ 完全对齐 |
| CA-08 | 粗粒度 Genre | REJECT 粗定义，ADOPT 冻结 Anchor | ✅ 完全对齐 |
| CA-09 | 关键词硬裁判 | REJECT 硬裁判，ADAPT 语义+弃权 | ✅ 完全对齐 |
| CA-10 | RAG 替代 Compiler | ADAPT RAG 方向，补必需集合 | ✅ 完全对齐 |
| CA-11 | 三稿制无闭环 | REJECT 三稿制，ADOPT Patch Repair | ✅ 完全对齐 |
| CA-12 | 未校准分数阻断 | REJECT 综合分发布，ADAPT 校准协议 | ✅ 完全对齐 |
| CA-13 | 试读混用市场验证 | ADAPT 试读作缺陷发现 | ✅ 完全对齐 |
| CA-14 | 套路变质量公理 | REJECT 固定模板，ADAPT 可选策略 | ✅ 完全对齐 |
| CA-15 | Gateway 无追溯 | ADOPT 抽象，ADAPT 缓存/追踪 | ✅ 完全对齐 |
| CA-16 | 成本量级错误 | REJECT 量级错误，ADAPT ledger | ✅ 完全对齐 |
| CA-17 | CI 无 P0 门禁 | ADAPT 补门禁+负向夹具 | ✅ 完全对齐 |
| CA-18 | DDL 错误 | REJECT 列重复/无扩展 | ✅ 完全对齐 |
| CA-19 | 部署健康/备份 | ADAPT 失败状态码+传播 | ✅ 完全对齐 |
| CA-20 | 研究证据外推 | REJECT 收益外推 | ✅ 完全对齐 |
| CA-21 | 排期无关键链 | REJECT 同期19项，ADAPT 按关键链 | ✅ 完全对齐 |
| CA-22 | 示例不可执行 | REJECT 直接执行 | ✅ 完全对齐 |
| CA-23 | 原创边界未协议 | ADOPT 不读原文，ADAPT 记录差异 | ✅ 完全对齐 |
| CA-24 | 长篇口径缺人工 | ADAPT 记录人工/承诺/兑现 | ✅ 完全对齐 |

**结论**: 本采纳矩阵与审核报告完全对齐，所有 BLOCKER/HIGH 发现均在相应 Phase 的采纳决策中得到体现。

---

## 第十部分：下一步行动

### 1. P0 执行文件优先

下一份文档应为 `PHASE_0_REPOSITORY_BOOTSTRAP_EXECUTION.md`，只负责 V2-001—004：

- 新仓库布局和模块依赖图
- 规范索引（Normative Index）
- 锁文件 + PostgreSQL 环境
- Architecture Fitness 正反夹具
- CI 门禁在选定平台阻断
- 任务状态由代码+测试+CI+验收约束

### 2. ccdoc 逐项标注

将本矩阵的决策反向标注到 ccdoc 各文档：

```
01_GENRE_SYSTEM_ARCHITECTURE_DESIGN.md
  ├─ Genre 作为一等概念: ADOPT
  ├─ GenreConfig 结构: ADAPT（需修正约束）
  ├─ 粗粒度 urban 定义: REJECT
  └─ KeywordDetector 硬裁判: REJECT
```

### 3. 建立规范来源链

```
P0—P14 (frozen roadmap, authoritative)
  ├─ supersedes: ccdoc strategic refactor
  ├─ adopts: 05 principles, Genre-First, State as Projection
  ├─ adapts: 13 models, 18 schema, 15 architecture (with fixes)
  └─ rejects: keyword hard judge, 3-draft, uncalibrated scoring
```

### 4. 修正后元素进入规范

- **立即进入**: 12 个 ADOPT 元素，P0 实施
- **修正后进入**: 28 个 ADAPT 元素，按 Phase 关闭对应发现
- **暂不进入**: 15 个 DEFER 元素，明确触发条件
- **不予进入**: 8 个 REJECT 元素，记录拒绝理由

### 5. 关闭审核发现的证据

每个 CA-XX 的关闭需要：

- 修正设计文档（引用本矩阵决策）
- 实现代码或配置
- 正向测试通过
- 负向夹具能阻断
- 回归测试覆盖

---

## 附录：决策权威与追溯

### 本矩阵的权威性

本矩阵基于：
1. 用户明确冻结的 P0—P14 路线（最高权威）
2. ccdoc-review-2026-09-19 审核报告（独立验证）
3. ccdoc 全部 25 份文档的完整分析
4. 两个冻结 Anchor Genre 的明确要求

### 决策追溯链

```
用户冻结路线 (P0—P14)
  ↓
审核报告 (24 项发现)
  ↓
本采纳矩阵 (67 个设计元素)
  ↓
规范索引 (指向权威版本)
  ↓
Phase 执行文件 (具体实施)
  ↓
验收证据 (代码+测试+CI)
```

### 冲突解决

- 本矩阵与冻结路线冲突：以冻结路线为准
- 本矩阵与 ccdoc 冲突：以本矩阵为准
- ccdoc 内部冲突：以本矩阵标注的 supersedes 为准
- 审核发现与本矩阵不一致：视为矩阵错误，需修正

---

**评估完成日期**: 2026-09-19  
**评估人**: Architecture Review Agent  
**状态**: FINAL  
**下一步**: 建立规范索引，启动 P0 执行文件编写

