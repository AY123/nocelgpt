# 原始失败与修复记录

所有原始尝试按实际结果保留；成功汇总仅引用成功复验，不改写历史。

- raw/001：V2-003 启动后旧入口 fixture 前提变更，缺包预期碰到 action mismatch。修正隔离 seed，保留旧 test 定义和断言，raw/002 复验通过。
- review/diff-second.xml、diff-third.xml：新增测试辅助目录/重复暂存已删除路径的 fixture 问题；修正辅助代码，没有删正例或断言，raw/003 的181项综合回归通过。后加4项反射/注解边界，raw/precommit_weakening_final 66项通过。
- raw/004：实际差异未处置 finding 加遗漏的既有全局忽略配置，FAIL。原scope不改；v2补充当前保护身份，mtime的历史局限明示。
- raw/006：辅助保留检查脚本误认为 .gitlab-ci.yml 已存在，真实失败。raw/007 修正为检查它仍不存在，不把不存在当CI成功。
- raw/008：AI-EXEC-02 在owner尚 IN_PROGRESS时过早声明整体IMPLEMENTED，被现行治理拒绝。已回退；只有提交后成功证据绑定且task IMPLEMENTED后再更新。raw/009、010通过。
- raw/011：235通过/1失败，旧治理契约期望TASK_EVIDENCE与真实缺ci/acceptance TASK_SCHEMA不符。v3先固定必要支持路径，然后保留拒绝测试并加两项明确断言；raw/013的14项通过。
- dist/validation/v2-003-precommit/action-entry.json：主代理在检查进行时写入任务工具，实际 ENTRY_RACE 正确阻断。不是规则失败被忽略；提交后串行稳定执行入口。
- raw/018：首次提交后命令错误填写了不存在的review完整SHA，被实际固定输入校验阻断，子命令未执行。raw/019使用 git rev-parse 实际确认的 adc537d88d2228ef2690d4e7bc04d2def8e1b1af，命令前后差异检查与真实架构子命令均PASS。原BLOCKED报告与正确报告均归档。

本地通过不替代可信CI/最终验收；同一操作者的多次修复和协作复核不称独立审核。
