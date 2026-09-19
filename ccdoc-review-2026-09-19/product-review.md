# ccdoc 专项审核：产品目标、中文网文质量、读者证据与外部研究

审核日期：2026-09-19。审核对象是规划文本及其中的示例，不是已经上线的 V2。重点阅读 00、01、02、04、05、06、07、08、09、10、11、README，并交叉核对 12 的三部分及 13、17、21 中相关章节。未修改 ccdoc，未调用付费模型，未发布作品。本文供总审核报告合并使用。

## 结论

这套资料认识到了“工程能力不等于作品结果”，也有 Genre 约束、Canon、可恢复工作流、真人阅读、修订净收益等正确方向。但目前最充分设计的是“生成、检查和存储章节”，最薄弱的部分是“独特的故事为何值得持续阅读，以及怎样证明自动化真的改善了作品”。因此它可以作为设计候选材料，不能按“最终可执行版”的字样直接视为自动产出起点爆款的已验证路线。

最终目标可以保留为产品愿景；阶段承诺必须是可测量的能力。工程稳定、作品吸引力、真实市场成效需要三份独立证据。30 章没有重大矛盾证明的是一个有限范围的生产结果，不自动证明百万字叙事能力、付费意愿或爆款概率。

用户已经冻结的 P0→P14 顺序继续有效。本文提出的整改不要求提前实现 Reference Intelligence、Corpus Learning 或复杂市场反馈；P8/P9 可以开展简单人工正文评阅，P11 才建设正式校准/学习系统，P13 才进行实际市场反馈闭环。

## 应保留的设计意图

- 05 明确不把未校准模型评分称为商业真值，也强调真实 Provider 验证、Canon 唯一入口、Draft 非 Canon。这些原则应升级成跨文档的不可绕过约束，而不是被后续例子覆盖。[证据等级原则](/Users/angyang/Documents/AI/ANovelOS/ccdoc/05_V1_LESSONS_LEARNED.md:228)
- 06 提出在 30 章阶段进行真人阅读、失败后暂停扩张，优于仅以测试数或生成字数验收。[人工验收](/Users/angyang/Documents/AI/ANovelOS/ccdoc/06_MILESTONE_DEFINITIONS.md:347)
- 12 暂缓 Genre Blending、复杂图记忆和多智能体争论，体现范围控制。需要区分“暂不做混合题材产品”与“基础领域模型不能表达独立题材维度”。[暂缓项](/Users/angyang/Documents/AI/ANovelOS/ccdoc/12_ARCHITECTURE_DECISION_RECORD_PART3.md:501)
- 参考材料只用于提炼机制、规划，避免 Writer 读取连续参考原文，是值得保留的隔离意图。[Reference 边界](/Users/angyang/Documents/AI/ANovelOS/ccdoc/05_V1_LESSONS_LEARNED.md:414)

## 十二项重点发现

### PM-01｜高：现行路线没有明确权威关系；后稿也没有退出旧项目战略重构路线

**性质：跨资料冲突，不是把旧稿误判为现行。** README 仍只索引 00—07，宣称完整资料共 8 份；11 自称 Final、可执行，仍写“战略性重构，不推倒重来”，因此问题不能只用 README 陈旧解释。12 的“最终决策”仍以 Genre→Genesis→生产重构的 M1/M2/M3 编排，与用户冻结的 Repository→Narrative→Canon→Genre→Contract→Context→Single Chapter→Quality→认证顺序不同。[README 索引](/Users/angyang/Documents/AI/ANovelOS/ccdoc/README.md:12)；[11 核心决策](/Users/angyang/Documents/AI/ANovelOS/ccdoc/11_FINAL_EXECUTABLE_GUIDE.md:12)；[12 Genre 决策](/Users/angyang/Documents/AI/ANovelOS/ccdoc/12_ARCHITECTURE_DECISION_RECORD_PART1.md:90)

