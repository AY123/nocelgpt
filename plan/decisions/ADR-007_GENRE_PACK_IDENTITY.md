# ADR-007 — Genre身份、扩展命名空间与版本化加载

2026-11-13；适用V2-013～016。由当前V2-013任务授权内作设计决定；同操作者技术交叉检查，不声称独立人员审核或运行验收。

## 本轮决定

采用现有Python值对象及ADR-005的ANOVELOS-CJSON-1。生产loader只用标准库，复用既有canonical encoder，不增加依赖、动态插件或另一Canon写入口。`registry.yaml`采用严格JSON子集（也是合法YAML），不是任意YAML执行入口。目录为全局只读输入，loader只读字节、不修改文件或数据库。

只支持两个冻结Anchor：`urban.business.realistic`与`fantasy.eastern.progression`。catalog字段为schema_version及packs；每条pack引用必须包含id/version/content_hash/path，重复id/version拒绝。manifest字段为schema_version/id/version/profile/extensions/strategies/rubric/examples/consumers；profile包含anchor/reality_model/setting_model/world_mechanics/forbidden_mechanics。所有字段严格封闭，未知键、重复JSON键、非有限数、错误类型、非法路径和symlink拒绝。

PackRef三元组(id,version,content_hash)必须完整精确匹配。content_hash是整个manifest规范字节SHA256，manifest不含自引用hash；另记录原manifest bytes的source_file_sha256及catalog_source_sha256和相对来源路径。文件只读取一次，解析/hash来自相同字节。GenreProfile随Pack同版，其身份使用anchor、同版version及自身规范内容hash，不建立互相漂移的独立版本来源。

配置返回冻结值对象、tuple及bytes；to_dict返回新副本。项目bind保存project、完整原manifest及规范bytes、profile与pack身份和目录来源，后续修改目录不影响既有binding。该binding是可持久化消费的进程内快照，本轮不声称已把书籍配置写入Canon，也不提供生产Pack切换权限。

可选策略只在已绑定Pack内按精确strategy id选择。无命中返回NO_MATCH/None且保留原binding的全部身份；没有关键词、模糊标签、排序第一条、跨Pack或默认子流派fallback。缺Pack/版本/hash及未知扩展均硬拒绝。

## 扩展与后续任务边界

本轮两Pack的extensions为空；所有非空扩展在实际实现注册前均拒绝。V2-015/016实现时，扩展命名空间须归属相应Anchor，Schema及版本/hash明确且封闭；不得从manifest import任意Python类、任意路径或调用者自报“支持”。合法字段、单位/资源/比例/境界及前置状态、合法转移由实际扩展验证器负责，变化仍经有限Delta及唯一CanonCommitService。扩展加入或世界机制变化必须新Pack版本和适用重验，旧书保持绑定。

world mechanics和规则声明是V2-014实际policy及后续Contract/Context的输入，不等于当前loader已判断正文事实。strategies是可选创作建议，rubric/examples为具名配置样本，不是作品质量评分、真人批准或市场证据。现实Anchor不默认重生/系统/修炼，幻想中的交易和商会不自动变成都市场景或污染。

## 验证

原AT-V2-013四条不变：精确身份正负控；未知Pack/扩展拒绝；全局目录到项目完整血缘/不可变性；显式Pack且可选策略无命中时身份不变。两Anchor的实际数据由同一loader加载，错误类型/路径/重复/篡改及近似策略命中不能改变Pack。后续世界语义、类型扩展、模型、小说阅读质量和外部备份均不据此完成。
