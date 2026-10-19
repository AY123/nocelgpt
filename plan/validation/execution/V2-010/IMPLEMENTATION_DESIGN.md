# V2-010 — 授权章节提交的最小实现

依据本轮直接任务授权、现行03契约及已接受ADR-004/005/006细化。同操作者实施和验证；不是新SSOT、独立审核或完成证据。原五条验收不变，不提前关闭V2-011/012。

## 能力和信任边界

沿用同一个CanonCommitService及现有Repository内部事务。root接口保持兼容；章节只消费ADR-004的四种既有事实操作，不新增领域操作、Genesis、Retcon、Workflow或模型调用。

章节授权是独立的branch-scoped管理记录，包含actor、issuer、授权version、enabled及完整policy。根initializer不自动获得章节权限。管理engine仅由可信应用组合持有，不交给普通Worker；authenticated actor仍由可信入口提供，本轮不新增网络认证。

规范02及05允许P2隔离测试issuer，正式签发集成在P7。因此本轮实现独立ProtectedPermitIssuer的隔离测试能力，不伪造Q0–Q3。该能力和接收测试Permit的服务组合均须显式绑定同一个可销毁`anovel_test_...`数据库身份。默认生产服务拒绝TEST Permit；没有允许调用方传`ALLOW`、检查结果或production标签的入口。数据库名检查仅是防误用护栏，隔离仍依赖独立配置/凭据与可信组合，不声称可抵抗数据库管理员。

ProtectedPermitIssuer从受控policy读取固定必跑集合，实际运行TEST_CANDIDATE_BINDING-1和TEST_DELTA_PREVIEW-1，再把完整检查记录持久化进Permit。普通提交只传Permit引用，必须从库读取完整记录；不能用同名自造对象签发权限。生产Q0–Q3及正式issuer保持未实现，不以TEST正例冒称产品放行。

## 输入和证据

ChapterCandidate(id:EntityId,branch,parent_ref,version,prose:bytes,delta:NarrativeDelta,dependencies:tuple[CandidateEvidence,...])。
CandidateEvidence(kind,content:bytes,schema_id,schema_version,producer,producer_version)；kind闭集CONTRACT/PACK/MODEL/CONTEXT，四类恰好各一，content是完整非空bytes。候选id与Delta.source_id一致，作用域和parent严格相符；修改正文、Delta、版本或依赖任何一项都改变稳定payload。依赖包装绑定project/branch，不从其自由内容推断权限；测试MODEL等内容明确是fixture而非真实调用。

Permit完整规范字节绑定project/branch、actor/request、parent、候选id/version、raw prose与Delta内容hash、依赖的metadata/hash/完整bytes、完整policy及hash、issuer、必跑检查记录、授权/执行version和数据库生成的issued/expires时间。TTL是明确有界输入，DB时间重验有效期。引用id和body hash均核对，缺失/损坏/未知版本/错scope/错policy/过期/撤销/缺必跑检查均拒绝。

原始正文、Delta、输入、依赖包、Permit和候选事实状态作为不可变artifact与提交链接。多检查/多依赖用完整bundle，不增通用框架。长期读取不因Permit过期/撤销失去历史bytes。已接受正文无覆盖API，保留现有数据库不可变约束；更正留未来明确流程。

## 存储与事务

增加0002_chapter.sql；0001及其checksum、既有root envelope/bytes不改。迁移验证已安装版本为已知完整前缀，逐次事务升级；未知版本/缺口/checksum漂移拒绝。requests增加ROOT/CHAPTER purpose和章节冻结parent；已有请求默认ROOT。新增章节authority和Permit记录，扩artifact闭集，event/reducer按ROOT_INITIALIZED/ROOT-1与CHAPTER_COMMITTED/FACT_DELTA-1成对约束。

事实索引保持不可变身份登记。每章保存按commit绑定的完整有限事实状态，不覆盖旧facts。load_baseline从真实parent提交读取；root从seed构造，章节从已校验状态artifact构造，返回parent_ref=所读取commit_id。preview输出中的旧parent引用只用于derived-from证据；不冒充新HEAD。这不是V2-012全事件重建。

预处理完整bytes与hash在事务前完成。签发、提交、取消、撤销锁同一branch行；保留connection级READ COMMITTED override。提交顺序：核对request actor/purpose及既有同payload收据，随后检查当前章节grant/policy、请求fence、Permit有效性与HEAD，实际preview_delta，再写artifact/commit/link/event/receipt及HEAD CAS。任何故障全回滚；无远程调用。

成功收据恢复早于当前过期/撤销/HEAD判断，但仍验证actor/scope/稳定payload。ROOT与CHAPTER请求不得交叉复用。同scope相同内容artifact可复用，但必须INSERT DO NOTHING后逐字节核对，绝不UPDATE覆盖。

## 对外接口

CanonCommitService保留root方法，并增加：
- configure_chapter_authority(project,branch,actor,issuer_id,policy_version) — 可信管理组合；不接受空必跑集合。
- begin_chapter(project,branch,actor,request_id,parent_ref) -> ExecutionTicket。
- commit(ticket,candidate,permit_ref) -> CommitReceipt；普通提交无issue/check注册入口。
- load_commit(project,branch,commit_id) -> StoredChapter；load_baseline -> FactBaseline。
- review_submission(ticket,candidate) -> 只读正文/Delta/parent/version/阻断信息，不放行、不写Canon。
- revoke_chapter_authority(project,branch,actor)；cancel仍沿用同一服务。

ProtectedPermitIssuer(engine,test_database,issuer_id)只由可信隔离测试组合创建：issue(ticket,candidate,ttl_seconds)、revoke(project,branch,permit_ref)。服务仅在显式test_database匹配时消费该来源。

CommitReceipt新增严格to_dict/from_dict和闭合commit-receipt.schema.json，字段兼容现有root收据。生产默认拒绝测试Permit；P2正向章节提交只证明真实数据库协议，不证明语义检查、模型、生产备份或产品完成。

## 验证

真实PG覆盖五条原验收、0001带root升级的原字节保留、0002失败回滚、伪造/缺少/过期/撤销/错误绑定/缺检查/production消费TEST拒绝、root权限不升级、请求purpose隔离、两种取消次序、故障无新增/HEAD事件一致、历史正文不可改及完整证据读回。新增Schema正负对账。现有root测试只维护迁移列表和真正未知版本前提，所有原断言/并发/AUTOCOMMIT负控保留。包装测试包含0002，六门不削减。
