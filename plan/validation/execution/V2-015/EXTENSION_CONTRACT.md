# V2-015 — 都市商业 Canon 扩展实施决定

本决定在接口实施前细化已接受ADR-007，复用ADR-005字节身份及ADR-006唯一提交/恢复边界。当前真实代码只有标量Fact、四种Delta操作和空扩展目录，因此补通用注册接缝是本任务必需工作，不另建Canon或财务数据库。原三项验收及任务身份/依赖不变；同操作者实施与技术交叉检查，不声称独立人员审核。

## 有界数据与合法操作

`business.py`提供冻结Company(id)、CashAccount(id,owner,currency,balance_minor)、ShareHolding(id,company,owner,parts)、ResourceHolding(id,owner,resource,unit,quantity)、BusinessState(companies,accounts,holdings,resources)。EntityId必须同project，字段精确封闭。公司股权总额固定1_000_000 parts；金额为最小货币单位整数；资源数量为显式unit的整数。所有数量拒绝float/bool/负数；交易量严格正整数。各持仓总额须等于公司固定股权总额，零余额/零持仓是合法值。

扩展将每个具名字段编码为独立WorldFact标量，predicate固定为`ext:urban.business:<kind>.<field>`；不存自由业务JSON字符串。kind/字段集合由实际编译Schema与validator封闭定义，Fact.id确定且唯一，同(subject,predicate)不能重复。每个公司/账户/持仓及holder/owner/company引用都必须对应root实际Entity；不依赖显示名。

有限transfer builder只对已有现金账户、股权持仓、资源持仓产生两个SetFact，复用当前NarrativeDelta、源证据及完整revision/state前值。转移校验不只存在于builder：原始generic SetFact同样要通过注册扩展对完整冻结before/after的强制验证；metadata和事实身份不可变，拒绝MARK_UNKNOWN/RETRACT绕开余额前提；现金按currency、股权按company、资源按(resource,unit)分别守恒。负余额、币种/单位不符、超额持仓及部分转移拒绝。允许同一批多项守恒转移，失败不产生部分候选或部分提交。

只处理已登记公司、账户与持仓；不在本任务实现动态实体创建、发行/销毁、币种兑换、完整会计ERP、授信或外部交易服务。合法普通Fact仍按原P2路径处理。保留业务命名空间的字段不能被自报扩展或普通数据格式绕过；都市业务结构拒绝玄幻字段及跨Pack使用。真实正文的语义抽取/全文Q2仍是后续范围，V2-014结构化世界机制规则继续使用，不用关键词判正文事实。

## 最小通用接缝与身份

`domain/extensions.py`仅定义ExtensionBinding、ExtensionValidator Protocol、ExtensionRegistry和reserved namespace校验，不含公司/财务字段或genre实现依赖。ExtensionBinding字段固定：namespace、version、schema_id、schema_hash、pack_id、pack_version、pack_hash、pack_bytes、schema_bytes、entity_ids。bytes使用base64明确序列化；schema_hash为ANOVELOS-CJSON-1 Schema内容SHA256，Pack hash沿用完整manifest规范字节SHA256。pack_bytes为ProjectGenreBinding.to_dict的完整规范字节，包含项目、原始manifest/catalog、source信息与精确PackRef；不是只有hash。entity_ids为完整root登记EntityId tuple，root校验与真实Entity集合精确一致。

`RootSeed.extensions`与`FactBaseline.extensions`默认空tuple；空时保持原1.0字段/字节，非空使用显式1.1嵌套格式并保留完整binding。NarrativeDelta仍为原1.0四种标量操作，不增加任意扩展op，不改旧SQL、旧事件或规范编码。FactBaseline在preview、历史重放及重锚parent时传播同一冻结binding。

ExtensionRegistry验证root/baseline/transition，任何`ext:`数据无匹配binding或无已登记handler均拒绝；默认empty registry不能放行业务数据。只有编译的genre.extensions.registration工厂登记实际BusinessValidator，既有CanonCommitService和ProtectedPermitIssuer在可信组合处加载该注册表，内部Repository及projection通过通用接口消费；不开放调用者按路径import或自报支持的API。Domain.preview_delta追加可选extension_registry参数，缺失时对扩展fail closed；常规纯预览不获得提交权。

Canonical root提交、root读回、Permit发行、review、chapter提交、state读回及历史replay都必须校验同一冻结注册信息。业务chapter的PACK依赖content必须精确等于root binding的pack_bytes，不接受别的版本或只有自报ID/hash的字典。历史按已保留schema/pack内容及编译的版本化handler运行，不从当前目录latest猜测。未知handler版本/schema/hash或绑定变化拒绝。

## Pack/Schema与兼容

新增urban.business.realistic 1.1.0及urban.business 1.0.0 Schema/validator，保留旧1.0.0 Pack原文件及旧ref可加载。manifest extensions改为精确ExtensionRef(namespace,version,schema_id,schema_hash)数组；未知/不匹配/跨Anchor扩展拒绝。空extensions旧Pack返回原空tuple。ProjectGenreBinding增加离线from_dict恢复，验证全部保留字节和目录记录，不访问当前catalog。GenrePolicy只显式增加新1.1.0精确ref并沿用现实机制，旧两ref及其结果继续可复现，不自动接受其他版本。

规范Schema与手写类型适配通过正负例一致性核对；生产不新增jsonschema依赖。注册与Schema内容由编译常量固定，并与specs文件规范字节对账，不能以manifest声称“支持”来放行。

## 验证与任务边界

新增契约与真实PostgreSQL测试：合法商业公司/股权/现金/资源交易、整数/比例/币种/单位/引用/余额负控、原生SetFact绕过负控、Pack/Schema/namespace不匹配、取消/幂等/失败不写入、冷连接读回及历史重放。PG六门driver仅追加本任务真实测试文件，保留所有旧检查；对应固定命令测试精确追加同一文件，不降低验收。

所有旧回归继续执行。本地全部通过后正常main交付，并只触发一次关键同SHA六门CI；原始产物核验后才关闭V2-015。P3/V2-016、生产Q0–Q3签发、自动写作、阅读/市场质量、外部备份保持未完成。修正既有Canon路径不重新声称旧任务独立验收，也不启动付费模型或真实有价值小说持久运行。
