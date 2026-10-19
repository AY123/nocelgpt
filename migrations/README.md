# Canon migration 0001

SQL 的唯一源为 `src/anovel/canon/sql/0001_root.sql`，随 wheel/sdist 发布。调用 `anovel.canon.migrations.migrate(engine)`：仅 PostgreSQL、事务级迁移锁、版本/checksum 核对，不写初始 Canon，不自动选数据库。不能编辑已部署迁移来修改故事历史；后续变更新增版本。

V2-009 测试创建独立临时数据库，通过相同迁移与 `CanonCommitService.initialize_root` 写入初始事实。生产不得向 Worker 暴露管理连接。当前服务仅 root，不实现章节 Permit / 一般提交 / 投影恢复。早期恢复责任见 ADR-006；本轮不提供生产运行或备份验收。
