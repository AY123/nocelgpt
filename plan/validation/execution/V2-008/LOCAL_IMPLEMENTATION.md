# V2-008 本地实现

ADR-004先在b52e8c0固定，再由f2b4c3b登记接受；IMPLEMENT入口PASS后才实现接口。Task与AT只登记IMPLEMENTED；远程六门CI及正式验收未执行，P1/M1仍NOT_VERIFIED。

## 能力

`delta.py`提供四个封闭的v1.0操作：SET_FACT、MARK_UNKNOWN、RETRACT_FACT、NO_CHANGE。现阶段只变更已登记WorldFact的`proposition.value`，不实现任意路径补丁、新建事实或扩展注册框架。值类型从初始事实继承，UNKNOWN不解除类型限制；bool与number区分，null不代表未知/删除/不变。

预演必须由调用方传入事实基线、来源和允许的授权引用，校验项目/分支/parent、事实身份、版本及前值。批量失败不产生部分结果，输入不可变；NO_CHANGE保留版本且changes为空，撤销保留原始事实并进入终态。相同基线重演确定，旧前提不能重放到已变更基线。

Schema封闭四类操作与各层字段；动态基线、外部授权集合、状态转换由领域入口校验。标准JSON Schema不能证明引用真实存在。结构引用不等于实际Permit或正文证据真实性。

## 复现与结果

- `.venv/bin/python -B demo_v2_008.py`：合法事实变更、显式未知/撤销、不变、错类型与过期前提拒绝。
- `.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/test_v2_008.py`：原三条验收断言及跨项目、来源、授权、严格类型、状态转换、原子性、往返和Schema一致性。

最终专项102项、全UNIT928项、ARCH244项通过，0skip；STATIC与五项治理检查PASS。原始本地receipt/JUnit和四个交付文件hash见`local-results/`。首次ARCH入口因新Ruff缓存越界被正确阻断，缓存保留后原门禁通过；未增加忽略或降低检查。

这是内存提议与预演，不是Canon写入、真实Permit、ChangeSet、模型调用或小说生产能力。未改现有知识/事件/Promise模块，无DB/Provider/新增依赖。正式V2-008验收后还需P1汇总，当前不开始P2。
