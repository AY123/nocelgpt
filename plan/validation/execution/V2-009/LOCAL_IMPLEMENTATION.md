# V2-009 本地实现

ADR-005/006原文在d8df3a9固定，接口前接受；原IMPLEMENT入口通过后实施。本轮仅登记IMPLEMENTED，不关闭V2-009或P2，远程CI未运行。

实现：ANOVELOS-CJSON-1及raw UTF-8身份；打包SQL、校验和/事务迁移；project/branch复合FK；完整原文/输入/授权字节；root-only CanonCommitService；同branch锁下唯一root、控制版本、取消/撤销与成功收据恢复。初始Entity/Relationship/WorldFact全部走同一服务，迁移/provision不写故事。历史内容不可就地更新删除，读回校验hash；实际数据库丢失恢复、完整章节Permit、一般提交与投影仍由V2-010～012/028承担。

初始化actor由可信应用入口提供，服务未实现网络身份认证。管理engine不能给Worker。本轮只用可销毁测试库，不宣布production-ready。

## 本地结果

UNIT 1014，ARCH 244，字节身份/模型专项84（UNIT子集），真实PostgreSQL 60（其中原基础服务1项），均0失败/错误/skip。STATIC、五项治理、Secret/Dependency通过。SQLAlchemy2.0.54和psycopg3.3.6由dev移至runtime，51个锁定包版本无升级；独立无dev安装能导入Repository/service并读取打包SQL。

真实事务负测发现AUTOCOMMIT连接可使旧写入非原子，已修正为实际connection上设置READ COMMITTED；修复后故障注入无残留。旧GitLab测试夹具仅固定历史命令，新增断言保证当前POSTGRES_ENV包含原服务检查和V2-009全部数据库用例。未改远程设置或放宽门禁。

复现：`.venv/bin/python -B scripts/ci/run_gate.py postgres_env --output-dir dist/validation/<new-dir>`；本机Docker须可用，缺失失败不skip。测试自动建临时数据库、清理自己资源。原始结果见local-results；失败尝试保留dist/validation/v2009-local-20261018，不包装为PASS。

原四条验收分别覆盖：空库迁移/checksum；合法与跨scope数据库引用；两个PG backend真实锁竞争和唯一root；接口前ADR、取消/提交次序、权限版本、完整bytes读回及早期恢复责任。最终正式验收仍需一个相同最终SHA远程六门运行。
