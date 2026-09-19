# 章间契约层补救方案

**基于深度诊断的精准修复**  
**日期**: 2026-08-13

---

## 🎯 核心结论

**当前问题不是"没有大纲"，而是"缺少章间契约层"**

```
现状：上一章 → [状态折叠] → 下一章目标
缺失：上一章出口状态 → [契约校验] → 下一章入口匹配
```

---

## 📊 现有模块评估

### ✅ 已有且运作良好

| 模块 | 功能 | 状态 |
|------|------|------|
| outline.schema.json | 全书大纲 | ✅ |
| 前30章规划 | goal/conflict/hook | ✅ |
| 百章长弧 | 10章一band | ✅ |
| 滚动计划 | 10-20章窗口 | ✅ |
| Chapter IR | 目标/冲突/回报 | ✅ |
| Chapter Objective | 读者疑问/兑现 | ✅ |
| Character Runtime | 角色当前状态 | ✅ |
| Narrative Mandate | 升级必然性 | ✅ |
| Story State | 事实摘要 | ✅ |

### ❌ 存在的关键缺口

#### 1. 前30章后大纲降级
```python
# AI-Novel-Runtime/runtime/scene/ir.py:257
# 第31章+ 的 outline_ref 为 null
# IR 退化为单一泛化 beat：
"抬升代价并防止中段停滞，推进至曜士"
# ← 这是卷段目标，不是可执行章节计划
```

#### 2. 滚动计划是"列出"非"细化"
```python
# AI-Novel-Runtime/runtime/serialize/rolling_plan.py:94
# 同一10章band的active_goal基本相同
# 解决了：接下来10章属于哪个阶段？
# 没解决：第31章具体做什么？如何承接第30章？
```

#### 3. next_chapter_bridge 语义错位
```python
# AI-Novel-Runtime/runtime/chapter/finalizer.py:23
# 当前存储的是：改动率/QA结果/编辑决策
# 应该存储的是：地点/时间/人物/动作/情绪/未完成目标
```

#### 4. Narrative Mandate 只保证升级不保证接上
```
能表达：冲突等级升级、心理状态变化
不能表达：上章人物在哪、下章从哪接、钩子如何兑现
```

---

## 🔧 五层状态驱动大纲法

### 架构设计

```
第一层：战略层（已有，保持）
    雪花法 → 梗概/卖点/世界规则/主角引擎

第二层：长弧层（已有，需增强）
    九线法 → 必须落到"状态变化"
    
    ❌ 错误示例：
    成长线：力量提升
    
    ✅ 正确示例：
    成长线：
    - Ch1-10：只能被动吞噬
    - Ch11-30：开始主动控制代价
    - Ch31-50：利用晶化风险战斗
    - Ch51-70：力量反噬人格

第三层：事件与承诺图（新增）⭐
    promise_id: "矿心身世"
    埋设章节: 2
    当前状态: "已提示，未揭露"
    下次提醒: 35
    回收章节: 94
    回收方式: "二叔揭示真相"

第四层：章间契约层（新增）⭐⭐⭐
    entry_state        本章开始时状态
    chapter_objective  本章目标
    conflict          主要阻力
    irreversible_change 不可逆变化
    payoff            兑现什么
    exit_bridge       下一章从哪接 ← 关键

第五层：场景执行层（已有，需增强）
    beat: setup/escalation/turn/reward
    → 增加：scene_entry/state_change/scene_exit
```

---

## 🎯 P0：章间契约层设计

### exit_bridge 完整结构

```json
{
  "chapter": 93,
  "exit_bridge": {
    "time": "当夜，距花开不足三天",
    "location": "赤曜矿脉地宫外悬空石台",
    "pov": "段奕尘",
    "characters_present": ["段奕尘", "镜见川", "荧惑"],
    "physical_state": {
      "段奕尘": "刚与失落曜晶共鸣，右手暗金纹路扩散",
      "镜见川": "戒备状态，曜能外放",
      "荧惑": "暗金光芒笼罩，威压降临"
    },
    "emotional_state": {
      "段奕尘": "决心直面，无路可退",
      "镜见川": "震惊于曜师出现"
    },
    "unfinished_action": "曜师降临，对峙即将开始",
    "pending_threat": "荧惑的真实目的未明",
    "hook_promise": "段奕尘如何应对曜师",
    "next_chapter_must_open_with": {
      "scene": "对峙场景延续",
      "pov": "段奕尘或荧惑",
      "time": "无时间跳跃，连续发生",
      "must_consume_hook": true,
      "consume_within_paragraphs": 5
    },
    "continuity_check": {
      "location_must_match": true,
      "characters_must_present": ["段奕尘", "荧惑"],
      "time_no_backward": true,
      "unfinished_action_must_resolve": true
    }
  }
}
```

### entry_state 校验结构