**影响：** 自动实施代理可能先改 V1 的 Genre 和 Genesis，再补事务与恢复；也可能执行 07 中对旧仓库打标签和推送的命令。这些是文档内容，不是本次用户授权执行的动作。

**最小整改：** 在 P0 规范索引中登记每份资料的角色、权威级别、适用版本和 supersedes。ccdoc 的旧 M1/M2/M3 统一映射到冻结 P0—P14，并标明只保留建议还是成为规范。复用率与工期先作为假设，不能据此替换已冻结 greenfield 路线。

**验收：** 同一任务在 README、ADR、执行清单、CI、机器 backlog 中只映射到一个现行阶段；历史命令不会被当作待执行任务。

### PM-02｜高：Genre 从字符串升级成配置对象，但仍把“都市/玄幻”硬编码成两套模板

**性质：可定位的领域约束缺陷。** urban 允许重生、系统、预知，却禁止超自然力量；xuanhuan 禁止市场经济、商业竞争等整类机制。12 又明确暂不做层次与混合规则。只实现两个 Anchor Genre 是正确范围控制，但这不等于可以把平台大类、世界现实程度、题材内容、叙事机制合成一个互斥枚举。[都市规则](/Users/angyang/Documents/AI/ANovelOS/ccdoc/01_GENRE_SYSTEM_ARCHITECTURE_DESIGN.md:120)；[玄幻规则](/Users/angyang/Documents/AI/ANovelOS/ccdoc/01_GENRE_SYSTEM_ARCHITECTURE_DESIGN.md:159)；[最终决策](/Users/angyang/Documents/AI/ANovelOS/ccdoc/12_ARCHITECTURE_DECISION_RECORD_PART1.md:110)

**影响：** `urban.business.realistic` 可能被默认注入重生/系统；东方玄幻中的商会、拍卖、资源交换可能因“商业”被错误拦截。同一问题从 V1 的“玄幻 Schema 通用化”，转为 V2 的“都市财富升级模板通用化”。11 的“都市不生成修炼、玄幻不生成商业”依然延续这一验收歧义。[11 验收](/Users/angyang/Documents/AI/ANovelOS/ccdoc/11_FINAL_EXECUTABLE_GUIDE.md:1372)

**最小整改：** P3 只实现两个精确 Anchor ID，但从一开始把世界规律、时代/科技、超自然许可、主冲突、成长维度分别声明；允许合规例外必须有明确项目规则。参考作品检测只提出建议，用户/已冻结 GenreProfile 才决定生产约束。都市写实包应默认不带重生和系统；玄幻包应禁止未经许可的现代制度/物件，而不是禁止一切经济互动。

**验收：** 至少包含六类语义对照：写实都市确实施法、都市谈论游戏修炼、玄幻商会交易、玄幻突然调用现代券商、明确许可的重生设定、未许可的系统奖励。测试应判定文本中的事实作用，不能只检查关键词出现。

### PM-03｜高：三名读者的意向评分被包装成“留存度”，不足以支撑商业 Go

**性质：验收设计不足，非否定小样本的形成性价值。** 06 用 3 名真实读者，要求愿继续读 >60%、愿追更 >50%，并把“前十章平均分 >6/10”称为留存度；11 继续采用这些阈值。[样本与阈值](/Users/angyang/Documents/AI/ANovelOS/ccdoc/06_MILESTONE_DEFINITIONS.md:349)；[后稿复用](/Users/angyang/Documents/AI/ANovelOS/ccdoc/11_FINAL_EXECUTABLE_GUIDE.md:1417)

**反例：** 三人中两人同意就是 66.7%，两个比例门槛都通过。即使理想化假设为独立随机样本，2/3 的 Wilson 95% 区间约 20.8%—93.9%；真实便利样本还存在选择偏差。这个区间仅说明不确定性，不能把它解释为实际平台读者的置信区间。

