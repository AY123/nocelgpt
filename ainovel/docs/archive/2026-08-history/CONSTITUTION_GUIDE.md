# Commercial Constitution 使用指南

## 📋 什么是Commercial Constitution

Commercial Constitution（商业宪法）是作品级的商业规则定义，它明确了：
- **目标是什么**：平台、题材、受众
- **卖点是什么**：核心吸引力
- **底线是什么**：约束和禁区

所有章节必须符合这个宪法，违反宪法的章节会被标记或拒绝。

---

## 🎯 为什么需要Constitution

### 问题
- 题材漂移（从玄幻写成都市）
- 卖点缺失（说好的爽文却全是剧情）
- 受众不匹配（男频内容女频读者）
- 商业失焦（没有明确的付费驱动）

### 解决方案
Constitution作为"商业宪法"：
- ✅ 明确定位，避免漂移
- ✅ 强制卖点，确保爽感
- ✅ 受众匹配，提升留存
- ✅ 商业约束，保证变现

---

## 📦 Constitution结构

### 1. 基础定位
```json
{
  "constitution_id": "CONST-LINGSE-001",
  "work_title": "灵色",
  "target_platform": "qidian",      // 起点中文网
  "primary_genre": "xuanhuan",      // 玄幻
  "secondary_genres": ["xiuzhen"]   // 修真
}
```

### 2. 受众画像
```json
{
  "primary_audience": {
    "age_group": "young_adult",           // 18-25岁
    "gender": "male",                     // 男性
    "payment_willingness": "high",        // 高付费意愿
    "reading_speed": "fast",              // 快速阅读
    "content_preference": ["爽文", "升级"], // 内容偏好
    "pain_points": ["无聊", "压力"],       // 痛点
    "fulfillment_needs": ["成就感"]        // 满足需求
  }
}
```

### 3. 核心卖点
```json
{
  "core_selling_points": [
    {
      "name": "修炼升级",
      "type": "power",
      "frequency": "every_3_chapters",
      "validation_keywords": ["突破", "境界", "修炼"],
      "minimum_intensity": 0.6
    }
  ]
}
```

### 4. 商业约束
```json
{
  "constraints": {
    "forbidden_elements": ["政治敏感"],
    "required_elements": ["正能量"],
    "min_hook_score": 75,
    "max_chapters_without_payoff": 3,
    "genre_drift_tolerance": 0.25
  }
}
```

---

## 🚀 如何使用

### 步骤1: 创建Constitution

使用示例模板：
```bash
cp examples/constitution-lingse.json my-constitution.json
```

修改为你的作品定位：
- 修改平台和题材
- 定义受众画像
- 列出核心卖点
- 设置约束规则

### 步骤2: 验证章节

```python
from runtime.constitution_integration import ConstitutionIntegration

# 加载Constitution
integration = ConstitutionIntegration("my-constitution.json")

# 验证章节
chapter_content = "..."  # 章节正文
chapter_metadata = {
    "qa_scores": {"hook": 80, "retention": 75}
}

compliance = integration.validate_chapter(chapter_content, chapter_metadata)

# 检查结果
if compliance["is_compliant"]:
    print("✅ 章节符合商业规则")
else:
    print("❌ 章节违反商业规则")
    for v in compliance["violations"]:
        print(f"  - [{v['severity']}] {v['description']}")
```

### 步骤3: 决策影响

```python
# 获取对发布决策的影响
action, reason = integration.get_decision_impact(compliance)

if action == "block":
    print(f"🚫 阻断发布: {reason}")
elif action == "hold":
    print(f"⏸️  暂缓发布: {reason}")
else:
    print("✅ 可以发布")
```

### 步骤4: 查看报告

```python
# 生成可读摘要
summary = integration.generate_summary_message(compliance)
print(summary)
```

输出示例：
```
Constitution Compliance: ✅ PASS
Overall Score: 82.5%
  Genre: 85.0%
  Selling Points: 75.0%
  Audience: 90.0%
  Constraints: ✅

No violations
```

---

## 📊 验证维度