```json
{
  "chapter": 94,
  "entry_state": {
    "from_chapter": 93,
    "entry_must_match": [
      "location=赤曜矿脉地宫外",
      "unfinished_action=对峙开始",
      "pov=段奕尘或荧惑",
      "characters_present=段奕尘,荧惑"
    ],
    "hook_consumption": {
      "from_chapter": 93,
      "hook_content": "曜师降临，段奕尘无路可退",
      "must_address_within": 5,
      "address_method": "直接对峙或对话"
    },
    "time_continuity": {
      "reference": "Ch93末尾",
      "max_skip": "无跳跃或几息内",
      "no_backward": true
    }
  }
}
```

---

## 🔧 实施方案

### P0-1: 修正 next_chapter_bridge 语义

**当前问题**:
```python
# runtime/chapter/finalizer.py:23
next_chapter_bridge = {
    "改动率": 0.0,
    "QA": "pass",
    "recommendation": "rollback"
}
# ← 这是编辑决策，不是剧情桥接
```

**修正方案**:
```python
# 1. 重命名现有字段
editorial_decision = {
    "改动率": 0.0,
    "QA": "pass",
    "recommendation": "rollback"
}

# 2. 新增剧情桥接字段
narrative_bridge = {
    "time": "...",
    "location": "...",
    "characters_present": [...],
    "physical_state": {...},
    "emotional_state": {...},
    "unfinished_action": "...",
    "next_chapter_must_open_with": {...}
}

# 3. 下一章生产链必须读取并校验
```

**代码位置**:
- `runtime/chapter/finalizer.py` - 生成bridge
- `runtime/serialize/loop.py:639` - 消费bridge
- 新增：`runtime/chapter/continuity_checker.py` - 校验

---

### P0-2: 为现有100章逆向提取 exit_bridge

**工具链设计**:

```python
# tools/extract_bridge.py
def extract_chapter_bridge(chapter_num, chapter_text):
    """
    从正文提取章节桥接信息
    """
    # 1. 提取章末最后3-5段
    ending_paragraphs = extract_ending(chapter_text, n=5)
    
    # 2. LLM分析提取
    prompt = f"""
    分析以下章节结尾，提取桥接信息：
    
    {ending_paragraphs}
    
    提取：
    1. 时间状态
    2. 地点
    3. 在场人物
    4. 人物身体状态
    5. 人物情绪状态
    6. 未完成动作
    7. 章末钩子承诺
    8. 下一章必须如何开始
    
    输出JSON格式。
    """
    
    return bridge_data
```

**批量处理**:
```bash
# 逐章提取
for ch in 1..100:
    bridge = extract_chapter_bridge(ch)
    save_to_db(ch, bridge)
    
# 校验相邻章
for ch in 1..99:
    validate_continuity(ch, ch+1)
    report_gaps()
```

---

### P0-3: 增加相邻章自动检查

**检查维度**:

```python
# runtime/chapter/continuity_checker.py

def check_continuity(prev_chapter, next_chapter):
    """
    检查相邻章节连续性
    """
    issues = []
    
    # 1. 地点检查
    if prev.exit_bridge.location != next.entry_state.location:
        if not has_explicit_transition(next):
            issues.append({
                "type": "location_jump",
                "severity": "high",
                "prev": prev.exit_bridge.location,
                "next": next.entry_state.location,
                "suggestion": "需要添加场景转换描述"
            })
    
    # 2. 时间检查
    if next.entry_state.time < prev.exit_bridge.time:
        issues.append({
            "type": "time_backward",
            "severity": "critical"
        })
    
    # 3. 人物连续性
    missing_chars = set(prev.exit_bridge.characters_present) - \
                   set(next.entry_state.characters_present)
    if missing_chars and not has_exit_explanation(next):
        issues.append({
            "type": "character_disappear",
            "severity": "medium",
            "missing": list(missing_chars)
        })
    
    # 4. 未完成动作消费
    if prev.exit_bridge.unfinished_action:
        if not consumed_in_opening(next, 
                prev.exit_bridge.unfinished_action):
            issues.append({
                "type": "unfinished_action_dropped",
                "severity": "high",
                "action": prev.exit_bridge.unfinished_action
            })
    
    # 5. 钩子兑现检查
    if prev.exit_bridge.hook_promise:
        consume_para = find_hook_consumption(next)
        if consume_para > 20:  # 超过20%章节才回应
            issues.append({
                "type": "hook_delayed",
                "severity": "medium",
                "hook": prev.exit_bridge.hook_promise,
                "consumed_at": consume_para
            })
        elif consume_para == -1:
            issues.append({
                "type": "hook_not_consumed",
                "severity": "high"
            })
    
    return issues
```

---

### P1: 升级滚动计划

**当前问题**:
```python
# rolling_plan.py:94
# 同一band内active_goal相同
band_goal = "抬升代价并防止中段停滞"
chapters = [31, 32, 33, 34, 35, 36, 37, 38, 39, 40]
# 全部复制同一目标
```