**影响：** 愿意追更的回答、编辑评分、实际续读、付费转化混在一起。系统可能以“熟悉团队的三个人觉得还行”获得商业扩张资格。

**最小整改：** P8/P9 的三人阅读定义为人工试读/缺陷发现，保留其低成本价值；将“留存度”改为对应的问卷指标。正式晋级实验预先声明目标读者筛选、对照作品/系统、盲法、单位是书还是章节、随机化、弃读记录、独立样本数、置信区间、排除规则和重复试验方式。不能把同一本书的多个章节当成多个独立作品样本。

**验收：** 工程认证和人工可读性验收分别出具报告；报告不得把 3 人意向投票表述为起点市场留存/付费率。P11 再用独立留出集建立校准，P13 才接实际市场行为。

### PM-04｜阻断自动决策：后续 QA 重新引入“评分即发布/部署”，违背已声明证据边界

**性质：跨规范矛盾及可执行示例反例。** 05 规定 E2 不能 Gate、未校准模型评分不参与生产决策；17 却把综合分 A 级直接发布、B 级小修或直接发布。17 的 A/B 分析注释称“显著性”，实际只是算均值涨幅，超过 5% 推荐 deploy。[证据边界](/Users/angyang/Documents/AI/ANovelOS/ccdoc/05_V1_LESSONS_LEARNED.md:253)；[评分发布](/Users/angyang/Documents/AI/ANovelOS/ccdoc/17_QUALITY_ASSURANCE_FRAMEWORK.md:963)；[A/B 部署](/Users/angyang/Documents/AI/ANovelOS/ccdoc/17_QUALITY_ASSURANCE_FRAMEWORK.md:823)

**已复现：** 从 Markdown Python 代码块提取原样 `ABTestManager`，对照和候选各仅 1 条评分，75 对 81，返回 improvement=8.0、recommendation=deploy。它没有最小样本数、区间、回归维度或独立确认集。详见 product-probes.py 与 product-probe-results.json。此反例证明设计示例会误晋级；不表示运行中的 V2 已发生部署。

**最小整改：** 总分只用于诊断/排序；发布、Canon 提交、策略晋级应是分离的命令。强制硬门禁不能被均值抵消。Promotion 必须引用校准版本、实验协议、未污染留出集与回归报告。早期默认人工决定候选，不建立自动“分高就发布”路径。

**验收：** 单样本、缺失评分、缺失对照、无校准、任一硬门禁失败的候选均不能获得发布或部署许可。

### PM-05｜高：最终“爆款”目标没有可执行产品定义，且质量权重会偏离目标

**性质：目标分解与指标设计缺口。** 17 将读者吸引力权重设为 10%，题材符合、文本质量、逻辑、角色合计 90%；按线性权重理解，其余全满分、读者吸引力 0 分仍可达到 A 级 90 分。这里是对权重规范的算术反例，不声称已执行某个真实聚合器。[权重](/Users/angyang/Documents/AI/ANovelOS/ccdoc/17_QUALITY_ASSURANCE_FRAMEWORK.md:31)；[A级](/Users/angyang/Documents/AI/ANovelOS/ccdoc/17_QUALITY_ASSURANCE_FRAMEWORK.md:41)

**影响：** 项目容易优化“没有错且像网文”，忽略“读者愿意为什么付出注意力”。“爆款”本身尚未绑定题材队列、时间窗、曝光条件、阅读基数、收入成本与基准分位，无法形成可以证伪的最终目标。

**最小整改：** 不用一个总分同时替代正确性与吸引力。建立三条独立轴：①生产可靠性；②正文的目标读者偏好与连续追读价值；③有真实曝光基数时的市场表现。P4 的契约至少记录读者承诺、当章不可替代的状态变化、代价、对抗、信息变化、兑现与新问题；不能只写长度、钩子、爽点数量。P13 再定义真实起点发布条件下的漏斗与目标队列，目标值待真实基线建立后冻结。

