# ADR-005 — 规范化字节与原始正文身份

日期：2026-10-19。任务：V2-009，后续 V2-010。责任：canon-maintainer。依据用户“先准备 ADR-005、ADR-006，再实现 Canon 持久化 Schema 与 Repository”决定；同一 Codex 操作者实施与技术复核，不声称独立人员验收。生效状态由 ADR_DECISION 及机器登记决定，本文不证明实现或 CI。

## 决定

采用项目自有 **ANOVELOS-CJSON-1**，不声称 RFC/JCS 兼容。输入只接受精确 JSON 原始类型：dict（键只能 str）、list、str、int、有限 float、bool、None；不隐式调用对象序列化、不接收 tuple/set/Decimal/datetime、自定义子类或循环容器。领域对象先通过自己的严格 `to_dict` 适配。

- UTF-8，无 BOM，无额外空格；对象键按 Unicode code point 升序，数组顺序保持。集合由领域 adapter 显式稳定排序。字符串不做 NFC/NFKC、trim 或换行替换，拒绝孤立 surrogate。双引号、反斜线、控制字符依 JSON 转义；其余 Unicode 原样 UTF-8。
- bool 与 number 分离，null 为显式 JSON null，不推断 UNKNOWN/删除/NO_CHANGE；领域层继续使用 ADR-004 的封闭结构。
- int 使用十进制，不加正号、不加指数。float 必须有限，由 `as_integer_ratio()` 得到精确 n/2^k，以 abs(n)*5^k / 10^k 输出十进制，补足小数零、去尾部小数零；负零统一为0。因此1与1.0、0与-0.0相同，bool true不同；0.1 的二进制实际值精确写为 `0.1000000000000000055511151231257827021181583404541015625`。不采用默认浮点打印或业务精度舍入。此规则与现有 Scalar 的 int/float 数值比较一致。
- 通用编码器不猜测时间字符串。系统时间通过单独 UTC adapter：必须 aware datetime，转换 UTC，以固定六位微秒和 Z 输出；naive拒绝。领域 StoryTime/叙述位置保持各自已有语义，不当系统时间转换。
- structured hash 为 SHA-256(canonical bytes)，记录编码版本。raw prose hash 为 SHA-256(输入的严格有效UTF-8原始bytes)，保留 BOM、CRLF、空格及末尾换行。raw与structured是不同artifact类型，内容哈希相等也不等于来源或权限相同。

验收向量至少固定 `{}`、空列表、键重排、中文/组合字符、转义、1/1.0/true、-0.0、0.1、最小有限float、巨大int、时区转换。精确期望字节与独立固定哈希同时测试；未知类型、非有限值、surrogate、循环、非字符串key拒绝。编码器设置有限嵌套深度，错误不降级到repr/default=str。

## 持久化身份

Canon ID 使用 `sha256:` 加结构化提交包的64位小写摘要；包显式包含 kind/schema、project/branch、parent、稳定request ID、初始事实、raw prose hash及初始化授权快照。时间在服务端生成并随提交保留，不纳入稳定请求载荷；attempt ID不进入逻辑幂等身份。作用域、版本、内容与来源分别核对。

原始canonical bytes及raw正文直接存 PostgreSQL bytea；不从jsonb、数据库文本格式或重排JSON计算权威hash。加载先核对保存字节hash，再解析，拒绝损坏；恢复不只保存hash。ADR-004的parent_ref仍是外部引用，只有从Repository读取已存在提交构建的FactBaseline才携带持久Canon ID；不得把任意parent_ref当作已认证HEAD。

软件迁移版本、Canon包版本、reducer版本分开记录。未来变更编码算法须新版本与迁移方案，不重算旧提交身份。
