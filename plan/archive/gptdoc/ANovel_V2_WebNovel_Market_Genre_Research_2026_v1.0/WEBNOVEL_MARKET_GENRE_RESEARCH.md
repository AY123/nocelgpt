# ANovel V2 China Web-Novel Market, Genre Taxonomy & Hit-Pattern Research 2026

> **中文名**：ANovel V2 中国商业网文市场、分类体系与爆款机制深度研究 2026  
> **Document ID**：RES-0003  
> **Version**：1.0.0  
> **Status**：BASELINE / RESEARCH INPUT  
> **Authority**：RESEARCH-EVIDENCE  
> **Depends-On**：`PROJECT_CONSTITUTION.md`, `V1_FORENSIC_LESSONS.md`, `REFERENCE_ARCHITECTURE_STUDY.md`  
> **Research Cutoff**：2026-09-18  
> **Primary Platforms**：起点中文网 / 阅文生态；辅助参考中国网络文学行业公开资料  
> **Primary Use**：为 `GENRE_INTELLIGENCE_SPEC.md`、GenrePack、MarketTrendSnapshot、Corpus Intelligence、Reference Intelligence 与商业质量体系提供研究输入。  
> **Important**：本文描述“市场证据与设计假设”，不是永久 Genre 真理。市场数据必须版本化，不得硬编码为核心 Domain 规则。

---

# 0. Executive Conclusion

ANovel V2 在架构第一天就必须考虑网文分类，但不能把“平台分类目录”直接当作内部 Genre Architecture。

最关键的结论是：

> **平台分类回答“作品放在哪个书架”；Genre Intelligence 回答“作品为什么以这种方式运转”。**

一部真实商业网文通常同时由多个正交维度决定：

```text
Platform Category
+
Genre Family
+
Subgenre
+
Reality Model
+
World Model
+
Narrative Engine
+
Progression Engine
+
Conflict Engine
+
Reader Promise
+
Payoff Pattern
+
Trope / Mechanic
+
Tone
+
Cast Architecture
+
Domain Knowledge
+
Fusion Policy
```

因此 V2 必须采用：

> **Multi-axis Genre Ontology + Versioned GenrePack**

而不是：

```yaml
genre: 都市
```

这种单字段模型。

---

# 1. Market Snapshot: 2025–2026

## 1.1 Industry Scale

《2025中国网络文学蓝皮书》公开数据显示，截至 2025 年底：

- 网络文学作品总量超过 3300 万部；
- 注册作者超过 3500 万；
- 读者规模约 5.25 亿；
- 2025 年网络文学营收规模约 490 亿元；
- 现实、科幻、历史、幻想等大类均出现明显“提质”趋势；
- 类型创作正从公共模板、套路复制向个人化、风格化和类型融合演进。

对 ANovel V2 的含义：

> 市场不是“缺能生成文本的 AI”，而是缺能稳定生成**有类型辨识度、长篇结构和原创差异**的系统。

---

## 1.2 Qidian Recommendation Logic Changed

2025 年 7 月，起点新书推荐从长期使用的多轮 PK 模式全面转向“流量包”模式。

公开研究指出：

- 签约作品稳定日更约 4000 字；
- 约 6 万字进入首轮流量包；
- 上架前存在 21–42 天培育期；
- 放量更关注追更率、留存率、转化率等；
- 流量包 1–2 天刷新；
- 机制更有利于慢热文、创新文获得持续试错机会；
- 上架后仍回归订阅、追订、月票等付费用户信号。

### V2 Implication

V2 不能只优化：

```text
title
简介
前三章
第一爽点
```

还必须独立建模：

```text
Early Conversion
Long-term Retention
Paid Continuation
Narrative Durability
IP Potential
```

即：

> **Opening Quality ≠ Long-Sell Quality**

---

# 2. Evidence Hierarchy for Market Research

V2 必须明确市场证据等级。

## M0 — Platform Machine Facts

例如起点官方作品页 / 荣誉页：

- 分类；
- 字数；
- VIP；
- 十万均订徽章；
- 首订过万；
- 月票榜名次；
- 荣誉时间。

可以作为较强事实。

## M1 — Industry Official / Institutional Reports

例如：

- 中国网络文学蓝皮书；
- 中国作家网行业综述；
- 阅文公开行业资料。

可用于判断趋势。

## M2 — Author Interview / Professional Criticism

可以解释：

- 创作机制；
- 读者审美变化；
- 类型突破。

