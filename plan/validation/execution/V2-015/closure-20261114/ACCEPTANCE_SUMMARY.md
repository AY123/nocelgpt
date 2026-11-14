# V2-015 工程验收

V2-015 CLOSED。受测代码`e9a19d0b105443374006807cda905d0c67caffd7`；[GitHub run43539261866](https://github.com/AY123/nocelgpt/actions/runs/43539261866)同SHA六门全部PASS：1386UNIT +244ARCH +185PG = **1815项，0失败/error/skip**。新88契约+28PG用例属于各suite子集，不重复计数。仅一次关键run、attempt1；原始六ZIP、GitHub digest、receipt source/driver/lock、命令退出/日志/产物hash及JUnit均已逐项核验。

新增都市商业1.1.0 Pack及urban.business1.0.0注册Schema/validator，旧1.0 Pack与旧现实政策指纹保留。公司、现金账户、股权及资源持仓用闭集字段和严格整数，币种/单位/引用明确；完整状态按币种/公司/资源单位守恒。三种Transfer builder及直接generic SetFact均受同一验证，未知/撤销余额、metadata改写、超额/部分转移、错误namespace或Pack/Schema都拒绝。

业务字段编码为独立标量Fact；Core仅通用ExtensionBinding/Registry，原四种Delta、旧SQL与唯一CanonCommitService保留。空绑定保持1.0字节，非空嵌套格式显式1.1并保存完整Pack/Schema及root Entity集合。root/Permit/review/commit/读回/历史replay贯通同一冻结绑定，章PACK依赖与root完整bytes一致；冷连接可重放指定历史目标，不读当前catalog猜测版本。CI只追加本任务PG文件，旧用例/六门/allow_failure=false不变。CODE_MANIFEST登记10个明确集成改动、9个新增文件，其他35个既有源/数据/测试/工作流/锁文件保持。

首次PG3项失败是新测试将输入Entity tuple顺序当成存取契约；旧生产to_dict已正确排序，改为完整规范seed字节比较后185项全部通过。首次UNIT3个安装/打包用例被本地沙箱拒绝uv缓存，未弱化测试；适用权限下重跑完整UNIT通过。原失败与修复后结果分开保留；本验收仅使用本次远程同SHA完整结果，不拼旧revision。

安全54项仍OPEN，批准范围/期限不变；本次54/54精确消费，0新增未匹配/未使用，51依赖0漏洞。实施、验证及技术交叉检查同操作者承担，不冒称独立人员审核。

## 能力边界

当前仅已有公司/账户/持仓的类型化转移，不含动态公司创建、发行销毁、兑换或会计ERP；仍仅隔离TEST Permit，生产Q0–Q3签发未完成。结构化现实机制及业务Schema不代表全文语义抽取/Q2、自然章节或真人阅读验证已完成。AI构造的交易测试输入不冒充人工批准标准测试书；两Anchor人工Story Fixtures、抽取遗漏和连续章节认证仍待后续。AR-15/CA-08/RR-11/SUP-01仅当前机制范围部分解决，P3/V2-016、自动写作、阅读质量及外部备份仍未完成。

结项只登记证据/状态/导航，源码、数据、测试、driver/lock与受测SHA相同，不为资料再跑CI。下一任务V2-016：东方玄幻Canon扩展。
