# 章间契约层完整实施方案

**目标**: 确保小说具备四大核心能力  
**时间**: 预计10-14小时  
**当前**: 2026-08-13

---

## 🎯 四大核心能力对应的技术保障

### 1. 小说质量高

**对应机制**:
- ✅ 结构完整 → 五层大纲法
- ✅ 人物可信 → Character Runtime + 人物卡片库
- ✅ 设定稳定 → 设定模块化 + 自动检查
- ✅ 正文可读 → Scene Plan + AI味道检测
- ✅ 节奏优秀 → 升级流循环 + Narrative Mandate

### 2. 商业价值高

**对应机制**:
- ✅ 题材定位 → outline.schema.json
- ✅ 卖点强 → 曜能体系 + 身世悬念
- ✅ 付费点 → 升级流设计
- ✅ 竞争力 → 起点玄幻标准

### 3. 读者留存强

**对应机制**:
- ✅ 开篇吸引 → Ch1已精修（危机前置）
- ⏳ 章末钩子强 → 10章已强化，26章待处理
- ❌ 追读动机持续 → **章间契约层缺失**
- ❌ 弃书风险低 → **断裂检测缺失**

### 4. 长期维护好

**对应机制**:
- ❌ 不崩设定 → **设定库未建立**
- ❌ 不崩人设 → **人物卡片不完整**
- ❌ 不崩节奏 → **31章后大纲降级**
- ❌ 不丢伏笔 → **伏笔管理表缺失**

---

## 🔧 实施路径（三阶段）

### 阶段一：基础设施（P0，4小时）

**目标**: 建立数据基础，支撑后续工作

#### Task 1.1: 建立知识库目录结构（30分钟）
```
knowledge-base/
├── characters/          # 人物卡片
│   ├── 段奕尘.json
│   ├── 镜见川.json
│   ├── 二叔段正山.json
│   └── templates/
│       └── character_template.json
├── world/              # 世界观设定
│   ├── 曜能体系.json
│   ├── 势力关系.json
│   ├── 地图.json
│   └── 重要地点.json
├── plot/               # 剧情管理
│   ├── 主线规划.json
│   ├── 九线规划.json
│   ├── 伏笔管理表.json
│   └── 事件因果链.json
├── outline/            # 大纲规划
│   ├── 卷规划.json
│   ├── 章节大纲.json
│   └── chapter_contracts/
│       ├── ch001.json
│       ├── ch002.json
│       └── ...
└── quality/            # 质量保障
    ├── 断裂检测日志.json
    ├── 设定冲突记录.json
    └── 质量巡检报告.json
```

#### Task 1.2: 调试extract_bridge.py（1小时）
- 修复API调用问题
- 测试前10章提取质量
- 确认数据结构正确

#### Task 1.3: 提取100章基础数据（2小时）
- 批量提取章末段落
- 提取章节开头
- 生成初步bridge数据
- 人工审核关键章节

#### Task 1.4: 建立质量检查工具（30分钟）
- check_continuity.py框架
- 基础断裂检测规则
- 报告生成器

---

### 阶段二：核心补强（P1，6小时）

**目标**: 补充缺失的关键模块

#### Task 2.1: 逆向提取100章剧情骨架（2小时）

**工具**: extract_plot_skeleton.py

**提取内容**:
```python
# 每章提取
{
  "chapter": 1,
  "起始状态": {
    "time": "...",
    "location": "...",
    "主要人物": [...],
    "当前目标": "..."
  },
  "本章事件": [
    "矿监司盘问",
    "身份即将暴露",
    "暗金晶体觉醒",
    "二叔现身"
  ],
  "角色变化": {
    "段奕尘": "被动逃亡 → 被迫面对",
    "状态": "隐藏身份 → 暴露"
  },
  "新增事实": [
    "段奕尘有暗金晶体",
    "二叔未死",
    "十七号身份"
  ],
  "埋下伏笔": [
    {
      "promise_id": "十七号身世",
      "内容": "\"十七年了，总算让二叔找到你了\"",
      "预计回收": 94
    }
  ],
  "兑现承诺": [],
  "未完成目标": "逃离二叔",
  "章末出口": {
    "location": "矿道深处",
    "characters": ["段奕尘", "二叔"],
    "unfinished": "对峙即将开始"
  },
  "下章入口要求": {
    "must_continue_from": "对峙场景",
    "time_gap": "无跳跃",
    "pov": "段奕尘"
  },
  "断裂风险": []
}
```