属于解释性证据。

## M3 — Reader Booklists / Community Opinion

适合发现：

- reader vocabulary；
- trope names；
- niche patterns；
- dissatisfaction。

但不能作为市场规模真值。

### Rule

GenrePack 不得把 M2/M3 直接升级成硬规则。

---

# 3. Current High-value Market Signals

公开起点荣誉数据为若干作品提供了强商业信号。

## 3.1 《没钱修什么仙？》

起点荣誉页显示：

- 2026-04-01 获得“十万均订”；
- 2026 年 6 月男频月票榜第 3；
- 2026 年 7 月第 5；
- 2026 年 8 月第 4。

其重要性不只是成绩，而是：

> **传统修仙母体 + 现代金融/消费/教育/阶层逻辑的深度融合。**

这不是简单“修仙 + 手机”。

它把：

```text
修炼资源
→ 金融产品

功力
→ 可借贷资本

宗门/学校
→ 教育与阶层系统

修仙竞争
→ 现代社会内卷
```

做成同一世界逻辑。

### V2 Lesson

真正优秀的 Genre Fusion 需要：

> **World Logic Fusion**

而不是关键词拼接。

---

## 3.2 《苟在初圣魔门当人材》

起点荣誉页显示：

- 2026-04-01 获得“十万均订”；
- 2025 年多月稳定位居男频月票榜高位。

作品公开分类为东方玄幻，核心机制包含：

- 多次人生重开；
- 魔门生存；
- 风险管理；
- 信息积累；
- 资源继承；
- 非传统“伟光正”主角路线。

### V2 Lesson

Mechanic（模拟/重开/轮回）不应该和 Genre 处于同一层。

正确表达：

```text
Primary Genre: Eastern Fantasy
Mechanic: Repeated-life Simulation
Tone: Dark Comedy
Progression: Accumulated Knowledge + Power
Narrative Engine: Risk / Survival / Iteration
```

---

## 3.3 《捞尸人》

起点荣誉页显示：

- 2026-04-01 获得“十万均订”；
- 2025 年到 2026 年 8 月长期高居男频月票榜，其中多月第一。

公开分类标记为“异术超能”，但行业与读者讨论更常强调：

- 民俗；
- 灵异；
- 悬疑；
- 人性；
- 地方文化；
- 群像和人物弧光。

### V2 Lesson

Platform Category 与 Narrative Identity 不完全等价。

内部应表达：

```text
Platform: 都市 / 异术超能
Reality: Contemporary + Supernatural
Narrative Engine: Mystery / Investigation / Folk Ritual
Cultural Domain: Chinese Folk Belief
Tone: Dark / Humanistic
Reader Promise: Strange Case + Human Nature + Revelation
```

---

## 3.4 《玄鉴仙族》

2026 年行业公开资料显示，作品达到十万均订量级，并成为新一代头部修仙案例。

核心突破不是“境界更复杂”，而是：

- 家族作为长期主体；
- 代际叙事；
- 群像；
- 高阶力量压迫下的现实主义求生；
- 个人死亡与家族持续成长同时成立。

### V2 Lesson

“主角”不一定是单个 Character。

ANovel Canon 必须允许：

```text
Protagonist Entity:
  person
  family
  faction
  institution
  ensemble
```

至少架构上不能把“单主角永生”写死。

---

## 3.5 《重生高考前99天》与都市重生

2026 年新晋白金相关公开资料指出：

- 柳岸花又明已有两部都市重生作品达到十万均订量级；
- 《重生高考前99天》长期位居都市分类前列。

其商业机制不只是“提前知道未来”，还包括：

- 社会经验差；
- 人情世故优势；
- 身份反差；
- 年代/校园真实感；
- 人际关系变化；
- 情感张力；
- 微观人生修正。

### V2 Lesson

`Rebirth` 是：

> Narrative Mechanic

不是 Genre。

正确表达：

```text
Genre: Urban
Subgenre: Daily / Youth / Era
Mechanic: Rebirth
Core Fantasy: Mature mind in younger identity
Progression: Social competence / relationship / career
```

---

## 3.6 《1979黄金时代》

起点荣誉页显示：

- 首订过万；
- 精品；
- 多月进入男频月票前十。

其代表：

```text
Urban
+
Era
+
Entertainment/Cultural Industry
+
Rebirth/Knowledge Advantage
```

### V2 Lesson

年代文必须拥有 `Period Constraint`。

不能只写：

```text
year: 1979
```

而应约束：