**验收：** 一篇零矛盾但无冲突变化的正文可以通过技术检查，但不得被报告为作品质量优秀；市场报告必须区分曝光→开读→有效阅读→次日/更新后续读→付费阅读等不同分母，不把总点击数当作品因果效果。

### PM-06｜高：固定套路是可选配方，却被写成默认跨书生产规则

**性质：可定位的产品同质化风险。** 都市模板要求第 1 章获得金手指、第 2 章打脸、每章至少一个小爽点、前 30 章至少 2—3 个重要女性角色；玄幻模板要求每章至少一次战斗/机遇、每 3 章小突破、前三章废材被羞辱—打脸。这些可能适合某类特定选题，但不构成所有中文网文的质量公理。[都市配方](/Users/angyang/Documents/AI/ANovelOS/ccdoc/04_GENRE_SPECIFIC_PROMPT_TEMPLATES.md:154)；[玄幻配方](/Users/angyang/Documents/AI/ANovelOS/ccdoc/04_GENRE_SPECIFIC_PROMPT_TEMPLATES.md:549)

**影响：** 同一工厂生成多本书时，人物功能、开局冲突、回报节拍趋同；把“原创”理解成替换名字、地点和力量体系仍不够。作品可能形式合格，读者却很快识别套路，缺乏持续好奇。

**最小整改：** 将这些模板降为版本化可选策略，不作为 Genre 宪法。每本书在 P4 就声明独特的核心矛盾、主角主动选择及其代价、人物关系的不可替代性、长期问题、承诺兑现方式；增长可以是财富、能力、关系、认知或地位的不同组合。节奏规则应有情境与窗口，而不是每章机械完成同一事件。

**验收：** 对两个 Anchor 各准备不同 premise 的少量固定测试书，人工盲评检查“遮去名字后是否仍像同一本书”；记录重复冲突/解决机制，不用单纯词汇相似率替代情节同质化判断。

### PM-07｜高：三稿制并未证明全自动净收益，最后一稿直接返回也不等于最佳稿

**性质：源码示例缺口与来源被扩展解释。** 11 的 A→B→C 代码在 C 生成后直接返回，没有对 C 重跑完整检查，也没有把三稿作为候选比较；注释写“返回最佳版本”，实现仅返回最后版本。B/C prompt 主要携带初稿和问题，没有完整重申冻结契约/Genre/Canon 上下文。[实现](/Users/angyang/Documents/AI/ANovelOS/ccdoc/11_FINAL_EXECUTABLE_GUIDE.md:503)；[B/C prompt](/Users/angyang/Documents/AI/ANovelOS/ccdoc/11_FINAL_EXECUTABLE_GUIDE.md:565)