### 1. 题材对齐度 (genre_alignment)
**检查内容**: 是否符合预定义的题材
**检测方法**: 关键词匹配
**阈值**: `1 - genre_drift_tolerance`

**示例**:
- 玄幻题材关键词：灵力、修炼、法宝、仙、魔
- 都市题材关键词：都市、公司、职场、豪门

### 2. 卖点命中率 (selling_point_hit)
**检查内容**: 核心卖点是否体现
**检测方法**: validation_keywords匹配
**阈值**: 至少50%卖点命中

**示例**:
- 修炼升级卖点：检查"突破"、"境界"等关键词
- 战斗爽感卖点：检查"战斗"、"胜利"等关键词

### 3. 受众匹配度 (audience_match)
**检查内容**: 内容是否符合受众偏好
**检测方法**: content_preference匹配
**阈值**: 根据偏好关键词

**示例**:
- 爽文偏好：打脸、反转、震惊
- 剧情偏好：阴谋、布局、伏笔

### 4. 约束检查 (constraint_pass)
**检查内容**: 是否违反约束
**检测方法**: 直接检测
**阈值**: 零容忍

**检查项**:
- 禁止元素（critical）
- 必需元素（medium）
- 钩子分数（high）

---

## ⚠️ 违规处理

### Critical违规 → Block
- 包含禁止元素
- 例：政治敏感内容

**处理**: 阻断发布，必须修改

### High违规 → Hold
- 题材严重偏离
- 钩子分数过低
- 例：对齐度 < 70%

**处理**: 暂缓发布，建议修改

### Medium违规 → Warning
- 卖点命中率低
- 缺少必需元素

**处理**: 记录警告，可以发布

---

## 💡 最佳实践

### 1. 早期定义
在开始创作前就定义Constitution，而不是写完再补

### 2. 定期检查
每10-20章检查一次题材漂移和卖点密度

### 3. 数据驱动
根据真实反馈数据调整阈值：
- 钩子分数阈值
- 卖点最低强度
- 题材漂移容忍度

### 4. 版本管理
Constitution应该版本化：
- 记录修改历史
- 说明修改原因
- 评估影响范围

---

## 📝 示例：灵色Constitution

参考 `examples/constitution-lingse.json`

**定位**:
- 平台：起点
- 题材：玄幻+修真
- 受众：18-25岁男性，高付费

**卖点**:
1. 修炼升级（每3章）
2. 战斗爽感（每章）
3. 智慧布局（里程碑）
4. 悬念钩子（每章）

**约束**:
- 钩子≥75分
- 最多3章无爽点
- 题材漂移容忍25%

---

## 🔧 集成到生成流程

在loop.py中集成：
```python
# 1. 加载Constitution
from runtime.constitution_integration import ConstitutionIntegration

constitution_path = project_path / "constitution.json"
if constitution_path.exists():
    integration = ConstitutionIntegration(str(constitution_path))
else:
    integration = None

# 2. 生成章节后验证
if integration:
    compliance = integration.validate_chapter(
        chapter_content,
        {"qa_scores": final_quality_scores}
    )
    
    # 3. 写入Production Card
    production_card.constitution_compliance = compliance
    
    # 4. 影响决策
    action, reason = integration.get_decision_impact(compliance)
    if action == "block":
        production_card.publish_recommendation = "block"
        production_card.blocking_issues.append(reason)
```

---

## 🎯 FAQ

### Q: Constitution可以修改吗？
A: 可以，但建议谨慎：
- 修改会影响所有后续章节
- 记录版本和修改原因
- 评估对已生成章节的影响

### Q: 如何校准阈值？
A: 基于真实数据：
- 收集多章节数据
- 观察分数分布
- 设置合理阈值（如P85分位）

### Q: 多个作品需要多个Constitution吗？
A: 是的：
- 每个作品一个Constitution
- 不同作品的定位不同
- 便于独立管理和优化

### Q: 验证失败了怎么办？
A: 分级处理：
- Critical: 必须修改
- High: 建议修改
- Medium: 可选修改
- 记录所有违规，用于改进

---

**开始使用Commercial Constitution，让你的作品商业价值最大化！** 🚀