- 技术；
- 货币；
- 工资；
- 商品；
- 政策；
-机构；
- 城市空间；
- 流行文化；
- 社会习俗；
- 信息传播速度。

这直接影响 Canon 与 Validation。

---

# 4. 2025–2026 Macro Creative Trends

综合行业公开研究，可以得到几个值得进入 V2 Research Model、但不能硬编码成永久规律的趋势。

## T-01 Stable Genre Base + Controlled Innovation

类型叙事仍是网络文学最坚实基础。

但头部作品越来越不是“纯模板复制”，而是：

```text
成熟类型
+
新的世界规则
+
新的社会视角
+
新的叙事结构
```

### System Implication

V2 的创新不是随机“脑洞”。

应当是：

```text
Stable Reader Promise
+
Controlled Novelty
```

---

## T-02 Reality Penetrates Fantasy

近期修仙/玄幻头部作品明显增加：

- 阶层；
- 资源；
- 生存；
- 金钱；
- 组织；
- 社会结构；
- 现实困境。

### Important

这不等于玄幻要“写现实主义”。

而是：

> Fantasy World 需要拥有可相信的社会运行机制。

---

## T-03 Worldbuilding Must Generate Story

优秀世界观不只是 Wiki。

它必须持续产生：

- resource conflict；
- class conflict；
- faction conflict；
- moral dilemma；
- progression obstacle；
- unknown mysteries。

### V2

每个 World Rule SHOULD 声明：

```text
story_consequences
conflicts_generated
affected_entities
```

---

## T-04 Ensemble / Group Dynamics Rise

2025–2026 代表性讨论中，群像、家族、组织叙事的重要性上升。

### V2

不能只设计：

```text
Protagonist Arc
```

还需要：

```text
Ensemble Dynamics
Faction Arc
Family Arc
Relationship Network
```

---

## T-05 Anti-template and Authorial Voice

2024/2025 蓝皮书反复指出：

- 系统文泛化；
- 模板化；
- 人物扁平；
- 类型融合停留在标签拼接；

是质量问题。

头部创作则趋向：

- personal voice；
- unique aesthetic；
- more complex character；
- deeper reality observation。

### V2

Quality System 必须加入：

```text
Genericness Risk
Template Repetition
Voice Distinctiveness
Character Specificity
World Specificity
```

---

## T-06 Genre Fusion Becomes a Main Innovation Path

公开行业评论指出：

- 科技 + 都市；
- 科幻 + 玄幻；
- 科幻 + 末世；
- 修仙 + 现代社会机制；

等融合持续增长。

### V2

必须支持：

> Controlled Genre Composition

而不是：

```text
genre = "都市玄幻科幻"
```

---

# 5. Platform Taxonomy ≠ Internal Ontology

平台常见大类包括：

```text
玄幻
奇幻
武侠
仙侠
都市
现实
军事
历史
游戏
体育
科幻
诸天无限
悬疑/灵异相关
轻小说
...
```

但平台分类的主要目的：

```text
navigation
discovery
recommendation
catalog
```

ANovel 内部则要解决：

```text
generation
state
validation
planning
commercial promise
```

所以不能一一等同。

---

# 6. Recommended Multi-axis Genre Ontology

建议 V2 至少定义以下轴。

## A01 Platform

```yaml
platform: qidian
channel: male
platform_category: urban
platform_subcategory: urban_life
```

## A02 Genre Family

```text
urban
fantasy
xianxia
historical
sci_fi
mystery
...
```

## A03 Subgenre

例如：

```text
urban.business
urban.era
urban.entertainment
fantasy.eastern
fantasy.high_martial
xianxia.classical
xianxia.family
```

## A04 Reality Model

```text
realistic
heightened_realism
hidden_supernatural
open_supernatural
full_fantasy
science_speculative
```

## A05 Setting Model

```text
contemporary
era
campus
workplace
alternate_world
dynasty
future
multiverse
```

## A06 Narrative Engine

回答：

> “为什么还能继续写下一章？”

例如：

```text
entrepreneurship
investigation
survival
cultivation
faction_growth
family_growth
competition
exploration
dungeon_cycle
political_rise
career_growth
```

## A07 Progression Engine

回答：

> “主角/主体怎么变强？”

```text
wealth
status
career
company_scale
social_network
realm
skill
artifact
territory
faction_power
technology
knowledge
reputation
```

## A08 Conflict Engine