#### Task 2.2: 建立伏笔管理表（1.5小时）

**工具**: extract_promises.py

**数据结构**:
```json
{
  "promises": [
    {
      "promise_id": "矿心身世",
      "type": "mystery",
      "priority": "high",
      "埋设章节": 2,
      "埋设内容": "父亲说'你不是我儿子'",
      "当前状态": "已提示，未揭露",
      "影响剧情线": ["主线", "悬念线"],
      "已提醒章节": [2, 15, 35, 67],
      "下次提醒章节": 88,
      "提醒方式": "暗金回应强化",
      "预计回收章节": 94,
      "回收方式": "二叔揭示十七号计划",
      "回收质量要求": "震撼、合理、有伏笔",
      "检查点": [
        {"chapter": 88, "status": "pending"},
        {"chapter": 94, "status": "pending"}
      ],
      "相关事件": ["ev_001", "ev_015", "ev_094"],
      "相关人物": ["段奕尘", "二叔", "父亲"],
      "风险": "跨度较大，需持续提醒"
    }
  ]
}
```

#### Task 2.3: 建立人物卡片库（1.5小时）

**核心人物卡片**（段奕尘示例）:
```json
{
  "name": "段奕尘",
  "role": "主角",
  "初始设定": {
    "年龄": "17",
    "身份": "逃矿矿工",
    "外貌": "瘦削、眼神警觉",
    "性格": "隐忍、警觉、果断",
    "背景": "清远矿难幸存者",
    "秘密": "体内有暗金晶体"
  },
  "核心驱动": {
    "外部目标": "复仇二叔、找到真相",
    "内部需求": "证明自己、保护妹妹",
    "最大恐惧": "失控、伤害无辜",
    "性格缺陷": "过度自我牺牲、不信任他人"
  },
  "能力体系": {
    "曜能等级": "觉醒期",
    "特殊能力": "暗金晶体吞噬",
    "成长路径": [
      {"章节": "1-10", "阶段": "被动吞噬"},
      {"章节": "11-30", "阶段": "主动控制"},
      {"章节": "31-50", "阶段": "战斗运用"},
      {"章节": "51-70", "阶段": "代价平衡"},
      {"章节": "71-100", "阶段": "融合突破"}
    ],
    "代价机制": "晶化风险"
  },
  "关系网络": {
    "镜见川": {
      "关系": "试探→合作→信任",
      "转折章节": [3, 15, 45],
      "当前状态": "相互试探"
    },
    "二叔": {
      "关系": "仇恨→真相",
      "核心冲突": "十七号计划",
      "决战章节": 94
    }
  },
  "成长轨迹": [
    {"章节": 1, "状态": "被动逃亡", "心理": "恐惧"},
    {"章节": 10, "状态": "主动觉醒", "心理": "决心"},
    {"章节": 30, "状态": "掌握力量", "心理": "自信"},
    {"章节": 50, "状态": "面对代价", "心理": "挣扎"},
    {"章节": 70, "状态": "接纳自我", "心理": "成熟"},
    {"章节": 94, "状态": "终局对峙", "心理": "平静"}
  ],
  "禁止事项": [
    "不能突然变得信任他人",
    "不能轻易放弃复仇",
    "不能忘记父亲教诲",
    "代价机制不能消失"
  ],
  "出场章节": [1, 2, 3, ...],
  "关键场景": [
    {"chapter": 1, "scene": "暗金觉醒"},
    {"chapter": 10, "scene": "主动吞噬"},
    {"chapter": 94, "scene": "终局对峙"}
  ]
}
```

#### Task 2.4: 建立世界观设定库（1小时）

