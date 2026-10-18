# 路线、阶段门禁与里程碑

## 1. 冻结路线

```text
P0 Repository & Governance
→ P1 Narrative Kernel
→ P2 Canon Kernel
→ P3 Genre Kernel
→ P4 Planning & Contracts
→ P5 Context & Model Gateway
→ P6 Single-Chapter Production
→ P7 Quality & Repair
→ P8 Dual-Genre 10-Chapter Certification
→ P9 30-Chapter Certification
→ P10 Genesis & Reference Intelligence
→ P11 Human Calibration / Learning
→ P12 100-Chapter Reliability
→ P13 Reader / Market Feedback
→ P14 300+ Chapter / Million-word Evolution
```

阶段、任务数量和里程碑由机器表生成，详见 [任务视图](generated/PHASE_TASK_REGISTRY.md) 与 [里程碑视图](generated/MILESTONE_MAP.md)。禁止另写不同编号的平行路线。

## 2. Task DAG 与 Phase Gate

任务依赖决定一个任务需要哪些上游产物；阶段 Gate 决定是否允许开始下一阶段。即使 V2-005 的直接任务依赖只有 V2-001，它仍必须等待 G-P0 验证通过。

P0 任务可在执行需要时并行推进，但最终 G-P0 需要四个任务及独立验收证据。P1 以后先满足前一阶段 Gate，再检查本任务依赖与必需 ADR；未满足时不得用“文档已准备好”越级。

## 3. M4 接缝

P6 交付生产编排、抽取和恢复框架，可使用隔离 fixture；G-P6 只确认这些阶段产物。真正的 M4 Single Chapter E2E 必须同时拥有 P7 Q0–Q3、质量聚合和 Permit 集成证据。

因此 M4 在 P7 相关任务后才可能关闭，不能在 P6 用 Mock Gate 宣称生产闭环完成；P7 的进入不依赖 M4 先关闭，避免循环。M5 另外验证补丁修复及回归。

## 4. 不改变关键链

V2-005 → 008 → 009 → 010 → 013 → 017 → 018 → 019 → 020 → 021 → 022～025 → 026 → 033 → 034/035 → 040。

这是能力关键链摘要；真实任务依赖、阶段门禁、并发/恢复/修复等必要旁支均须满足，不能因未列在摘要中就跳过 V2-011/027/028/032/036 等验证。

## 5. 状态读取与历史时点

当前任务、阶段准入和里程碑状态分别读取[任务表](machine/implementation-backlog.yaml)、[阶段门禁](machine/phase-gates.yaml)和[里程碑表](machine/milestones.yaml)，阅读摘要见[实施入口](README.md)及其验收引用。本节保留规划初始状态与历史进度，不另维护一份当前任务清单；某次验收只适用于它绑定的工程修订。

### 规划初始状态（历史）

P0_ENTRY_READY；G-P0～G-P14 和 M0～M12 初始均 NOT_VERIFIED。P13/P14 具体任务未排入首批 60 项。机器资料通过只证明文件一致性，不能把这些状态改成 PASS。

### 2026-10-17 进度记录（历史）

2026-10-17：P0/G-P0和M0已基于611d777原始工程CI及四项任务验收VERIFIED；后续资料与夹具维护不冒称新远程CI。P1仍NOT_VERIFIED，V2-005尚未开始。见 validation/execution/P0/closure-20261017/P0-decision.yaml。