```text
market_competition
institutional_pressure
class_conflict
resource_competition
faction_conflict
survival_threat
mystery
relationship
war
ideology
```

## A09 Core Fantasy

读者代入的根本欲望。

例如：

```text
upward_mobility
second_chance
mastery
freedom
revenge
recognition
control
discovery
belonging
legacy
```

## A10 Reader Promise

比 Core Fantasy 更具体：

```text
watch_company_grow
watch_family_survive_generations
watch_protagonist_outsmart_elite
discover_hidden_truth
progress_from_mortal_to_immortal
```

## A11 Mechanic / Trope

这些不能和 Genre 混层：

```text
system
rebirth
transmigration
simulation
sign_in
hidden_master
family
ensemble
farming
lord
beast_taming
infinite_flow
```

## A12 Tone

```text
light
comedic
dark
tragic
warm
satirical
epic
suspenseful
```

## A13 Cast Model

```text
single_protagonist
dual_protagonist
ensemble
family
faction
multi_generation
```

## A14 Domain Pack

专业领域：

```text
business
finance
medicine
law
entertainment
esports
military
archaeology
AI
semiconductor
education
```

DomainPack 与 GenrePack 分离。

## A15 Fusion Policy

显式说明：

```text
primary
secondary
overlay
allowed interactions
forbidden interactions
world-law precedence
```

---

# 7. Urban Taxonomy for V2

都市不能只是一种 GenrePack。

建议至少研究以下族群。

---

## U01 Urban Realistic / Daily Life

核心：

```text
real social pressure
daily life
relationship
career
small wins
identity
```

Reader Promise：

> 在熟悉现实中获得更好的生活与身份。

Canon Extensions：

- Career
- Income
- Asset
- Residence
- Social Relation
- Reputation

---

## U02 Urban Rebirth / Second Chance

Mechanic：

```text
rebirth
future knowledge
mature cognition
```

必须区分：

```text
knowledge advantage
vs
supernatural prediction
```

未来信息发生改变后：

> 先知优势应衰减。

V2 应维护：

```text
FutureKnowledgeConfidence
TimelineDivergence
```

这是一个非常重要的新 Canon Extension 候选。

---

## U03 Era /年代

核心不是“旧年份”。

必须维护：

```text
period technology
policy
price
wage
institution
media
fashion
transport
communication
social norm
```

### Hard Rule

时代错误可以是 deterministic violation。

---

## U04 Business / Startup / Commerce

核心状态：

```text
Company
Equity
Cash
Revenue
Product
Market
Customer
Competitor
Contract
Financing
Team
Reputation
```

Reader Promise：

```text
upward mobility
strategic victory
wealth accumulation
industry expansion
```

最容易出现的 AI 错误：

- 金额失控；
- 公司规模瞬间跃迁；
- 商业常识错误；
- 股权前后冲突；
- 对手降智；
- 只写“商业成功”不写过程。

---

## U05 Entertainment / Culture Industry

Canon Extensions：

```text
Work
Role
Project
Production
Audience
BoxOffice
Rating
Agency
Contract
Reputation
Award
```

风险：

- 真实人物/作品版权；
- 行业流程悬浮；
- 作品“好”仅靠作者宣称。

---

## U06 Professional / Industry Fiction

例如：

```text
medical
law
finance
engineering
AI
semiconductor
civil_service
```

我建议这类主要实现为：

> **Urban GenrePack + DomainPack**

而不是无限制造顶级 Genre。

---

## U07 Urban Supernatural

需要明确：

```text
hidden_supernatural
open_supernatural
```

以及：

```text
why authorities do or do not know
how supernatural affects economy/law/society
```

否则很容易变成“现代背景的玄幻”。

---

# 8. Fantasy Taxonomy for V2

---

## X01 Eastern Fantasy

核心：

```text
power system
resource
faction
realm
world expansion
```

但 V2 必须避免把所有玄幻都退化成：

```text
修炼 → 打脸 → 突破 → 新地图
```

需明确 Narrative Engine 与 Progression Engine 是否真正变化。

---

## X02 High Martial

高武的关键不是：

> 玄幻人物穿现代衣服。

而是：

```text
extraordinary power
+
modern institutional society
```

核心 Canon：

- official rank；
- association；
- military；
- school；
- legal privilege；
- public threat；
- social treatment。

---

## X03 Otherworld /异世大陆

核心：

```text
different civilization
different institution
different culture
different world law
```

风险：

> 换地名但所有组织仍是中式宗门。

需要 Culture/Institution Model。