**曜能体系**:
```json
{
  "system_name": "曜能体系",
  "version": "1.0",
  "last_update": "2026-08-13",
  
  "核心规则": {
    "能量来源": "曜晶",
    "修炼体系": [
      {"等级": "曜徒", "特征": "感知曜能", "章节范围": "1-30"},
      {"等级": "曜士", "特征": "外放曜能", "章节范围": "31-60"},
      {"等级": "曜师", "特征": "曜能共鸣", "章节范围": "61-90"},
      {"等级": "曜宗", "特征": "曜能化形", "章节范围": "91+"}
    ],
    "特殊存在": {
      "曜能种": "植入体内的曜能核心",
      "暗金晶体": "段奕尘的特殊能力",
      "矿心": "曜能种的来源"
    }
  },
  
  "代价机制": {
    "晶化风险": "过度使用会导致身体晶化",
    "表现": "皮肤出现暗金纹路",
    "不可逆": "超过临界点会永久晶化",
    "克制方法": "控制使用频率"
  },
  
  "禁止事项": [
    "不能随意改变等级体系",
    "不能让代价消失",
    "不能让暗金晶体变成普通能力",
    "不能让曜能种随便获得"
  ],
  
  "已展示章节": [1, 2, 5, 10, 15, ...],
  "核心设定出处": {
    "曜能种": "Ch2",
    "暗金晶体": "Ch1",
    "代价机制": "Ch5",
    "等级体系": "Ch10"
  }
}
```

---

### 阶段三：系统集成（P2，4小时）

**目标**: 将数据接入生产链，实现自动化

#### Task 3.1: 开发连续性检查工具（2小时）

**工具**: check_continuity.py

**检查维度**:
```python
def check_chapter_continuity(prev_ch, next_ch):
    """
    检查相邻章节连续性
    """
    issues = []
    
    # 1. 地点连续性
    if prev_ch.exit_bridge.location != next_ch.entry_state.location:
        if not has_explicit_transition(next_ch):
            issues.append({
                "type": "location_jump",
                "severity": "high",
                "prev_location": prev_ch.exit_bridge.location,
                "next_location": next_ch.entry_state.location,
                "suggestion": "需要添加场景转换"
            })
    
    # 2. 时间连续性
    if is_time_backward(prev_ch.exit_bridge.time, next_ch.entry_state.time):
        issues.append({
            "type": "time_backward",
            "severity": "critical"
        })
    
    # 3. 人物连续性
    missing = set(prev_ch.exit_bridge.characters) - set(next_ch.entry_state.characters)
    if missing and not has_exit_explanation(next_ch, missing):
        issues.append({
            "type": "character_disappear",
            "severity": "medium",
            "missing_characters": list(missing)
        })
    
    # 4. 未完成动作
    if prev_ch.exit_bridge.unfinished_action:
        if not action_consumed_in(next_ch, prev_ch.exit_bridge.unfinished_action):
            issues.append({
                "type": "unfinished_action_dropped",
                "severity": "high",
                "action": prev_ch.exit_bridge.unfinished_action
            })
    
    # 5. 钩子兑现
    if prev_ch.exit_bridge.hook_promise:
        consumed_at = find_hook_consumption_paragraph(next_ch, prev_ch.exit_bridge.hook_promise)
        if consumed_at > 20:  # 超过20%才回应
            issues.append({
                "type": "hook_delayed",
                "severity": "medium",
                "consumed_at_paragraph": consumed_at
            })
        elif consumed_at == -1:
            issues.append({
                "type": "hook_not_consumed",
                "severity": "high"
            })
    
    # 6. 设定一致性
    setting_conflicts = check_setting_consistency(prev_ch, next_ch)
    issues.extend(setting_conflicts)
    
    # 7. 人设一致性
    character_conflicts = check_character_consistency(prev_ch, next_ch)
    issues.extend(character_conflicts)
    
    return issues
```

#### Task 3.2: 开发伏笔追踪工具（1小时）

**工具**: track_promises.py

**功能**:
- 自动标记已埋伏笔
- 检查提醒时机
- 警告超期未收束
- 生成回收建议

#### Task 3.3: 建立自动巡检系统（1小时）

