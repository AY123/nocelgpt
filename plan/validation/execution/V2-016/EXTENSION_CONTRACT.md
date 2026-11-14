# V2-016 — 东方玄幻 Canon 扩展契约

任务授权细化ADR-007，复用V2-015已有ExtensionBinding/Registry、四种有限Delta、唯一CanonCommitService及保留字节的重放路径。无需新表、新Writer或新ADR。原三个AT断言、任务依赖与阶段不变。同操作者实施与技术交叉检查，不声称独立人员审核。

## 有界类型与身份

新增ProgressionState(realms,cultivators,abilities,ability_states,resources)，成员均为冻结精确类型tuple：
- RealmDefinition(id,rank,resource,unit,breakthrough_cost)：realm的rank唯一且从0连续；rank0费用为0，其余费用为正整数；资源/单位及费用都是root冻结规则。
- Cultivator(id,realm)：realm引用已登记定义。
- AbilityDefinition(id,minimum_realm,resource,unit,learning_cost,use_cost)：学习及使用费用为正整数、最低境界和费用冻结。代表有限注册能力/功法，不引入装备引擎。
- AbilityState(id,owner,ability,learned,uses)：owner必须是已登记cultivator；同owner/ability唯一；learned为严格bool，uses为严格非负整数；未学会时uses必须0；已学会者必须符合最低境界。
- ProgressionResource(id,owner,resource,unit,quantity,spent)：owner为root登记Entity（允许商会等非修行者）；同owner/resource/unit唯一；quantity及累计spent为严格非负整数。

全部对象ID唯一、引用同project且均在root完整Entity集合中；realm/ability必须有定义，state必须至少有realm/cultivator和资源。拒绝bool冒充数字、float、负数、未知键、未声明公司股权字段。资源类型/单位是显式非空标识，不用商业关键词判错。各项字段编码为独立WorldFact，predicate为ext:fantasy.progression:<kind>.<field>，factID由subject/predicate规范字节确定；不使用自由JSON事实。

## 强制状态转移

metadata、种类、事实身份及root规则不可变；扩展字段必须保持KNOWN。MARK_UNKNOWN/RETRACT或改id/owner/cost/单位不能绕过规则。原生generic SetFact和builder同样由Registry的完整before/after验证强制检查。

境界仅允许不变或相邻rank+1；禁止跳级和倒退。学习仅false→true，禁止遗忘退款。使用次数单调；增加uses时，before必须已学会且before境界足够。所有行为前置统一使用before状态，不能同批先升级再按新境界学习/使用；学习与使用不能靠中间overlay绕过。

费用从冻结RealmDefinition/AbilityDefinition读取，按owner/resource/unit累加：相邻进阶收目标境界breakthrough_cost，学习收learning_cost，uses增加n收n*use_cost。对应owner在before必须已有足额quantity；该owner对应pool的spent增量必须精确等于本次总费用。任何无行动消费、少付/多付、他人代扣、重复共用扣款、错误资源/单位和spent倒退均拒绝。所有resource/unit分组的quantity+spent总量守恒；不允许铸造/销毁或隐式兑换。

商会资源交易只改变两个兼容pool的quantity，spent不变；必须正整数且源足额，资源和unit精确相同。词汇“商会/财富/交易”不会改变Anchor或成为拒绝理由。有限builders advance_realm、learn_ability、use_ability、transfer_resource仅为已登记事实产生标准SetFact，完整revision/state前置、正文位置、授权ref沿用原Delta。普通章节可无进阶或资源变化，不强制每章升级战斗。

## 版本、Canon与边界

新增fantasy.eastern.progression Pack1.1.0、fantasy.progression Schema/validator1.0.0。Schema封闭结构与编译类型通过正负例对账，跨字段/转移由实际validator承担；不新增依赖。保留旧Pack1.0、urban1.1及旧政策hash/行为。ExtensionRef按namespace→Anchor精确登记，不允许manifest动态import或调用方自报handler。新增policy只绑定新精确Pack，沿用旧fantasy世界机制：允许LOCAL_TRADE，WORLD/OCCURRED的未声明现代公司股权制度FAIL；梦境/引用/UNKNOWN保留V2-014语义。

根提交完整冻结pack/schema bytes/version/hash和全部Entity；binding继承已有1.1格式。当前目录变化不能改变旧书。现有root验证、Permit、review、chapter事务、冷读回、历史重放自动消费编译ProgressionValidator；PACK依赖仍须精确等于root保留bytes。未知版本/缺binding/空Registry/错schema或Pack均拒绝。不扩展domain、SQL或Canon写路径。

契约和真实PG验证全部三个AT、直接SetFact负控、费用不重复消费、幂等/失败不写入/冷重放及旧版本兼容。CI driver与固定命令测试仅追加tests/integration/test_v2_016_postgres.py。完整本地通过后正常main交付，只运行一次关键同SHA六门CI，核对原始来源与产物后才关闭本任务。

本任务仅证明结构化已登记玄幻事实一致性，不证明正文抽取、全文Q2、生产Permit、叙事阅读质量、自动写作或外部备份。P3及人工标准测试书仍单独评估，不用AI交易fixture冒充人工审定故事。