---

## X04 Dynasty / Faction Expansion

核心：

```text
territory
population
army
tax
food
faction
administration
diplomacy
```

它更像：

> State Progression

而不是 Character Progression。

---

## X05 Beast Taming

Progression 主体是：

```text
human
+
pet
+
team composition
+
evolution path
+
bloodline
```

适合作为 Genre Extension / Mechanic Pack。

---

## X06 Family / Clan

家族流不是普通 trope。

当家族成为持续主体时，需要：

```text
Family Canon
Generation
Bloodline
Succession
Marriage
Branch
Asset
Territory
Reputation
Ancestor Legacy
```

---

# 9. Xianxia Taxonomy for V2

仙侠必须和玄幻在 Domain 层区分。

---

## A01 Classical Xianxia

核心：

```text
dao
longevity
karma
mortality
cultivation
spiritual resource
sect
world order
```

Reader Promise 不只是“变强”。

还包括：

```text
transcend mortality
seek truth
freedom from lifespan
dao identity
```

---

## A02 Cultivation / Progression Xianxia

更强的：

```text
realm
resource
technique
bottleneck
breakthrough
```

需要 Power/Realm hard consistency。

---

## A03 Family Cultivation

结合：

```text
Family
+
Cultivation
+
Generation
+
Territory
+
Legacy
```

这是 V2 很值得作为第三批认证的高价值 Pack。

---

## A04 Realist / Harsh Cultivation

近期爆款显示较强趋势：

- 修炼资源稀缺；
- 社会阶层；
- 高阶修士压迫；
- 生存困境；
- 现实隐喻。

但这应被建模成：

```text
social_model
tone
conflict_engine
```

而不是固定为“仙侠必须黑暗”。

---

## A05 Modern / Cyber Cultivation

关键是：

> 两套世界逻辑必须融合。

例如：

```text
finance <-> cultivation resource
education <-> cultivation ranking
technology <-> supernatural system
```

如果只是：

```text
手机 + 灵气
```

不算真正 Fusion。

---

# 10. Genre vs Mechanic vs Domain: Mandatory Separation

V2 必须禁止如下平铺 taxonomy：

```text
玄幻
都市
重生
系统
家族
商战
群像
种田
```

因为它们不是同级。

正确：

```yaml
genre_family: urban
subgenre: business
mechanics:
  - rebirth
cast_model: ensemble
domain_packs:
  - finance
  - internet_startup
tone: realistic
```

另一例：

```yaml
genre_family: xianxia
subgenre: family_cultivation
mechanics:
  - artifact_legacy
cast_model: multi_generation
tone: dark_realist
```

---

# 11. Controlled Genre Fusion

V2 推荐：

```yaml
composition:
  primary:
    genre: xianxia
    weight: 0.65

  secondary:
    genre: urban_social_logic
    weight: 0.20

  overlays:
    - satire
    - campus

fusion_policy:
  world_law_owner: xianxia
  social_logic:
    may_borrow_from: contemporary_finance
```

权重不必直接参与生成数学计算。

它主要表达：

- dominance；
- precedence；
- allowable interaction。

---

# 12. What Makes a Commercial Hit? A Systems Model

不能把“爆款”写成固定公式。

但可以建立一个研究模型：

```text
Commercial Strength
≈
Premise Strength
×
Reader Promise Clarity
×
Early Conversion
×
Narrative Engine Durability
×
Progression Satisfaction
×
Character Attachment
×
World Specificity
×
Payoff Reliability
×
Long-Arc Expandability
×
Authorial Distinctiveness
```

这里使用乘法只是表达：

> 某些关键维度极弱会拖垮整体。

它不是市场预测公式。

---

# 13. Premise Strength

好 Premise 通常能让读者很快回答：

> “这本书最特别的东西是什么？”

比如：

```text
修仙世界被金融化
家族而不是个人成为修仙史主角
成熟公务员重回高中
传统民俗职业进入现代异术世界
```

V2 Genesis 应产生：

```text
One-sentence High Concept
```

但必须继续验证：

> 是否具有长期 Narrative Engine。

---

# 14. Reader Promise

Reader Promise 是 V2 必须正式建模的对象。

例如：

### Urban Business

> 看主角利用认知、能力与时代机会，从个人困境进入商业竞争并不断提升社会位置。

### Family Xianxia

> 看一个弱小家族在残酷修仙秩序中跨代生存、扩张并留下传承。

### Folk Mystery