**每章生成前自动检查**:
```python
def pre_chapter_check(chapter_num):
    """
    生成新章前的自动检查
    """
    checks = []
    
    # 1. 上一章出口状态
    prev_bridge = load_chapter_bridge(chapter_num - 1)
    checks.append(("上章出口", prev_bridge))
    
    # 2. 本章入口要求
    entry_requirements = generate_entry_requirements(prev_bridge)
    checks.append(("入口要求", entry_requirements))
    
    # 3. 伏笔检查
    pending_promises = get_pending_promises(chapter_num)
    checks.append(("待处理伏笔", pending_promises))
    
    # 4. 人物状态
    character_states = get_character_states(chapter_num)
    checks.append(("人物状态", character_states))
    
    # 5. 设定检查
    active_settings = get_active_settings(chapter_num)
    checks.append(("激活设定", active_settings))
    
    return checks

def post_chapter_check(chapter_num, chapter_text):
    """
    章节生成后的质量检查
    """
    issues = []
    
    # 1. 连续性检查
    if chapter_num > 1:
        continuity_issues = check_continuity(chapter_num - 1, chapter_num)
        issues.extend(continuity_issues)
    
    # 2. 设定冲突检查
    setting_conflicts = check_setting_conflicts(chapter_text)
    issues.extend(setting_conflicts)
    
    # 3. 人设冲突检查
    character_conflicts = check_character_ooc(chapter_text)
    issues.extend(character_conflicts)
    
    # 4. 伏笔检查
    promise_issues = check_promise_handling(chapter_num, chapter_text)
    issues.extend(promise_issues)
    
    # 5. 钩子质量检查
    hook_quality = evaluate_hook_quality(chapter_text)
    issues.append(("钩子评分", hook_quality))
    
    return issues
```

---

## 📋 详细执行计划

### 第一天（4小时）

**上午（2小时）**:
1. 创建knowledge-base目录结构
2. 调试extract_bridge.py的API
3. 测试前10章提取

**下午（2小时）**:
4. 批量提取100章基础数据
5. 人工审核关键章节
6. 修正提取错误

### 第二天（6小时）

**上午（3小时）**:
7. 运行extract_plot_skeleton.py
8. 逆向提取100章骨架
9. 人工补充关键信息

**下午（3小时）**:
10. 建立伏笔管理表
11. 建立核心人物卡片（5人）
12. 建立世界观设定库

### 第三天（4小时）

**上午（2小时）**:
13. 开发check_continuity.py
14. 运行全章检查
15. 生成断裂报告

**下午（2小时）**:
16. 开发track_promises.py
17. 建立自动巡检系统
18. 集成测试

---

## 🎯 质量保障机制

### 四大能力保障清单

#### 1. 小说质量高

**保障机制**:
- [ ] 章间契约层完整
- [ ] 连续性自动检查
- [ ] 设定冲突检测
- [ ] 人设OOC检测
- [ ] 节奏巡检

**验收标准**:
- 相邻章节断裂率 < 5%
- 设定冲突 = 0
- 人设OOC = 0

#### 2. 商业价值高

**保障机制**:
- [ ] 卖点库建立
- [ ] 付费点规划
- [ ] 钩子质量检测

**验收标准**:
- 每章钩子评分 > 60分
- 卖点密度适中

#### 3. 读者留存强

**保障机制**:
- [ ] 开篇已优化（Ch1精修完成）
- [ ] 章末钩子强化（10章完成，26章待处理）
- [ ] 追读动机检查
- [ ] 弃书风险预警

**验收标准**:
- 开篇3章吸引力 > 80分
- 钩子平均分 > 70分
- 断裂点 < 3处/100章

#### 4. 长期维护好

**保障机制**:
- [ ] 设定库完整
- [ ] 人物卡片完整
- [ ] 伏笔追踪系统
- [ ] 自动巡检

**验收标准**:
- 设定冲突 = 0
- 人设冲突 = 0
- 伏笔回收率 > 90%
- 大纲细化到每章

---

## 🚀 立即开始

我现在开始执行**Task 1.1**：创建知识库目录结构

需要我立即开始吗？
