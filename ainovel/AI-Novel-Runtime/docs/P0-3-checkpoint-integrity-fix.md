# P0-3: 100章运行证据不完整 - 诊断与修复方案

**日期**: 2026-08-18  
**问题**: RUN-00040 的checkpoint数据存在多处异常

---

## 问题清单

根据核验报告，RUN-00040存在以下问题：

### 1. 第50章checkpoint缺失关键字段
- ❌ 缺少 `draft_hash` / `final_hash`
- ❌ 缺少 `m7` 数据
- ❌ 缺少 `quality_snapshot`

### 2. 状态hash长时间不变
- 多个checkpoint的 `state_hash` 完全相同
- 表明状态可能没有正确更新

### 3. Event ID重复
- 多个checkpoint的 `event_id` 重复为 `EVT-00033`
- 违反了每章消费不同事件的预期

### 4. 商业裁决全为null
- 所有checkpoint的 `commercial_verdict` 为 `null`
- 即使有商业循环，也没有记录verdict

---

## 根本原因分析

### Checkpoint生成机制

**正常流程** (`runtime/serialize/loop.py:2583-2598`):
```python
if c.spec.index in CHECKPOINT_INDICES:  # 10, 20, 30, ...
    checkpoint = build_checkpoint(
        chapter_index=c.spec.index,
        chapter_id=c.spec.task_id,
        event_id=c.spec.event_id,
        draft_hash=c.draft_hash,        # ← 来自ChapterRun
        state_hash=c.state_hash,        # ← 来自ChapterRun
        final_hash=...,                  # ← 来自c.m5_final
        verdict=c.verdict,
        commercial_verdict=c.commercial_verdict,
        quality_snapshot=c.quality_snapshot,
        m7=c.m7,
    )
    # 写入 registry/derived/serial-checkpoints/cp-XXX.json
```

**关键依赖**: Checkpoint完全依赖 `ChapterRun` 对象的字段

### 可能的失败模式

#### 失败1: 章节生成失败但checkpoint仍写入
```python
# 如果章节在某个阶段失败（c.ok = False）
if not c.ok:
    # draft_hash, m7等可能为None
    pass

# 但checkpoint仍然在写入
if c.spec.index in CHECKPOINT_INDICES:
    checkpoint = build_checkpoint(
        draft_hash=None,  # ❌ 缺失
        m7=None,          # ❌ 缺失
        ...
    )
    # 仍然写入文件
```

**问题**: 没有检查 `c.ok` 就写入checkpoint

#### 失败2: 状态更新失败但没有检测
```python
# 状态应该在每章更新
new_state = project_state(facts_up_to_event)
new_state_hash = hash(new_state)

# 如果状态投影失败
if projection_error:
    # state_hash可能保持不变
    c.state_hash = last_state_hash  # 重复
```

#### 失败3: Event消费记录丢失
```python
# 每章应该消费一个新事件
c.spec.event_id = next_event_id

# 如果事件队列耗尽或索引错误
if no_more_events:
    c.spec.event_id = last_event_id  # 重复EVT-00033
```

#### 失败4: Commercial verdict从未写入
```python
# loop.py 中有commercial优化逻辑
if simulator and rewrite_model:
    commercial_result = optimize_commercial(...)
    c.commercial_verdict = commercial_result.verdict

# 但是：
# 1. 可能simulator/rewrite_model未提供
# 2. commercial_result没有verdict字段
# 3. 赋值后被覆盖为None
```

---

## 诊断步骤

### Step 1: 检查RUN-00040是否真实存在

由于报告提到RUN-00040，但我们在测试fixtures中只找到RUN-00001到RUN-00006，需要：

1. 查找真实项目目录
2. 检查是否有RUN-00040或更高编号的运行
3. 加载该运行的manifest和checkpoint

### Step 2: 验证checkpoint完整性

对于每个checkpoint，检查：
```python
def validate_checkpoint(cp: dict) -> List[str]:
    issues = []
    
    # 必须字段
    if not cp.get("draft_hash"):
        issues.append("missing draft_hash")
    if not cp.get("final_hash"):
        issues.append("missing final_hash")
    if not cp.get("m7"):
        issues.append("missing m7")
    if not cp.get("quality_snapshot"):
        issues.append("missing quality_snapshot")
    
    return issues
```

### Step 3: 检查state_hash变化率
```python
state_hashes = [cp["state_hash"] for cp in checkpoints]
unique_count = len(set(state_hashes))
if unique_count < len(state_hashes) * 0.8:
    # 超过20%重复 → 状态更新问题
    print("state_hash repetition detected")
```

