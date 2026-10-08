# 本轮直接人类授权与解释边界

记录日期：2026-10-08（Asia/Shanghai）。

最新直接人类消息原文：

> 继续推进V2-004

该消息承接已向用户说明的下一步：修复 IR-MAINLINE-P2-01，给不可变批准增加获批 ledger hash 和批准类型，严格核对并补充正负测试、更新本地候选/审核包。此处后文为执行范围解释，不冒充用户逐字授权文本。

先前 V2-004-P0-MAINLINE-UNBLOCK-001 的边界继续有效：停止 H2/H3/H4 credential evidence acquisition；保留旧材料和 OPEN 状态；六门 mandatory；不扩大 ignore、不自行审批、不运行远程 CI、不改 GitLab、不启动 runner、不 push。本轮也不 commit/MR，不开始 P1。

本轮授权是本地代码修复和验证，不是真实 38 项 exception approval，也不是单一 7-finding Owner risk acceptance。不得填写批准时间、有效期或以角色字段伪造 authority。