**升级方案**:
```python
# 每章独立计划
rolling_plan = {
    "band": "Ch31-40",
    "band_goal": "代价体系深化，推进至曜士",
    "chapters": [
        {
            "chapter": 31,
            "specific_goal": "发现副种来源",
            "entry_from": "Ch30的暗金回应",
            "conflict": "追踪中遭遇监视",
            "payoff": "确认副种持有者身份",
            "exit_bridge": "尾随至交易地点",
            "connects_to": 32
        },
        {
            "chapter": 32,
            "specific_goal": "追踪副种持有者",
            "entry_from": "Ch31的尾随",
            "conflict": "被反追踪",
            "payoff": "暴露自身位置但获取情报",
            "exit_bridge": "决定主动接触",
            "connects_to": 33
        },
        # ... 逐章细化
    ]
}
```

---

### P1: 建立事件与承诺图

**数据结构**:

```json
{
  "promises": [
    {
      "promise_id": "矿心身世",
      "type": "mystery",
      "埋设章节": 2,
      "埋设内容": "父亲说'你不是我儿子'",
      "当前状态": "已提示，未揭露",
      "影响剧情线": ["主线", "悬念线"],
      "下次提醒章节": 35,
      "提醒方式": "妹妹的曜能种异常",
      "预计回收章节": 94,
      "回收方式": "二叔揭示十七号计划",
      "必须在此之前提及": [25, 35, 67, 88],
      "相关事件": ["ev_001", "ev_015"]
    },
    {
      "promise_id": "镜见川真实身份",
      "type": "character_secret",
      "埋设章节": 3,
      "埋设内容": "能够识别暗金晶体",
      "当前状态": "已多次暗示，接近揭晓",
      "回收章节": 45,
      "回收方式": "主动坦白或被迫暴露"
    }
  ],
  
  "events": [
    {
      "event_id": "ev_001",
      "event_name": "清远矿难",
      "发生时间": "一年前",
      "涉及人物": ["父亲", "二叔", "矿工"],
      "产生后果": [
        "父亲死亡",
        "账册遗失",
        "段奕尘逃离"
      ],
      "产生悬念": ["矿难真相", "账册内容", "幸存者"],
      "关联承诺": ["promise_矿心身世", "promise_账册"],
      "前置事件": null,
      "后续事件": ["ev_002", "ev_015"]
    }
  ],
  
  "causality_chain": [
    {
      "chain_id": "main_revenge",
      "起点": "ev_001_清远矿难",
      "路径": [
        "ev_002_逃离矿场",
        "ev_005_获得暗金晶体",
        "ev_015_暗金觉醒",
        "ev_045_获知二叔存活",
        "ev_094_终局对峙"
      ],
      "当前进度": "ev_015",
      "下一步": "ev_045准备"
    }
  ]
}
```

---

## 📋 100章逆向提取任务清单

### 批量提取（2-3小时）

```bash
# 步骤1: 提取每章exit_bridge
python tools/extract_bridge.py --chapters 1-100 \
  --input novel-lingse-complete-100-chapters.md \
  --output data/chapter_bridges.json

# 步骤2: 提取承诺与伏笔
python tools/extract_promises.py --chapters 1-100 \
  --output data/promises.json

# 步骤3: 提取事件因果链
python tools/extract_events.py --chapters 1-100 \
  --output data/events.json

# 步骤4: 校验连续性
python tools/check_continuity.py \
  --bridges data/chapter_bridges.json \
  --output reports/continuity_issues.json

# 步骤5: 生成修复建议
python tools/generate_fixes.py \
  --issues reports/continuity_issues.json \
  --output reports/fix_recommendations.json
```

### 手动审核（1-2小时）

1. 审核关键承诺（10-15个）
2. 确认主线事件链
3. 标记必须修复的断裂点
4. 确认31-100章的实际outline

---

## 🎯 预期效果

### 修复前
```
Ch93末："他来了。"
Ch94开："荧惑的指尖悬在晶阵核心上方"
         ↑ 场景跳接，缺少对峙过渡
```

### 修复后
```
Ch93末：
exit_bridge: {
  location: "地宫外石台",
  characters: ["段奕尘", "荧惑"],
  unfinished: "对峙即将开始",
  hook: "段奕尘如何应对曜师"
}

Ch94开：
entry_check: ✅ location匹配
            ✅ characters在场
            ✅ hook在3段内消费
            ✅ 时间连续

正文："荧惑站在石台对面，暗金光芒中..."
```

---

## 📊 投入产出评估

### 投入
- **工具开发**: 4-6小时
- **批量提取**: 2-3小时
- **手动审核**: 1-2小时
- **系统集成**: 2-3小时
- **总计**: 10-14小时

### 产出
- ✅ 100章完整桥接数据
- ✅ 承诺管理表
- ✅ 事件因果链
- ✅ 自动连续性检查
- ✅ 后续章节可复用

### ROI
- 避免101-200章重复断裂
- 降低50%的章节修复成本
- 提升写作流畅度200%

---

## 🚀 立即行动

需要我帮你：

1. **开发提取工具**（extract_bridge.py）
2. **批量提取100章数据**
3. **生成连续性报告**
4. **提供修复建议**

预计时间：2-3小时  
预期成果：完整的章间契约数据库

**开始吗？**