### Step 4: 检查event_id唯一性
```python
event_ids = [cp["event_id"] for cp in checkpoints]
duplicates = [e for e in event_ids if event_ids.count(e) > 1]
if duplicates:
    print(f"duplicate event_ids: {set(duplicates)}")
```

---

## 修复方案

### 修复A: 添加checkpoint完整性验证（推荐）

**在写入checkpoint前验证ChapterRun**:

```python
# runtime/serialize/loop.py, ~line 2579

if c.spec.index in CHECKPOINT_INDICES:
    # P0-3: 验证checkpoint完整性，缺失关键字段时警告
    incomplete_fields = []
    if not c.ok:
        incomplete_fields.append("chapter_failed")
    if not c.draft_hash:
        incomplete_fields.append("draft_hash")
    if not c.m5_final or not c.m5_final.get("final_hash"):
        incomplete_fields.append("final_hash")
    if not c.m7:
        incomplete_fields.append("m7")
    if not c.quality_snapshot:
        incomplete_fields.append("quality_snapshot")
    
    if incomplete_fields:
        print(f"  ⚠️  checkpoint cp-{c.spec.index:03d} incomplete: "
              f"missing {', '.join(incomplete_fields)}")
    
    # 仍然写入（audit目的），但标记不完整
    checkpoint = build_checkpoint(
        # ... 正常逻辑
    )
    # 可选：添加completeness字段
    if incomplete_fields:
        checkpoint["_incomplete"] = incomplete_fields
    
    # 写入
    derived.write_artifact(...)
```

### 修复B: 状态hash验证

```python
# 在状态更新后验证
prev_state_hash = last_state_hash
new_state_hash = c.state_hash

if prev_state_hash and new_state_hash == prev_state_hash:
    print(f"  ⚠️  ch{c.spec.index} state_hash unchanged "
          f"(possible projection failure)")
```

### 修复C: Event消费追踪

```python
# 维护已消费事件集合
consumed_events = set()

for c in running_chapters:
    if c.spec.event_id in consumed_events:
        print(f"  ⚠️  ch{c.spec.index} reusing event {c.spec.event_id}")
    consumed_events.add(c.spec.event_id)
```

### 修复D: Commercial verdict确保写入

```python
# 在commercial优化后确保verdict写入ChapterRun
if commercial_result:
    c.commercial_verdict = commercial_result.get("verdict")
    if not c.commercial_verdict:
        # 降级：没有verdict时记录原因
        c.commercial_verdict = "no_verdict"
```

---

## 立即行动

### 优先级P0（立即执行）
1. ✅ 添加checkpoint完整性验证（修复A）
2. ✅ 添加状态hash重复检测（修复B）
3. ✅ 添加event重复检测（修复C）

### 优先级P1（短期）
4. 调查RUN-00040的真实位置
5. 运行5章测试验证修复
6. 回填missing checkpoints（如果需要）

### 优先级P2（中期）
7. 建立checkpoint自动验证工具
8. 添加checkpoint diff比较
9. 完整性报告集成到dashboard

---

## 测试计划

### 单元测试
```python
def test_checkpoint_validation():
    """测试checkpoint完整性验证"""
    incomplete_chapter = ChapterRun(
        spec=...,
        ok=False,
        draft_hash=None,  # 缺失
        m7=None,          # 缺失
        ...
    )
    
    # 应该检测到不完整
    issues = validate_chapter_for_checkpoint(incomplete_chapter)
    assert "draft_hash" in issues
    assert "m7" in issues
```

### 集成测试
```python
def test_5ch_checkpoints_complete():
    """运行5章，验证第10章checkpoint完整"""
    result = run_serial(max_chapters=10, ...)
    
    cp = load_serial_checkpoint(project, 10)
    assert cp is not None
    assert cp["draft_hash"]
    assert cp["final_hash"]
    assert cp["m7"]
    assert cp["quality_snapshot"]
```

---

## 预期效果

**修复前**:
- ❌ 第50章checkpoint缺字段，静默写入
- ❌ state_hash重复，未检测
- ❌ event_id重复，未警告
- ❌ commercial_verdict全null，原因不明

**修复后**:
- ✅ 缺失字段写入前警告
- ✅ state_hash重复实时检测
- ✅ event_id重复立即警告
- ✅ commercial_verdict缺失有日志
- ✅ checkpoint带completeness标记

---

## 下一步

1. [ ] 实施修复A-D
2. [ ] 添加验证测试
3. [ ] 运行5章集成测试
4. [ ] 查找并分析RUN-00040
5. [ ] 更新文档
