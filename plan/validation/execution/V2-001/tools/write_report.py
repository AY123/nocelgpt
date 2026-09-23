#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Summarize preserved V2-001 results; does not execute tests or accept closure."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import shlex
import subprocess
import yaml

root = Path.cwd(); base = root / 'plan/validation/execution/V2-001'
baseline = '0089eecc496b0c0b4039fb2b26c186fc437c032e'
implementation = '390aa0f4f28068fdd146fca3eb98df1a5ec1a334'
head = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
branch = subprocess.check_output(['git','branch','--show-current'],text=True).strip()
packet = yaml.safe_load((base / 'execution-packet.yaml').read_text())
tasks = yaml.safe_load((root / 'plan/machine/implementation-backlog.yaml').read_text())['tasks']
old_tasks = yaml.safe_load(subprocess.check_output(['git','show',baseline+':plan/machine/implementation-backlog.yaml'],text=True))['tasks']
assert tasks[0]['status'] == 'IMPLEMENTED' and tasks[1:] == old_tasks[1:]
assert tasks[0]['evidence']['ci'] == tasks[0]['evidence']['acceptance'] == []
assert not (root / '.gitlab-ci.yml').exists()
tracked = subprocess.check_output(['git','diff','--name-status',baseline],text=True).splitlines()
changes = {line.split('\t',1)[1]:line.split('\t',1)[0] for line in tracked}
for path in subprocess.check_output(['git','ls-files','--others','--exclude-standard'],text=True).splitlines():
    changes[path] = 'A'
changes['docs/V2-001_IMPLEMENTATION_REPORT.md'] = 'A'
changes['plan/validation/execution/V2-001/raw/final-scope-review.json'] = 'A'
outside = [p for p in changes if not any(p == a or a.endswith('/') and p.startswith(a) for a in packet['allowed_paths'])]
assert not outside, outside
code_index = json.loads((base / 'artifacts/code-index.json').read_text())
for item in code_index:
    assert hashlib.sha256((root / item['source_path']).read_bytes()).hexdigest() == item['sha256']
scope = dict(status='PASS', baseline=baseline, implementation_revision=implementation,
             reviewed_at=datetime.now(timezone.utc).isoformat(), outside_allowed_paths=outside,
             initial_user_changes=[], other_59_tasks_unchanged=True, p1_features_implemented=False,
             deleted_or_renamed_paths=[p for p,s in changes.items() if s not in {'A','M'}],
             scope='Actual task-specific inspection; not a new V2-003 runner',
             files=[{'path':p,'status':s} for p,s in sorted(changes.items())])
assert scope['deleted_or_renamed_paths'] == []
(base / 'raw/final-scope-review.json').write_text(json.dumps(scope,ensure_ascii=False,indent=2)+'\n')
commands=[]
for path in sorted((base/'raw').glob('*.json')):
    obj=json.loads(path.read_text())
    if 'command' in obj:
        commands.append((path.name, shlex.join(obj['command']).replace('|','\\|'),obj['exit_code']))
