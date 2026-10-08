# V2-004-P0-MAINLINE-UNBLOCK-001 — Direct Human Authorization

Record role: transcription of the latest direct human task instruction in this conversation. It is neither a new Owner credential attestation nor a secret exception approval. The author is the human user; the implementer records the instruction. Recording time is not the time an approval or service event occurred.

## Verbatim task instruction

```text
TASK:
V2-004-P0-MAINLINE-UNBLOCK-001

MISSION:
用一次有边界的工程收口解除 P0 阻塞，
随后立即返回产品能力主线。

RULES:

1. 停止所有 H2/H3/H4 credential evidence acquisition。
   不再要求：
   - key 截图
   - 删除事件日志
   - 服务端时间
   - credential ownership 补证
   - historical key 调查

2. 保留现有 evidence，仅作为历史记录。
   不删除、不伪造 CLOSED。

3. 对当前已经识别的历史 finding 建立严格、机器可验证的
   finding-specific disposition / exception mechanism。

4. Exception 必须 EXACT MATCH，至少绑定：
   - finding identity
   - scanner rule
   - repository/path identity
   - worktree/history scope
   - applicable revision/baseline
   - authority record

5. 严禁：
   - global gitleaks ignore
   - rule-wide suppression
   - path-wide suppression
   - filetype-wide suppression
   - allow_failure
   - secret gate deletion
   - “发现数量 <= 45 就 PASS”
   - 对未来新增 finding 自动放行

6. 任意：
   - 新 finding
   - unmatched finding
   - malformed exception
   - unauthorized exception
   - identity mismatch
   必须 FAIL CLOSED。

7. 给现有 38 个非 Owner finding 使用严格 exact disposition。
   对 Owner 已明确声明不再作为项目主线处理的历史 credential
   finding，只设计单一 Owner risk-acceptance 输入，
   不再逐项索要 credential 证据。

8. 保持：
   STATIC
   SCHEMA_CONTRACT
   UNIT
   ARCH_FITNESS
   POSTGRES_ENV
   SECRET_DEPENDENCY
   六门均为 mandatory / allow_failure=false。

9. 增加正负测试：
   - exact approved finding → consumed
   - new secret → FAIL
   - changed path → FAIL
   - changed fingerprint → FAIL
   - history/worktree mismatch → FAIL
   - missing authority → FAIL
   - malformed approval → FAIL
   - unused approval → report
   - additional finding → FAIL

10. 不运行远程 CI。
    不修改 GitLab 设置。
    不启动 runner。
    不 push。
    先完成本地 implementation + tests + exact diff report。

11. 输出：
    - implementation diff
    - exception-consumer schema
    - approval/disposition schema
    - negative-test matrix
    - local test results
    - remaining blockers
    - 是否具备 final trusted-CI candidate 条件

12. 完成后 STOP，交给独立审核。

SUCCESS CONDITION:

不是“45 个 finding 消失”。

而是：

KNOWN_FINDINGS = explicitly accounted for
NEW_OR_UNMATCHED_FINDINGS = fail closed
SECRET_GATE = still mandatory
NO_BROAD_BYPASS = true
P0_FINAL_CANDIDATE = ready for independent review
```

## Authorization limits

- This is a V2-004 / P0 local engineering sub-work-package, not a new backlog task or P1 admission.
- IMPLEMENT is expressly authorized here; it is not relabeled as PREPARE.
- Existing 29 worktree differences, old canonical disposition, H1/H2/H3/H4 evidence and trusted-execution evidence are preserved.
- No additional credential evidence acquisition is authorized or required by this task.
- This instruction authorizes implementation and testing of exact exceptions. It does not supply machine-readable approval of the 38 requests or an executed risk acceptance for the 7 historical credential findings.
- The single Owner risk-acceptance input is designed for the exact fixed set; do not infer service revocation, ownership evidence, finding closure, future authorization, or an unbounded exemption from the human instruction.
- No remote CI, GitLab mutation, runner activation, paid Provider call, Git commit/push/MR, secret-gate weakening, or broad scanner suppression is authorized.
- STOP after local implementation, tests and exact diff reporting; independent review and final trusted-CI acceptance remain separate.
