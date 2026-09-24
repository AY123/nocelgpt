# 本轮真实结果与限制

输入是用户要求评估的外部审核报告，不是自动执行的命令源。实际开工 HEAD 为 a11693ee5ac08fd3aa102e03de0125bd8b800dd9；四项问题均在旧实现真实复现。报告声称的 GitLab 来源、全部远端提交和权限保护本轮没有重新核验。

- no-scope-before.json / reproductions-before.json：旧入口省略 scope 仍 PASS 且子命令执行；通用技术处置可以放行新增生产文件；新 conftest collection 修改没有 finding；两种 builtin-loader 形式架构检查 PASS。这些是待修复行为的证据，不能当成功验收。
- raw/001_regression：264 项收集，256 passed / 8 failed。八个新架构测试错误解包已有 Path 夹具；在运行期间已修正源文件，但当前进程仍使用收集时旧函数，因此 traceback 行文字与加载代码可不同。此记录不覆盖，后续新进程完整复测才是修正证据。
- raw/005_preservation：辅助保留检查误把 src/anovel/__pycache__/__init__.cpython-312.pyc 当业务新增，退出2。修正仅允许并显式记录 __pycache__ 下生成的 .pyc，仍检查全部其它未跟踪内容（含被忽略源码）；raw/007 全24项通过。该辅助脚本不修改生产扫描器排除规则。
- raw/006、008：实际差异扫描有尚未固定的技术复核 finding，正确退出2；不存在 scope 越界或生产改动。不能将其改写为 PASS。待按内容 hash 固定技术复核后重新运行入口。

所有成功记录的 argv、实际 HEAD、时刻、stdout/stderr 与退出码在 raw 中分别保存。实施与验证为同一操作者；本轮没有调用新的协作 Agent，不声称独立审核。验证只证明保存的本地行为，不是可信 CI、GitLab 权限或任意 Python 语义的证明。