lines = [
'# V2-001 Repository Bootstrap 实施报告（非最终验收）','',
'日期：2026-09-23。范围：仅 P0 / V2-001，Plan v1.3.0。结论：**IMPLEMENTED**；本地测试通过，缺远端 CI 与最终验收，未 VERIFIED/CLOSED。','',
'## A. Repository State','',
f'- Branch：`{branch}`；本报告生成时 HEAD：`{head}`。',
f'- 开工基线：`{baseline}`，初始已跟踪修改和未跟踪文件均为空；实施原文提交：`{implementation}`。',
'- 正式测试开始前实现源码已提交；运行中新增加的是结果文件，源码无修改。当前归档阶段 dirty 来自证据指针、快照及本报告；最终证据归档提交与被测实现提交区分。交付时 HEAD/工作区由最终 Git 检查给出。',
'- `.venv`、`dist/tools`、`dist/cache` 是忽略的本地环境，不是源码；原工具配置未编辑，没有覆盖用户已有修改，没有远端 push。','',
'## B. V2-001 Status','',
'已按 OPEN → IN_PROGRESS → IMPLEMENTED 推进。代码/配置、真实本地测试、正式 ADR 和 CODE/TEST_RESULT 已存在；`ci: []`、`acceptance: []` 保持真实。AT-V2-001 套件记录 IMPLEMENTED 和本地结果，不提前声明 P0 完成。其余 59 任务仍 OPEN，G-P0/M0 状态未改变。','',
'## C. ADR-001','',
'决定 CPython 3.12.14、uv 0.12.17、uv_build 0.12.17、PostgreSQL 17.11 bookworm + digest；精确 `.python-version`、`requires-python`、uv required-version 与唯一 lock。以临时 Compose project、回环随机端口、tmpfs 和一次性凭证隔离测试。','',
'- [正式决定原文](../plan/decisions/ADR-001_RUNTIME_AND_LOCKING.md)，源提交 `4b60312c487ad090adddca94e08e74982404e065`。',
'- [ACCEPTED decision record](../plan/validation/execution/V2-001/adr-001-decision.yaml)，先于 IMPLEMENT 开工校验。',
'- SQLAlchemy 2.x / psycopg 3 用于实际数据库测试；Pydantic / Alembic 待真实消费者出现，不提前安装业务框架。','',
'## D. Files Changed','',
'工程文件：`pyproject.toml`、`uv.lock`、`.python-version`、`compose.yaml`、`.env.example`、`src/anovel/__init__.py`、`scripts/check_postgres.py`、两份 `tests/integration/` 测试、根 README 和资料迁移说明。规划支持修改仅任务/ADR/套件状态与证据、入口状态文字、派生视图/manifest 及 4 行隔离测试夹具修正。执行目录保存真实输入快照、失败历史与结果；不是新增业务或通用治理框架。','',
'逐文件 A/M 清单见报告末尾；[机器清单](../plan/validation/execution/V2-001/raw/final-scope-review.json)可核对全部路径。没有删除或重命名用户文件。','',
'## E. Commands Executed','',
'下面列出任务录制器保存的真实命令及退出码（早期失败保留）。读取/比对和 Git 提交操作另在 Git 历史与 preflight 中核对；正式编号 025–032 均记录被测实现 revision。`python3` / `.venv/bin/python3` 的环境区别在原始日志中保留。','',
'| 原始记录 | 命令 | Exit |','|---|---|---:|',
]
for name, command, code in commands:
    lines.append(f'| [{name}](../plan/validation/execution/V2-001/raw/{name}) | `{command}` | {code} |')
