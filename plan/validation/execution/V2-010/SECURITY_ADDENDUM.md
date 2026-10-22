# V2-010 最小安全补充（2026-10-22）

3ac41fb/run39354762695于2026-10-20实际六门PASS；其原始产物仍保留。2026-10-22复查时，pip-audit返回certifi2026.7.22的PYSEC-2026-4320（GHSA-6q48-6c7w-9gw2），固定修复版本2026.10.19。官方GitHub公告于10月20日发布；不能将旧CI改写为当时失败，也不能用它拼接新的锁文件验收。

实际依赖路径：dev pip-audit→requests→certifi；应用直接依赖SQLAlchemy/psycopg不变。没有Canon被利用的证据；这是开发工具TLS信任包的已知漏洞，mandatory gate真实失败需修复。

在既有用户V2-010正常实施/交付授权内，最小scope补充仅加入uv.lock；原scope和pin不改，opening/pre_existing/authorization字节不变。不新增依赖或框架，不变task/phase/任务依赖/五条验收，不改scanner、ignore、approval、六门、GitHub设置或runner。只将现有传递certifi升级到2026.10.19，并机器对账其余50包、直接依赖、业务代码及门禁保持不变。这是必要安全维护的实施判断，不伪称用户另行逐字批准了此包版本。

当前SSOT保持IMPLEMENTED，未提交的CLOSED提案已按逐文件hash保存在dist/validation/v2010-closure-draft-suspended-20261022；不丢弃原证据。新scope先固定，再改lock；锁定安装/本地安全/适用回归通过后，只对新最终SHA做一次关键六门验收，不重复原3ac运行。新结果通过前不关闭V2-010或P2。

公告：https://github.com/advisories/GHSA-6q48-6c7w-9gw2
原始失败：dist/validation/v2010-closure-checks-20261022/security/security/dependency-audit.json