**外部核验：** 引用的 HZ-KMNO 仓库当前官方 README 的 A/B/C 主流程明确插入 user feedback 与 user approval。它证明存在这种有人参与的写作工作流，并不证明把这些节点删除后，全自动修订可提高本项目 15—25%。[官方流程](https://github.com/HZ-KMNO/web-novel-writing-guidance-skill#-core-workflow)

**最小整改：** 用户冻结的 P7 先完成有证据的 Patch Repair：限定修改范围，保留原稿，对修补后全文重新 Extract/验证，修复失败回滚或 Block；A/B/C 作为可选实验策略。所有候选保留相同基线与完整版本谱系，使用“最终被接受的最佳可用候选”语义。

**验收：** 改稿引入新 Canon 错误、删掉已兑现情节、改变人设/题材，必须被检出；修订净收益用成对盲评和缺陷回归分别证明；原稿、修补、整章重写纳入同预算对照。

### PM-08｜高：PPL 与离散情感状态只能先作为诊断，不能承担中文作品硬门禁

**性质：方法与使用权限不匹配。** 09 使用英文 GPT-2 的 PPL，在 20—40 间直接判为“有 AI 味”，并硬给 confidence=0.8；11 将 Perplexity 纳入 M2。GPT-2 模型卡明确是英语预训练模型，不能据此确认中文网文的流畅度或“AI 味”阈值。[示例阈值](/Users/angyang/Documents/AI/ANovelOS/ccdoc/09_PREARCHITECTURE_VS_INDUSTRY_DEEP_DIVE.md:498)；[纳入实施](/Users/angyang/Documents/AI/ANovelOS/ccdoc/11_FINAL_EXECUTABLE_GUIDE.md:1108)；[模型卡](https://huggingface.co/openai-community/gpt2)

11 的情感检查用有限状态转换表，happy→sad 需落入少数重大事件类型；首次出现或情感未变直接有效。虽然示例写有“简化版”和事件解释补偿，但该机制还不足以表达伪装、混合情感、迟发反应、视角误解与个人价值差异。[情感转换](/Users/angyang/Documents/AI/ANovelOS/ccdoc/11_FINAL_EXECUTABLE_GUIDE.md:919)

**影响：** 为减少“违规”，系统可能删去文学上的惊喜、情绪张力、反讽与复杂人物；机械一致不等于可信。追求低 PPL 也可能奖励平庸重复表达。

**最小整改：** 在 P7 保留为标记不确定性的诊断候选；P11 使用中文、目标题材、有人类意见的独立语料验证效用、误报和分布变化。人物诊断应解释“角色已知信息＋目标＋触发事件＋代价＋行为”，不能靠心情标签合法化整个心理过程。

**验收：** 以否定句、讽刺、引用、梦境、表里不一、悲喜交加、可信突发事件为对照；没有校准证据时不允许 these proxies 阻断或自动重写正文。

### PM-09｜高：论文存在不等于本项目已获得其收益，量化 ROI 缺乏可迁移证据

**性质：实证来源核查与推断越界。** 10/11 将 SCORE 的 23.6%、41.8%、89.7% 直接转为工程收益和 M2 阈值，并合成为本项目综合质量提升 25—35%；12 又写为 30—40%。不同指标、不同基线和没有统计定义的“单章质量”不能直接组合成一个综合提升率。[11 量化收益](/Users/angyang/Documents/AI/ANovelOS/ccdoc/11_FINAL_EXECUTABLE_GUIDE.md:1213)；[12 另一总收益](/Users/angyang/Documents/AI/ANovelOS/ccdoc/12_ARCHITECTURE_DECISION_RECORD_PART3.md:543)

**外部核验结果：** SCORE v1 摘要确实出现该组数字，不能把引用本身定性为编造。该论文目前列出的最新版本为 v6；v6 摘要不再出现 23.6% 这组承诺，Table 1 的 coherence 表述为多个模型的不同变化量，研究重点包括故事评估与检索 QA。它支持“值得试验追踪和检索”，并不证明中文双题材 30 章写作的同等增益，更不证明付费效果。[v1](https://arxiv.org/html/2503.23512v1)；[v6](https://arxiv.org/html/2503.23512v6)

10 的“行业采用率”90%、85%、75%等没有可复核的项目清单、分母、采纳判定和 commit 快照；11“所有项目均没有类似约束系统”“独创”也超过了有限样本调研能证明的范围。[行业比例](/Users/angyang/Documents/AI/ANovelOS/ccdoc/10_ULTIMATE_COMPETITIVE_LANDSCAPE_ANALYSIS.md:1056)；[独创断言](/Users/angyang/Documents/AI/ANovelOS/ccdoc/11_FINAL_EXECUTABLE_GUIDE.md:47)

**最小整改：** 每项外部主张记录来源版本、任务、语言、样本、基线、评价者、效应量与适用限制。把“必须做且提高 X%”改为“候选方法和待验证假设”。先在冻结的 1/10/30 章路线内做最小增量实验，不因论文/仓库存在而新增基础设施。

**验收：** 任何本项目收益声明必须能指向本项目实验；外部研究结论始终带来源和边界。竞品“未观察到”不得写成“绝对没有”，研究代码与商业成熟产品不得以同一勾选列比较。

### PM-10｜高：成本目标内部矛盾，且未形成“每个被接受章节”的完整成本模型

**性质：直接算术错误、同一文档冲突、预算遗漏。** 11:685 将 $0.020/章说成低于 $0.01；同一 Final 文档的 M3 有 $0.30/30章与 $0.75/30章两套标准。A/B/C 的 70%/20%/10% 分布未提供观测来源；按其所列累计单价加权为 $0.0192，仅能说明例算约为 $0.020，不能证明达到该成本。[价格描述](/Users/angyang/Documents/AI/ANovelOS/ccdoc/11_FINAL_EXECUTABLE_GUIDE.md:673)；[0.30门槛](/Users/angyang/Documents/AI/ANovelOS/ccdoc/11_FINAL_EXECUTABLE_GUIDE.md:1144)；[0.75门槛](/Users/angyang/Documents/AI/ANovelOS/ccdoc/11_FINAL_EXECUTABLE_GUIDE.md:1423)

**影响：** 强行把成本压到未经验证的 $0.025/章，可能鼓励缩短上下文、跳过检查或采用明显不足的模型；只记录正文生成调用，还会漏掉规划、抽取、Judge、重试、被拒稿、检索、人工与基础设施成本。

**最小整改：** P5 Model Gateway 起就记录冻结价格版本、输入/缓存/输出 token、调用角色、重试和未知计费结果。P8/P9 以“接受正文每千中文字/每章/每本”的实际分布报账，同时报告失败尝试和人工时长；目标预算区间基于真实测量再冻结。商业 ROI 后续需要收入/读者价值与投入，不能用两个不同维度的百分比直接得出“极高”。

**验收：** 同一 run 的所有调用对账合计等于 ledger；P50/P95 和失败预算可查；成本优化不能降低强制门禁覆盖，低成本方案必须与较强基线同协议盲评。

### PM-11｜高：Reference 的原则存在，但原创差异和语料隔离没有形成产品验证协议

**性质：从声明到验收的缺口。** 05 已说明抽象 EvidencePack、Writer 不读原文，但 04 使用具体名作的经典角色关系/桥段来构造配方，10 的优秀案例方案拟让模型按相似模式写第 1 章。12 后来暂缓 Few-shot，这一点应承认，不能说后稿已经要求默认复制正文；但历史材料缺少清晰的停用标记与何时安全启用的定义。[Reference 原则](/Users/angyang/Documents/AI/ANovelOS/ccdoc/05_V1_LESSONS_LEARNED.md:414)；[具体桥段](/Users/angyang/Documents/AI/ANovelOS/ccdoc/04_GENRE_SPECIFIC_PROMPT_TEMPLATES.md:569)；[暂缓 Few-shot](/Users/angyang/Documents/AI/ANovelOS/ccdoc/12_ARCHITECTURE_DECISION_RECORD_PART3.md:385)

**影响：** 不含连续参考原文依然可能生成高相似情节/人物组合；学习集、修订样本和评测金样混用，也会使“质量提高”只是记住评测偏好。起点爆款代表作可以帮助理解读者机制，却不能成为单一配方的效果证明。

**最小整改：** 当前只保留接口及 provenance，不提前建设完整 Reference 产品。P10 对每本新书声明不同于参考的主角选择、核心因果、关系动力、舞台约束和承诺；记录源材料许可/来源状态、允许用途、转换过程、可能的高相似片段及人工处置。P11 以作品级切分训练/开发/测试和来源，保留未参与改稿的独立测试书。

**验收：** 换名改写与近似桥段组合的对照不能被“无原文输入”自动判定为原创合格；相似度低也不能自动判定无风险。本报告不作版权或平台准入法律结论。

### PM-12｜高：研究启发被一口气提升为核心工程范围，工作量尚未可执行

**性质：任务范围与估算依据不足。** 11 说新增五项技术“必须”实施，M2 同时加入 19 个 Checker、三稿制、Temporal RAG、情感一致性、Token 熵与 Perplexity。12 Part3 的 M1 表逐项合计约 9 人周，却排在 6 周；M2 表合计约 12 人周，却排在 8 周，成本追踪还未单列。11 的估算口径假设 1 名全职开发者。可以通过并行资源或重叠任务解释，但表中没有相应安排。[M2 扩张](/Users/angyang/Documents/AI/ANovelOS/ccdoc/11_FINAL_EXECUTABLE_GUIDE.md:1093)；[任务工期](/Users/angyang/Documents/AI/ANovelOS/ccdoc/12_ARCHITECTURE_DECISION_RECORD_PART3.md:515)；[单人假设](/Users/angyang/Documents/AI/ANovelOS/ccdoc/11_FINAL_EXECUTABLE_GUIDE.md:1183)

**影响：** 为了追齐论文功能清单，延迟单章可靠生产和真正的正文阅读；一旦工期超出，又容易降低验收质量，重演 V1 的功能增长问题。

**最小整改：** 仍按冻结关键链：Canon/Contract/Context/Workflow/Q0—Q3/Patch Repair 优先。必要的事实时间语义属于 Narrative/Canon 正确性，应保留；语义检索可在 Context 内按最小必要范围实现；Token 熵、PPL、复杂情感自动机、整章三稿制属于待证明收益的可选实验，不默认成为 P0—P9 阻断项。区分功能底座与高级实现，不把名字相似就当作同一任务。

**验收：** 每个新增任务有对应的 V1 回归或用户故事、依赖、产物、验收和预算；新方法必须通过基线对照说明收益，不能仅以“论文采用”“行业趋势”占用关键链。

## 与最终目标对齐的最小验收层次

以下是对冻结路线的验收补充，不是新的实施路线，也不要求重新开始总体研究。

| 已冻结阶段 | 应证明什么 | 不能据此声称什么 | 最小新增证据 |
|---|---|---|---|
| P0 | 唯一规范与可执行治理 | 文档完成即架构成立 | 权威索引、冲突消解、任务映射 |
| P1—P7 | 一章完整、受约束、可恢复地生产；错误稿能拦截/修复 | 一章分高即有商业潜力 | 固定场景、全文证据、故障恢复、正文人工阅读 |
| P8 双 Genre 10章 | 同内核服务两个 Anchor，前文承诺继续推进 | 支持全部都市/玄幻或全部网文 | 两个不同类型的冻结书配置；自然违规与注入违规分开统计 |
| P9 30章 | 两个 Anchor 的长期一致性、阶段兑现与可读性 | 能写百万字或具有真实市场留存 | 全文完整阅读、弃读点、因果/关系/兑现检查、真实总成本 |
| P10 | 合法取得的多源资料能支持新书，而不直接复制与污染 Writer | 抽象过即当然原创 | 来源权限、版本、用途、情节差异与相似问题处置 |
| P11 | 自动评价/修订与目标读者判断有独立可复核的联系 | 相关性即因果提升或付费概率 | 作品级留出、成对盲评、校准及误差、修订退化率 |
| P12 | 百章连续稳定，未靠无上限人工介入维持 | 百章成立即可扩至百万字 | 多卷承诺、人物弧线、状态规模、人工介入密度、失败分布 |
| P13 | 在记录清楚的曝光条件下有真实读者与付费表现 | 流量差异全部由文本质量导致 | 分母、队列、渠道、版本、付费与流失行为、统计不确定性 |
| P14 | 300+章/百万字的长期演化仍能兑现核心承诺 | 长就是好或稳定就能爆款 | 长期重复度、世界膨胀、主线闭合、兑现债务与读者长期变化 |

一个重要的自动化指标是“每个被接受章节需要多少人工介入分钟、改写比例与异常干预”，以及这些数值随章节变长是否上升。它衡量系统是否在向自动生产前进。人工早期参与评估不等于最终产品必须逐章人工创作；相反，不记录人工贡献，会把人的劳动错误归因给模型架构。

## 外部来源有限核查台账

查询日期 2026-09-19；只把可访问的论文原站和项目官方仓库当来源。没有审计这些项目全部源代码，也没有复现实验，以下“已核实”只指明确写出的内容存在。

| 来源 | 核实内容 | 对 ccdoc 的判断与边界 |
|---|---|---|
| [FACTTRACK](https://arxiv.org/abs/2407.16347) | 时间有效区间与结构化故事大纲矛盾检测确实存在 | 支持时间语义方法候选；不证明百万字正文与商业成效 |
| [SCORE v1](https://arxiv.org/html/2503.23512v1) / [v6](https://arxiv.org/html/2503.23512v6) | v1摘要有被引用数字；v6叙述与表格须分开读取 | 不是凭空不存在的论文；禁止外推为本项目质量增益和 ROI |
| [ConStory-Bench](https://aclanthology.org/2026.findings-acl.410/) | 2,000 prompts、五类十九子类、Checker及错误分布描述可核实 | 可以借鉴测试分类；不是十九个简单函数即可完整实现相同检测能力 |
| [DHO](https://arxiv.org/abs/2412.13575) | 动态分层规划与记忆增强论文存在 | 动态计划应作为受版本与 Canon 约束的候选能力 |
| [ConWriter](https://arxiv.org/abs/2608.05169) | 状态转换约束叙事生成研究存在 | 可支持方法讨论，不能反向认证 ANovel 的事务实现正确 |
| [MAGNET/ATLAS](https://arxiv.org/abs/2607.00918) | 角色代理、共享世界状态、图式检测研究存在，提交年份2026 | 不能由研究存在推导本项目必须提前实现多Agent或图数据库 |
| [Re3](https://arxiv.org/abs/2210.06774) | 递归重提示与修订论文存在 | 自己的模型、语言、长度与成本仍需复测 |
| [Heterogeneous Recursive Planning](https://arxiv.org/abs/2503.08275) | 异构递归规划论文存在 | 可作后续计划能力候选，不是必要底座的自动证明 |
| [HZ-KMNO 官方仓库](https://github.com/HZ-KMNO/web-novel-writing-guidance-skill) | A/B/C工作流包含反馈与人工认可 | 不能直接作为全自动三稿净收益证据 |
| [Novel-OS 官方仓库](https://github.com/mrigankad/Novel-OS) | 仓库及持久状态/确定性连续性/五角色定位可访问 | 本次未验证 ccdoc 所称 SQLite snapshots 的具体代码与提交，不作为已核实实现 |
| [Zo-autonovel 官方仓库](https://github.com/Noesis-Boss/Zo-autonovel) | 五层结构、机械评估、修订与导出定位可访问 | 功能声明与市场效果独立 |
| [GPT-2 模型卡](https://huggingface.co/openai-community/gpt2) | 主要为英语预训练语言模型 | 不能未经中文校准使用固定PPL区间充当AI味硬门禁 |

本次打开起点榜单页未成功，因此没有据此给出当前榜单、起点平台规则、平均订阅收入或某题材当前热度的结论。报告不把无法访问当成不存在。没有调用 API 测成本，没有推断平台允许自动发布；将来发布阶段应单独核验当时的官方规则与账户授权。

## 交付与复现范围

- `product-probes.py`：从原文 Python fence 提取 A/B 例子，执行无网络、无模型的单样本实验，同时复算读者样本、成本和工作量。
- `product-probe-results.json`：包含源文档 SHA-256、输入条件、输出与统计假设说明。
- 本文所有产品缺口是对规划的审核；仅明确标注的 A/B 例子经过代码执行，其余为文本矛盾、算术分析或设计建议。没有把示例缺陷自动定性为已上线产品漏洞。