> 看主角不断进入民俗诡事，在破局过程中揭示更大的世界真相和人性。

Promise 必须被：

```text
establish
reinforce
delay
payoff
renew
```

---

# 15. Narrative Engine

这是“能不能写 300 章”的关键。

## Urban Business Engine

```text
Opportunity
→ Build
→ Resistance
→ Resource Acquisition
→ Competitive Resolution
→ Scale Up
→ New Market
```

## Cultivation Engine

```text
Constraint
→ Resource
→ Practice/Experiment
→ Conflict
→ Breakthrough
→ New Capability
→ Higher-order Constraint
```

## Mystery Engine

```text
Anomaly
→ Investigation
→ Evidence
→ False Theory
→ Reveal
→ Consequence
→ Larger Mystery
```

## Family Engine

```text
Generation
→ Internal/External Pressure
→ Resource Allocation
→ Marriage/Alliance/Conflict
→ Succession
→ Growth/Loss
→ Next Generation
```

### V2 Rule

每个项目必须回答：

> Narrative Engine 在第 150 章以后为什么还不枯竭？

---

# 16. Progression Engine

Progression 不等于 Power Level。

### Urban

```text
money
career
company
network
reputation
social status
knowledge
```

### Xianxia

```text
realm
technique
resource
dao understanding
lifespan
artifact
```

### Dynasty

```text
territory
army
population
administration
influence
```

### Mystery

Progression 可能是：

```text
knowledge
access
trust
investigative capability
world truth
```

---

# 17. Payoff Architecture

爆款通常不只是“爽点多”。

而是：

```text
Expectation
→ Tension
→ Delay
→ Resolution
→ Social Confirmation
→ State Change
→ New Promise
```

### Key Rule

Payoff 必须改变至少一项：

```text
state
relationship
knowledge
status
resource
world understanding
future options
```

否则只是临时情绪刺激。

---

# 18. Hook Architecture

Hook 不只在章末。

分层：

```text
Book Hook
Volume Hook
Arc Hook
Chapter Hook
Scene Hook
```

类型包括：

- question；
- threat；
- reveal；
- opportunity；
- promise；
- emotional；
- decision；
- reversal。

### V2

Hook Density 不应越高越好。

应考虑：

```text
hook fatigue
false promise
repetition
```

---

# 19. Character Architecture

近期市场变化提示：

> 长篇不能只靠“主角持续赢”。

应建立：

```text
Protagonist Engine
Supporting Character Arc
Relationship Dynamic
Opponent Learning
Faction Dynamics
Ensemble Memory
```

反派/竞争者必须：

```text
observe
learn
adapt
counter
```

否则剧情会机械重复。

---

# 20. Long-Arc Expansion

优秀长篇需要逐步扩大：

```text
Scope
Stakes
Relationship Network
World Knowledge
Responsibility
Cost
```

不是只扩大：

```text
enemy power
```

### Urban Example

```text
personal survival
→ team
→ company
→ local market
→ industry
→ capital
→ national/international
```

### Family Xianxia

```text
village family
→ regional clan
→ sect relation
→ state-level faction
→ major cultivation order
→ historical legacy
```

---

# 21. Common Failure Patterns

## F-01 Premise Burnout

开篇脑洞只能支持 20 章。

## F-02 System Replaces Character Motivation

系统任务变成唯一原因。

## F-03 Payoff Inflation

每次打脸都必须更大，最后失去可信度。

## F-04 Opponent Stupidity

反派永远不会学习。

## F-05 Progression Without Consequence

升级只改数字。

## F-06 Map Expansion Without Rule Change

换地图但故事完全相同。

## F-07 Fusion as Tag Stacking

类型只叠标签，世界逻辑没融合。

## F-08 World Wiki Disease

世界观很多，但不制造剧情。

## F-09 Character Tooling

配角只为主角服务。

## F-10 AI Genericness

- 过度总结；
- 人物声音一致；
- 抽象情绪；
- 空洞环境；
- “众人震惊”；
- 重复节奏；
- 模板化章末。

---

# 22. V2 Quality Dimensions Derived from Market Research

除了 consistency，V2 后续 Quality System 应至少研究：

```text
Q-Genre Fidelity
Q-Premise Delivery
Q-Reader Promise
Q-Narrative Progress
Q-Payoff
Q-Hook
Q-Character Specificity
Q-Relationship Dynamics
Q-World Specificity
Q-Progression Satisfaction
Q-Long-Arc Expansion
Q-Genericness Risk
Q-Repetition
Q-Authorial Voice
Q-Commercial Continuation Intent
```

