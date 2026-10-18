# V2-007 本地实现

ADR-003原文先在f2bd207固定，再由c586d98登记接受，IMPLEMENT入口PASS后才实现接口。Task与AT仍只登记IMPLEMENTED，不是VERIFIED/CLOSED；P1未验收。

## 能力与复现

- `events.py`：稳定事件身份、显式occurrence、同章主要叙述位置、独立故事时刻；未知/范围重叠/同时不会被ID强排。
- `promises.py`：读者兑现窗口、OPEN/PAID/BROKEN/ABANDONED；同项目已发生事件才能兑现/违约，完整事件快照和Timeline对账后才能恢复终态。晚兑现可PAID并报告LATE，超期不自动违约。
- 两个Schema封闭结构、共享事件定义对账；跨字段时序及外部引用由领域入口校验。
- 运行 `.venv/bin/python -B demo_v2_007.py` 查看插叙双顺序、窗口、未知发生拒绝及完整往返。
- 运行 `.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/test_v2_007.py` 验证三条原验收断言及边界。

## 本地结果与限制

V2-007专项 81项、全UNIT 826项、ARCH 244项通过，0 skip；STATIC和五项治理检查PASS。原始本地receipt/JUnit与代码hash在 `local-results/`；这些record的revision是当时dirty worktree的HEAD上下文，不冒称该HEAD已包含实现。固定后隔离复核另在dist保存actual SHA及结果。

不改知识/事实/Intent，不新增DB、Provider、Canon/reducer、Agent或付费调用；不认证自然语言确已发生/兑现，不声称小说生产能力。首轮UNIT有两项被沙箱uv缓存权限阻止；未删改测试，改在沙箱外重跑原始门禁并通过。终态直接断言已在重跑前补强，后续固定版本复核使用最终测试文件。尚需选择一次关键交付的同SHA真实六门CI，再单独做正式验收。未触发远程CI。

隔离复核实际SHA：`1b3326c5447b5450a36ae8a7c63677fd1ea61319`。锁定依赖离线安装、最终81条专项、STATIC、五项治理、原始IMPLEMENT入口、实际架构扫描及demo全部PASS，隔离工作区干净，六个实现/Schema/测试/演示文件与完整本地回归的摘要hash完全一致。未将旧完整回归重新标成此SHA。见 `local-results/EXACT_REPLAY.json`。本地secret-only额外扫描54项全部消费既有精确决定；未重跑依赖漏洞审计，不冒称完整SECRET_DEPENDENCY门禁。