lines += ['',
'## F. Test Results','',
'| 状态 | 项目 | 真实结果 |','|---|---|---|',
'| PASS | 锁定安装、导入、pytest discovery | 固定版本安装成功；发现 15 项测试；新虚拟环境非 editable 安装和 wheel 独立导入通过 |',
'| PASS | 工程验收 | 15 passed，0 failed / errors / skipped，含 5 项仓库和 10 项 PostgreSQL |',
'| PASS | 规划校验 | 实现提交上的检查通过；证据指针归档后再次通过 |',
'| PASS | validator self-test | 32 项 |',
'| PASS | governance regression | 39 项 |',
'| PASS | AI execution regression | 36 项 |',
'| FAIL（历史已修复） | 002 / 004 / 008 / 016 | 快照 Markdown 相对引用、Docker 沙箱权限、PyPI 网络沙箱、继承 live ADR 的负例夹具。失败原始结果未删除 |',
'| FAIL（归档补齐） | 036 | `.env.example.txt` 快照被原有 ignore 规则忽略；只将这个无真实凭证的样例快照显式纳入 Git，不扩大 ignore 例外或改变门禁 |',
'| UNKNOWN | 远端 runner、保护配置、其他平台 | 本任务未核验，不能由 macOS arm64 推定 Linux amd64 成功 |',
'| NOT_RUN | GitLab CI、安全/依赖流水线、完整架构 harness | 属于 V2-003 / V2-004，未开始 |',
'| NOT_RUN | P1+、Provider、章节/读者/市场认证 | 超出任务，未调用或实现 |','',
'最初一次 inline 准备脚本在 Python 解析阶段因编码失败，未执行修改；随后的 baseline PASS 不曾被当作正式执行包通过。正式 packet 通过有独立后续记录。原始 `.md` 快照移为 `.txt` 容器、字节不变，以避免将原文相对链接误按新目录解析；没有扩大 validator 扫描排除。','',
'夹具修正的原要求是“未接受 ADR 拒绝 IMPLEMENT”。真实 ADR 接受后，旧测试继承其状态，未建立负例前提，36 项中 1 项失败；已先说明问题和影响，再仅在 setUp 将隔离 ADR 设为 REQUIRED。所有拒绝/放行断言、validator、门禁、阈值和验收均未削弱。理由见 [fixture-correction-rationale](../plan/validation/execution/V2-001/raw/fixture-correction-rationale.json)。','',
'## G. PostgreSQL Evidence','',
'镜像：`postgres:17.11-bookworm@sha256:639ab7ceb90e13123085b741fb31ef493fba25463002f6da665352e7b534b652`；实测 Linux arm64，Docker 29.4.0 / Compose 5.1.2。数据库返回 `server_version_num=170011`、`database=bootstrap_test`，驱动 `postgresql+psycopg`。','',
'正式运行项目 `anovel-v2001-413b612124824f0c`（正常连接）和 `anovel-v2001-22964ddefea04592`（注入 consumer 异常）均清理成功，逐项目确认 containers/networks/volumes=0。两个独立连接的 backend PID 不同，public schema 无业务表。缺失配置、SQLite/错误驱动、不可连接端口均明确失败；测试使用一次性凭证。','',
'[正式原始输出](../plan/validation/execution/V2-001/raw/028_formal_pytest.json)及 [JUnit XML](../plan/validation/execution/V2-001/checks/formal/pytest.xml)。探针没有业务迁移；本任务不宣称 CAS/fencing/备份认证。SIGKILL/宿主掉电仍需按输出的精确 project name 清理，操作见根 README。','',
'## H. Plan / Governance Results','',
f'活动包 manifest：`{packet["plan_manifest_sha256"]}`；[证据绑定后检查](../plan/validation/execution/V2-001/checks/evidence-bound/plan-validation.json)为 PASS。此为结构和本地证据核验，不是远端真实性证明。','',
'[CODE](../plan/validation/execution/V2-001/code-evidence.yaml)、[工程 TEST_RESULT](../plan/validation/execution/V2-001/test-result.yaml)、[治理 TEST_RESULT](../plan/validation/execution/V2-001/governance-result.yaml)均绑定实际实现提交，引用真实输出与 SHA-256。CODE 快照与 Git blob/现场源码逐字节比对。ADR 保留自身历史 revision；没有把后续证据归档提交冒称为被测实现。','',
'## I. Remaining Blockers','',
'V2-001 的最终 closure 被缺失的真实 CI_RUN 和 ACCEPTANCE_RECORD 阻断。V2-002 仍须工程化接入执行治理；V2-003 仍须完整架构/差异/防降标 harness；V2-004 仍须可信 GitLab CI、Secret/依赖门禁、项目和 revision 核验、实际保护/权限检查。全部仍 OPEN。','',
'以下是本次责任交接，不是 FINDING_CLOSURE 或最终验收：','',
'| Finding | 本次已有依据 | 剩余责任 |','|---|---|---|',
'| AR-06 / RR-04 | 真实执行包、状态历史、输入 hash、代码/测试证据 | V2-002～004 的正式工程接入与可信关闭链 |',
'| AR-17 / CA-17 / RR-09 | 固定安装、真实 PostgreSQL、失败负例 | V2-003/004 架构、安全与真实 CI；Provider 在其适用后续阶段 |',
'| AR-18 | 最小环境、隔离测试和证据记录 | V2-004 权限；V2-009/010/019 等持久化、调用、恢复义务 |',
'| CA-19 | 缺配置/依赖失联明确失败、PG 版本检查 | V2-012 重建与 V2-058 长期备份/恢复认证 |','',
'这些 finding 仍 OPEN_TRACKED；没有删除整改义务或把部分履行记为解决。','',
'## J. Scope Check','',
'与初始基线比较并核对 packet.allowed_paths：全部实际修改在任务允许范围。唯一生产包文件为 `src/anovel/__init__.py`；无 Character/Canon/Genre/Workflow/模型调用、自动生成或发布。没有开始 V2-002～004；既有治理脚本仅修正一处负例测试前提。AI 子代理代码复核无具体阻断项，但与主实施者处于相同信任边界，不冒称独立人类审核。','',
'## K. Next Recommended Task','',
'建议下一项为 **V2-002 — Normative documentation index**。本次在 V2-001 IMPLEMENTED 停止，未自动启动下一任务；P0 未验证前不开始 V2-005。','',
'## 附：逐文件改动清单','',
'A 为新增，M 为修改；多数新增文件是按执行协议保存的输入快照及原始证据。清单为报告生成时刻；其后的任务校验日志同样留在 execution/V2-001。','',
]
lines.extend(f'- `{status}` `{path}`' for path,status in sorted(changes.items()))
(root/'docs/V2-001_IMPLEMENTATION_REPORT.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'report':'docs/V2-001_IMPLEMENTATION_REPORT.md','files':len(changes),'commands':len(commands),'status':'IMPLEMENTED'}))
