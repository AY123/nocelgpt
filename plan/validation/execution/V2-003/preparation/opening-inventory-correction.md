# 开工清单补正（不扩大修改范围）

2026-09-24，真实差异命令 `raw/004_unreviewed_actual_diff.json` 返回 FAIL。除待技术复核的4项 finding 外，`.claude/settings.local.json` 被固定基线扫描识别为范围外新增文件。真实 `git check-ignore -v` 确认该文件被用户全局规则 `**/.claude/settings.local.json` 忽略；原 PREPARE 使用的 Git 可见清单遗漏了它。

该文件的现有 mtime 为 2026-09-23 15:51:48（本地时区），早于此任务准备；但时间戳不证明开工时字节相同。因此不伪称原开工已核验它，也不将其归为本任务成果。依据用户要求保留既有工具配置、仅实施本任务，本次补充采集其当前普通文件模式和 SHA-256，用作此后的精确保护身份。未读取或复制配置内容到证据，未改动配置、全局 ignore、根 ignore 或扫描器排除。

原 `scope-baseline.json` 及 pin `518c8a6646acbd236a38436388d05da06ac19abd` 原样保留。新 `scope-baseline-v2.json` 只新增上述 `pre_existing` 身份和本局限；opening revision、packet_ref、allowed_paths、protected_paths、authorization_source、原用户文件身份全部相同，`task_edit_authorized=false`。这不会授权修改该配置；后续任意字节/模式/index 变化仍阻断。

新记录先单独提交固定，后续检查使用新完整 Git pin。历史检查不改写。此修正属于同一操作者的准备清单补正，不声称独立审核、远端授权或可信 CI；共享写权的外部保护仍待 V2-004。