注意：

> 大部分是 semantic/evaluative，不应直接作为 E0 hard gate。

---

# 23. MarketTrendSnapshot Design

市场趋势必须独立版本化。

示例：

```yaml
market_snapshot:
  platform: qidian
  channel: male
  period: 2026-Q3

  signals:
    - family_xianxia
    - realist_cultivation
    - cyber_cultivation
    - urban_rebirth
    - era
    - folk_supernatural

  structural_trends:
    - genre_fusion
    - world_specificity
    - ensemble_cast
    - reality_depth
    - long_sell_orientation
```

### Important

MarketTrendSnapshot：

- 可以影响 Genesis；
- 可以影响 candidate ranking；
- 可以建议 Genre Composition；

但：

> MUST NOT 修改 Genre Constitution 的永久语义。

---

# 24. Reference Intelligence Connection

用户提供参考小说后，系统应该先生成：

```text
BookNarrativeProfile
```

包含：

```text
platform_category
genre_axes
reader_promise
narrative_engine
progression_engine
conflict_engine
payoff_pattern
hook_pattern
cast_model
world_model
arc_expansion
style_signals
failure_patterns
```

然后多书：

```text
Cross-reference Mining
↓
ReferenceEvidencePack
```

最后才进入：

```text
GenesisSpec
```

这可以让 Reference 模式学习：

> 机制

而不是：

> 情节表面。

---

# 25. Recommended Initial Genre Certification Strategy

架构层：

> 从 Day 1 支持多 Genre。

实现层：

> 深做少量认证 Pack。

建议分三阶段。

---

## Certification Wave 1 — Contrast Anchors

### GPK-U01
`urban.business.realistic`

用于验证：

- no supernatural；
- company/equity/cash；
- period/social reality；
- business causality。

### GPK-X01
`fantasy.eastern.progression`

用于验证：

- explicit supernatural；
- power progression；
- resources；
- faction；
- realm/world rule。

这两个 Pack 差异最大。

若同内核不串：

> Genre Architecture 基本成立。

---

## Certification Wave 2 — Variation Inside Family

### GPK-U02
`urban.rebirth.era`

### GPK-X02
`fantasy.high_martial`

验证：

> 同一 Genre Family 内部能否保持 subgenre distinction。

---

## Certification Wave 3 — Xianxia Stress Test

### GPK-A01
`xianxia.family`

### GPK-A02
`xianxia.realist_cultivation`

用于验证：

- family as protagonist；
- multi-generation；
- longevity；
- realm；
- resource；
- sect；
- social hierarchy。

---

# 26. Proposed GenrePack Anatomy

每个 Production-ready GenrePack 至少包含：

```text
Identity
PlatformMapping
GenreConstitution
RealityModel
WorldLaw
AllowedElements
ForbiddenElements
FusionPolicy
NarrativeEngines
ProgressionModels
ConflictPatterns
ReaderPromises
PayoffPatterns
HookPatterns
PacingProfile
CharacterArchetypes
CastModels
CanonExtensions
DomainPackCompatibility
QualityRubric
ReferenceExtractionProfile
OriginalityConstraints
CertificationSuite
```

---

# 27. Genre Canon Extensions

Core Canon 永远拥有：

```text
Character
Relationship
Timeline
Knowledge
Location
Object
Event
Promise
```

Genre Extension：

## Urban Business

```text
Company
Equity
Money
Contract
Market
Product
Career
Reputation
```

## Xianxia

```text
Realm
Technique
SpiritualResource
Artifact
Sect
Lifespan
DaoState
```

## Family Xianxia

```text
Family
Generation
Branch
Succession
Bloodline
Territory
MarriageAlliance
Legacy
```

## Era Urban

```text
PeriodFact
Policy
Price
Salary
TechnologyAvailability
MediaAvailability
```

---

# 28. Genre Certification

一个 GenrePack 只有通过：

```text
Schema
Unit Rules
Negative Contamination
Reference Mode
10-chapter
30-chapter
Cross-genre Switching
```

才可标记：

```text
PRODUCTION_READY
```

示例：

### Urban

```text
CERT-U-001 no unauthorized cultivation
CERT-U-002 money/accounting transition valid
CERT-U-003 technology obeys period
CERT-U-004 business progression has evidence
```

### Fantasy

