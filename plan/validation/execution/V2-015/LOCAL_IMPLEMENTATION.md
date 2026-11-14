# V2-015 本地实现

本地实现完成，任务仍IN_PROGRESS；真实远程同SHA六门尚待执行。新增都市商业1.1.0 Pack及urban.business1.0.0闭集Schema/validator，旧两1.0 Pack和旧现实政策指纹保留。公司/现金账户/股权/资源持仓使用严格整数和明确币种/单位，逐字段映射独立标量Fact；三种转移复用原四种Delta，整体前后守恒，metadata冻结。原生SetFact、UNKNOWN/RETRACT同样受强制验证，不能绕过builder。

通用领域接缝不含公司/财务字段；root保留完整Pack/Schema及实体集合，非空绑定采用显式1.1嵌套格式，空绑定仍原1.0字节。根写入、Permit、review、commit、读回和replay接入同一注册表/冻结绑定；没有新SQL表/第二写口或可动态导入的插件。生产仍拒P2 TEST Permit。CI driver只追加真实PG文件，同步旧固定命令测试并保留原断言和所有六门。

实际本地UNIT 1386、ARCH 244、PG 185，合计1815项，0失败/error/skip。新88契约+28PG属于各套件子集，不重复计数。STATIC、五项治理、安全54/54精确消费及依赖扫描均PASS；命令/退出/日志/JUnit/hash见LOCAL_RESULTS receipt引用。这些是实际工作树证据，不冒称immutable SHA CI。

首轮PG3个失败只在新测试最后的RootSeed tuple顺序比较；此前转移/保存/重放断言均通过。既有to_dict规范排序正确，测试已改完整canonical seed字节相等，保留全部数据验证；原3失败及最终185通过分开保留。未通过修改生产排序/删断言获得PASS。

边界：只支持已登记公司/账户/持仓的转移，不含动态创建、发行销毁、FX或会计ERP。业务JSON拒玄幻字段，新1.1 Pack复用V014结构化现实机制规则；这不证明所有普通事实或全文已经Q2语义验证。真实抽取/生产Permit/写作阅读质量、外部备份、V016/P3均未完成。标准人工审定Story Fixtures和自然连续章节认证未建立，不把本轮AI构造的测试输入当真人批准测试书。

2026-11-14追加：已按e9a19d0b105443374006807cda905d0c67caffd7/run43539261866完成同SHA六门验收，见[正式验收](closure-20261114/ACCEPTANCE_SUMMARY.md)。上文本地失败/通过保留各原语义。
