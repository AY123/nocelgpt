# V2-010 工程验收

V2-010 CLOSED。验收代码 `16259d148ac33c5578b40d0221f7f70d7ca55dc4`；GitHub [run42632232950](https://github.com/AY123/nocelgpt/actions/runs/42632232950)，同SHA六门全部PASS。UNIT1099 + ARCH244 + PostgreSQL117 = **1460项，0失败/错误/skip**。PG含V2-010的57项、V2-009的59项及原服务1项；85项模型/收据契约为UNIT子集，不重复计算。六个原始ZIP、GitHub digest、receipt源码/lock身份、命令日志、完整产物hash和JUnit已实际读取核验。实施与验证为同一操作者，不冒称独立人员审计。

五条原验收均PASS：无授权或无有效Permit拒绝；真实事务故障无半写入且HEAD/event/receipt一致；完整历史正文/Delta/依赖/Permit可读；已接受正文UPDATE/DELETE拒绝；取消先胜拒绝旧许可，提交先胜返回原收据。逐项测试映射见SCENARIO_RESULTS.json。

本次只在已恢复额度后触发一个关键验收run，无自动重试。此前run39747798274计费拒绝启动、旧3ac运行及本地失败保留原语义，不拼接新旧结果。安全修复分别更新certifi至2026.10.19及filelock至4.2.1；新run实际完整安全PASS：54项精确消费，0新增/未匹配/未使用，51包0漏洞。54项finding仍OPEN，批准期限及范围不变，无宽泛忽略或门禁降级。

## 工程边界

现有唯一CanonCommitService具备有限事实章节提交、独立受控TEST issuer、持久化精确Permit、不可变完整证据及同事务commit/event/receipt/HEAD。默认生产拒绝TEST Permit；可信应用负责actor身份与管理engine隔离。

这不证明P7生产issuer/Q0–Q3、网络认证、模型/小说生产闭环或生产备份已完成。V2-011（并发CAS、幂等冲突、提交成功响应丢失）和V2-012（完整事件重建）仍OPEN，P2/G-P2/M2仍NOT_VERIFIED。12项跨任务finding均仅部分解决；EXT-006仅本任务审阅/改稿失效/不可变正文部分，其余Workflow/UI仍待做。承载有价值数据前仍须完成早期隔离备份恢复。

此后结项提交只修改状态、证据、导航和生成视图，CODE_MANIFEST证明实际业务字节不变；结项提交不是上述CI受测SHA，不为文档登记再触发CI。下一主任务：V2-011。