```text
CERT-X-001 realm transitions valid
CERT-X-002 ability prerequisites valid
CERT-X-003 world law stable
CERT-X-004 urban-business rules do not leak
```

### Xianxia Family

```text
CERT-A-001 generation lineage valid
CERT-A-002 lifespan valid
CERT-A-003 succession valid
CERT-A-004 family state survives individual death
```

---

# 29. What NOT to Encode from 2026 Trends

禁止把下列当前热点当永久规则：

```text
家族修仙一定热门
赛博修仙一定热门
重生一定热门
民俗一定热门
黑暗风一定热门
```

这些属于：

```text
MarketTrendSnapshot
```

不是：

```text
Genre Constitution
```

---

# 30. Research Questions Before GENRE_INTELLIGENCE_SPEC

下一份正式 Genre Spec 需要回答：

1. GenrePack 的继承机制？
2. Primary / Secondary / Overlay 如何表达？
3. Fusion conflict 如何裁决？
4. Core Canon 与 Genre Extension 如何组合？
5. Genre Hard Rule 使用什么 Policy interface？
6. MarketTrendSnapshot 如何进入 Genesis？
7. ReferenceEvidence 如何推断 Genre axes？
8. GenrePack 版本升级如何影响在写项目？
9. 项目中途可否改 Genre？
10. Genre Certification 最低标准是什么？
11. DomainPack 怎么与 GenrePack 组合？
12. Period Constraint 应属于 Genre 还是 Domain？
13. Narrative Engine 如何验证“仍然运转”？
14. Progression Engine 如何防止后期通胀？
15. Reader Promise 如何进入 Chapter/Arc Contract？

---

# 31. Formal Architecture Conclusions

## AC-GENRE-001
Platform taxonomy is mapping metadata, not internal narrative truth.

## AC-GENRE-002
Genre is multi-axis.

## AC-GENRE-003
Trope/Mechanic is orthogonal to Genre.

## AC-GENRE-004
Domain expertise is implemented as DomainPack, not endless Genre proliferation.

## AC-GENRE-005
Genre Fusion must be explicit and policy-governed.

## AC-GENRE-006
Genre can extend Canon schema.

## AC-GENRE-007
Current market trend is versioned evidence.

## AC-GENRE-008
Production support requires certification, not config existence.

## AC-GENRE-009
Long-sell capacity is a first-class quality objective.

## AC-GENRE-010
Reference learning extracts narrative mechanisms, not story content.

---

# 32. Final Recommendation

V2 下一步不应该直接开始写 Genre 代码。

现在已经有：

```text
Constitution
+
V1 Forensics
+
External Architecture Research
+
Market / Genre Research
```

下一份应该正式生成：

# `GENRE_INTELLIGENCE_SPEC.md`

它将从“研究”进入“规范”。

它必须冻结：

```text
Genre Ontology
GenrePack Schema
Genre Constitution
Fusion Policy
MarketTrendSnapshot Contract
Genre Canon Extension
Narrative Engine Contract
Progression Engine Contract
DomainPack Interface
Reference Genre Profile
Genre Certification
```

并同时生成机器文件：

```text
genre-ontology.yaml
genre-pack.schema.json
genre-constitution.schema.json
market-trend-snapshot.schema.json
genre-certification.schema.json
```

完成这一步以后，Genre Intelligence 才真正可以进入 V2 第一批代码。

---

# 33. Source Registry

本研究主要依据以下公开资料（截至 2026-09-18）：

## Industry / Market
- 中国作家协会网络文学中心：《2025中国网络文学蓝皮书》
- 中国作家网：《AI时代、“大文学观”与世界暗面的温柔——2024—2025年男频网络文学综述》
- 中国作家网：《网络文学多元化发展进入新阶段》
- 中国作家网：《原创的标尺：一份长达20年的网文“封神榜”》
- 中国作家网：《阅文年度白金大神名单出炉 首位00后白金作家诞生》
- 中国作家网：《季越人：修仙文里也有现实主义》
- 中国作家网：《2025年第一季度网络文学新书推介》

## Qidian Platform Evidence
- 起点中文网作品/荣誉页面：
  - 《没钱修什么仙？》
  - 《苟在初圣魔门当人材》
  - 《捞尸人》
  - 《1979黄金时代》
- 起点作品分类页、书单和作品标签用于辅助确认平台分类词汇。

## Evidence Warning
起点书单中的读者评价仅作为 M3 anecdotal evidence，不用于证明市场规模或质量真值。

**END OF REPORT**
