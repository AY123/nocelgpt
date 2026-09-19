# ANovel V2 质量保证框架

**版本**: v1.0  
**制定日期**: 2026-09-18  
**状态**: Draft  
**用途**: 定义AI生成内容的质量保证体系  

---

## 📋 文档目的

本文档定义ANovel V2的质量保证（QA）框架，包括：
1. **质量标准** - 什么是"好"的生成内容
2. **自动化检测** - 机器可执行的质量检查
3. **人工审核** - 人工介入的时机和流程
4. **反馈循环** - 如何持续改进质量
5. **A/B测试** - 如何验证改进效果

核心挑战：
- AI生成内容质量不稳定
- 主观评价难以量化
- 成本与质量的平衡
- 规模化质量控制

---

## 🎯 质量标准定义

### 1. 质量维度矩阵

| 维度 | 描述 | 权重 | 检测方式 |
|------|------|------|----------|
| **题材符合度** | 符合Genre约束 | 30% | 自动检测 |
| **文本质量** | 语言流畅、无错误 | 25% | 自动+人工 |
| **情节合理性** | 逻辑连贯、不矛盾 | 20% | 人工为主 |
| **角色一致性** | 人物性格、能力一致 | 15% | 自动+人工 |
| **读者吸引力** | 悬念、节奏、爽点 | 10% | 人工+数据 |

### 2. 分级标准

#### A级（优秀）- 90-100分
- ✅ 完全符合题材约束
- ✅ 文本流畅，无明显错误
- ✅ 情节合理，有吸引力
- ✅ 角色性格鲜明一致
- ✅ 章末有悬念钩子
- **处理**：直接发布

#### B级（良好）- 75-89分
- ✅ 基本符合题材约束
- ✅ 文本可读，少量小错误
- ⚠️ 情节偶有瑕疵
- ✅ 角色基本一致
- **处理**：小幅修订后发布

#### C级（合格）- 60-74分
- ⚠️ 题材符合度一般
- ⚠️ 文本有明显问题
- ⚠️ 情节有逻辑漏洞
- ⚠️ 角色表现不稳定
- **处理**：重新生成或大幅修订

#### D级（不合格）- <60分
- ❌ 违反题材约束
- ❌ 文本质量差
- ❌ 情节崩坏
- ❌ 角色OOC
- **处理**：拒绝，重新生成

---

## 🤖 自动化质量检测

### 1. 题材符合度检测

#### 1.1 基于规则的检测

```python
from core.genre import GenreValidator
from typing import List, Dict

class GenreComplianceChecker:
    """题材符合度检查器"""
    
    def __init__(self):
        self.validator = GenreValidator()
    
    async def check(
        self,
        genre_id: str,
        content: str,
        context: Dict = None
    ) -> Dict[str, any]:
        """检查题材符合度
        
        Returns:
            {
                "score": 0-100,
                "violations": [...],
                "has_blocking": bool,
                "details": {...}
            }
        """
        # 1. 执行约束验证
        result = self.validator.validate(genre_id, content, context)
        
        # 2. 计算分数
        if result.is_valid:
            score = 100.0
        elif result.has_blocking_violations:
            score = 0.0
        else:
            # 根据违规数量和严重程度计算
            score = self._calculate_score(result.violations)
        
        return {
            "score": score,
            "violations": [v.to_dict() for v in result.violations],
            "has_blocking": result.has_blocking_violations,
            "details": {
                "total_violations": len(result.violations),
                "critical": len(result.get_critical_violations()),
                "blocking": len(result.get_blocking_violations())
            }
        }
    
    def _calculate_score(self, violations: List) -> float:
        """计算分数"""
        if not violations:
            return 100.0
        
        # 每个违规扣分
        penalty = 0
        for v in violations:
            if v.severity.value == "critical":
                penalty += 50
            elif v.severity.value == "high":
                penalty += 20
            elif v.severity.value == "medium":
                penalty += 10
            else:
                penalty += 5
        
        return max(0, 100 - penalty)
```

#### 1.2 基于LLM的检测（更准确但更贵）

```python
async def check_genre_with_llm(
    genre_id: str,
    content: str,
    genre_config
) -> Dict[str, any]:
    """使用LLM检查题材符合度"""
    
    prompt = f"""
你是一位资深的{genre_config.genre_name}题材审核专家。

请评估以下内容是否符合{genre_config.genre_name}题材规范：

【题材规范】
{genre_config.to_prompt_context()}

【待审核内容】
{content[:1000]}...

【评估标准】
1. 是否严格遵守题材约束？
2. 是否包含禁止元素？
3. 世界观是否一致？
4. 整体风格是否匹配？

请输出JSON格式：
{{
  "score": 0-100,
  "compliant": true/false,
  "issues": ["问题1", "问题2", ...],
  "reasoning": "简短说明"
}}
"""
    
    result = await llm.generate(
        prompt,
        model="claude-haiku-4",  # 用便宜的模型
        max_tokens=500
    )
    
    return json.loads(result)
```

### 2. 文本质量检测

#### 2.1 基础指标

```python
class TextQualityChecker:
    """文本质量检查器"""
    
    def check(self, content: str) -> Dict[str, any]:
        """检查文本质量"""
        metrics = {}
        
        # 1. 字数检查
        word_count = len(content)
        metrics["word_count"] = word_count
        metrics["word_count_score"] = self._score_word_count(word_count)
        
        # 2. 段落结构
        paragraphs = content.split("\n\n")
        metrics["paragraph_count"] = len(paragraphs)
        metrics["avg_paragraph_length"] = sum(len(p) for p in paragraphs) / len(paragraphs)
        metrics["paragraph_score"] = self._score_paragraphs(paragraphs)
        
        # 3. 对话比例
        dialogue_ratio = self._calculate_dialogue_ratio(content)
        metrics["dialogue_ratio"] = dialogue_ratio
        metrics["dialogue_score"] = self._score_dialogue_ratio(dialogue_ratio)
        
        # 4. 重复检测
        repetition_score = self._check_repetition(content)
        metrics["repetition_score"] = repetition_score
        
        # 5. 标点符号
        punctuation_score = self._check_punctuation(content)
        metrics["punctuation_score"] = punctuation_score
        
        # 综合评分
        metrics["overall_score"] = (
            metrics["word_count_score"] * 0.2 +
            metrics["paragraph_score"] * 0.2 +
            metrics["dialogue_score"] * 0.2 +
            metrics["repetition_score"] * 0.2 +
            metrics["punctuation_score"] * 0.2
        ) * 100
        
        return metrics
    
    def _score_word_count(self, word_count: int) -> float:
        """评估字数（期望1800-2200字）"""
        if 1800 <= word_count <= 2200:
            return 1.0
        elif 1500 <= word_count < 1800 or 2200 < word_count <= 2500:
            return 0.8
        elif 1200 <= word_count < 1500 or 2500 < word_count <= 3000:
            return 0.6
        else:
            return 0.3
    
    def _score_paragraphs(self, paragraphs: List[str]) -> float:
        """评估段落结构"""
        if len(paragraphs) < 5:
            return 0.5  # 段落太少
        
        lengths = [len(p) for p in paragraphs]
        avg = sum(lengths) / len(lengths)
        
        # 期望平均段落长度50-200字
        if 50 <= avg <= 200:
            return 1.0
        elif 30 <= avg < 50 or 200 < avg <= 300:
            return 0.7
        else:
            return 0.4
    
    def _calculate_dialogue_ratio(self, content: str) -> float:
        """计算对话比例"""
        # 简单方法：统计引号内容
        import re
        dialogues = re.findall(r'"[^"]*"', content)
        dialogue_chars = sum(len(d) for d in dialogues)
        total_chars = len(content)
        
        return dialogue_chars / total_chars if total_chars > 0 else 0
    
    def _score_dialogue_ratio(self, ratio: float) -> float:
        """评估对话比例（期望20-40%）"""
        if 0.2 <= ratio <= 0.4:
            return 1.0
        elif 0.1 <= ratio < 0.2 or 0.4 < ratio <= 0.5:
            return 0.7
        else:
            return 0.4
    
    def _check_repetition(self, content: str) -> float:
        """检测重复内容"""
        sentences = content.split("。")
        
        # 检查是否有完全重复的句子
        unique_sentences = set(sentences)
        repetition_rate = 1 - (len(unique_sentences) / len(sentences))
        
        if repetition_rate < 0.05:
            return 1.0
        elif repetition_rate < 0.1:
            return 0.7
        else:
            return 0.3
    
    def _check_punctuation(self, content: str) -> float:
        """检查标点符号使用"""
        # 检查是否有基本标点
        has_period = "。" in content
        has_comma = "，" in content
        has_quotes = """ in content or "「" in content
        
        score = 0
        if has_period: score += 0.4
        if has_comma: score += 0.3
        if has_quotes: score += 0.3
        
        return score
```

#### 2.2 语言模型检测

```python
async def check_text_quality_with_llm(content: str) -> Dict[str, any]:
    """使用LLM检查文本质量"""
    
    prompt = f"""
请作为语文老师评估以下文本的质量（0-10分）：

【文本】
{content[:800]}...

【评估维度】
1. 语言流畅度（是否通顺）
2. 用词准确性（是否恰当）
3. 语法正确性（是否有错误）
4. 表达清晰度（是否易懂）

输出JSON：
{{
  "fluency": 0-10,
  "accuracy": 0-10,
  "grammar": 0-10,
  "clarity": 0-10,
  "overall": 0-10,
  "issues": ["问题1", ...]
}}
"""
    
    result = await llm.generate(prompt, model="claude-haiku-4", max_tokens=300)
    return json.loads(result)
```

### 3. 角色一致性检测

```python
class CharacterConsistencyChecker:
    """角色一致性检查器"""
    
    async def check(
        self,
        character_id: str,
        chapter_content: str,
        character_profile: Dict,
        previous_chapters: List[str]
    ) -> Dict[str, any]:
        """检查角色一致性"""
        
        # 1. 提取当前章节中的角色表现
        current_traits = await self._extract_character_traits(
            chapter_content,
            character_profile["name"]
        )
        
        # 2. 与角色档案对比
        profile_match = self._compare_with_profile(
            current_traits,
            character_profile
        )
        
        # 3. 与历史表现对比
        history_match = await self._compare_with_history(
            current_traits,
            character_profile["name"],
            previous_chapters[-5:]  # 最近5章
        )
        
        # 4. 计算一致性分数
        score = (profile_match * 0.6 + history_match * 0.4) * 100
        
        return {
            "score": score,
            "profile_match": profile_match,
            "history_match": history_match,
            "inconsistencies": self._find_inconsistencies(current_traits, character_profile)
        }
    
    async def _extract_character_traits(
        self,
        content: str,
        character_name: str
    ) -> Dict[str, any]:
        """提取角色特征"""
        
        prompt = f"""
分析{character_name}在以下内容中的表现：

{content[:1000]}...

提取以下信息（JSON格式）：
{{
  "personality": ["性格特点1", ...],
  "abilities": ["展示的能力1", ...],
  "speech_style": "说话风格描述",
  "actions": ["关键行为1", ...]
}}
"""
        
        result = await llm.generate(prompt, model="claude-haiku-4", max_tokens=500)
        return json.loads(result)
    
    def _compare_with_profile(
        self,
        current_traits: Dict,
        profile: Dict
    ) -> float:
        """与角色档案对比"""
        # 简化版：检查性格特征重合度
        current_personality = set(current_traits.get("personality", []))
        profile_personality = set(profile.get("personality_traits", []))
        
        if not profile_personality:
            return 1.0
        
        overlap = len(current_personality & profile_personality)
        return overlap / len(profile_personality)
```

### 4. 情节合理性检测

```python
async def check_plot_consistency(
    chapter_content: str,
    previous_summary: str,
    outline: Dict
) -> Dict[str, any]:
    """检查情节合理性"""
    
    prompt = f"""
你是一位资深小说编辑，请检查情节合理性。

【前文概要】
{previous_summary}

【章节大纲】
{outline.get("summary", "")}

【实际内容】
{chapter_content[:1000]}...

【检查项】
1. 是否与前文矛盾？
2. 是否偏离大纲？
3. 是否有逻辑漏洞？
4. 时间线是否合理？

输出JSON：
{{
  "consistency_score": 0-10,
  "outline_match": 0-10,
  "logic_score": 0-10,
  "issues": [
    {{"type": "类型", "description": "描述", "severity": "high/medium/low"}}
  ],
  "overall": 0-10
}}
"""
    
    result = await llm.generate(prompt, model="claude-sonnet-4", max_tokens=800)
    return json.loads(result)
```

---

## 👤 人工审核流程

### 1. 人工介入触发条件

```python
class HumanReviewTrigger:
    """人工审核触发器"""
    
    def should_trigger_human_review(
        self,
        quality_metrics: Dict[str, any]
    ) -> tuple[bool, List[str]]:
        """判断是否需要人工审核
        
        Returns:
            (是否需要, 原因列表)
        """
        reasons = []
        
        # 条件1：综合评分低
        if quality_metrics.get("overall_score", 100) < 75:
            reasons.append("综合评分过低")
        
        # 条件2：题材违规
        if quality_metrics.get("genre_compliance", {}).get("has_blocking", False):
            reasons.append("存在题材违规")
        
        # 条件3：角色一致性差
        if quality_metrics.get("character_consistency", 100) < 70:
            reasons.append("角色表现不一致")
        
        # 条件4：情节合理性差
        if quality_metrics.get("plot_consistency", 100) < 70:
            reasons.append("情节存在问题")
        
        # 条件5：随机抽查（10%比例）
        import random
        if random.random() < 0.1:
            reasons.append("随机质量抽查")
        
        return len(reasons) > 0, reasons
```

### 2. 人工审核界面设计

#### 审核任务结构

```python
@dataclass
class ReviewTask:
    """审核任务"""
    task_id: str
    chapter_id: str
    chapter_number: int
    novel_id: str
    
    # 内容
    content: str
    context: Dict  # 角色档案、前文概要等
    
    # 自动检测结果
    auto_metrics: Dict[str, any]
    trigger_reasons: List[str]
    
    # 审核结果
    status: str = "pending"  # pending/approved/rejected/needs_revision
    reviewer_id: Optional[str] = None
    review_time: Optional[datetime] = None
    review_comments: str = ""
    manual_score: Optional[float] = None
    
    # 决策
    action: Optional[str] = None  # publish/revise/regenerate
    revision_instructions: str = ""
```

#### 审核界面功能

```
┌─────────────────────────────────────────────────────┐
│ 章节审核                                             │
├─────────────────────────────────────────────────────┤
│                                                     │
│ 小说：都市之巅  第5章：初露锋芒                      │
│                                                     │
│ 【自动检测结果】                                     │
│ ✅ 题材符合度：95分                                  │
│ ⚠️ 文本质量：72分（需关注）                          │
│ ✅ 角色一致性：88分                                  │
│ ⚠️ 情节合理性：68分（需关注）                        │
│                                                     │
│ 【触发原因】                                         │
│ - 情节存在问题                                       │
│                                                     │
│ 【章节内容】                                         │
│ ┌─────────────────────────────────────────────┐   │
│ │ 陈阳走进会议室，十几双眼睛齐刷刷地看向他... │   │
│ │                                             │   │
│ │ （2150字）                                  │   │
│ └─────────────────────────────────────────────┘   │
│                                                     │
│ 【上下文】                                          │
│ - 角色档案  - 前文概要  - 章节大纲                  │
│                                                     │
│ 【审核意见】                                         │
│ ┌─────────────────────────────────────────────┐   │
│ │ [输入框]                                    │   │
│ └─────────────────────────────────────────────┘   │
│                                                     │
│ 【决策】                                            │
│ [✓ 通过发布] [✗ 拒绝] [↻ 修订] [⟳ 重新生成]         │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 3. 人工审核指南

```markdown
# 审核员指南

## 审核重点

### 1. 题材符合度（最高优先级）
- ❌ 是否有禁止元素？（如都市出现修炼）
- ❌ 是否违反世界观？（如现代出现古代物品）
- ✅ 是否符合题材风格？

### 2. 情节合理性
- 是否与前文矛盾？
- 时间线是否合理？
- 角色行为是否符合逻辑？
- 是否有明显Bug？

### 3. 角色一致性
- 性格是否稳定？
- 能力是否匹配？
- 说话风格是否一致？

### 4. 文本质量
- 语言是否流畅？
- 是否有错别字？
- 标点是否正确？

### 5. 读者体验
- 是否有吸引力？
- 节奏是否合适？
- 章末是否有钩子？

## 决策标准

### 通过发布
- 题材完全符合
- 质量达到B级以上
- 无明显问题

### 需要修订
- 有小问题但可修复
- 整体框架可用
- 给出具体修订意见

### 重新生成
- 题材严重违规
- 情节完全崩坏
- 无法通过修订修复

### 拒绝
- 质量极差
- 多次生成仍不合格
```

---

## 🔄 反馈循环与持续改进

### 1. 数据收集

```python
@dataclass
class QualityFeedback:
    """质量反馈"""
    chapter_id: str
    
    # 自动指标
    auto_metrics: Dict[str, any]
    
    # 人工评分
    manual_score: Optional[float]
    manual_comments: str
    
    # 用户反馈
    user_rating: Optional[int]  # 1-5星
    user_comments: str
    
    # 最终结果
    action_taken: str  # published/revised/regenerated
    
    # 时间戳
    created_at: datetime
```

### 2. Prompt优化

```python
class PromptOptimizer:
    """Prompt优化器"""
    
    async def analyze_failures(
        self,
        feedbacks: List[QualityFeedback]
    ) -> Dict[str, any]:
        """分析失败案例，找出Prompt问题"""
        
        # 筛选低分章节
        failures = [
            f for f in feedbacks
            if f.auto_metrics.get("overall_score", 100) < 70
        ]
        
        if not failures:
            return {"status": "no_issues"}
        
        # 提取失败模式
        issues = []
        for f in failures:
            if f.auto_metrics.get("genre_compliance", {}).get("score", 100) < 70:
                issues.append("genre_compliance")
            if f.auto_metrics.get("text_quality", {}).get("score", 100) < 70:
                issues.append("text_quality")
        
        # 统计
        from collections import Counter
        issue_counts = Counter(issues)
        
        return {
            "total_failures": len(failures),
            "failure_rate": len(failures) / len(feedbacks),
            "common_issues": dict(issue_counts.most_common(5)),
            "recommendations": self._generate_recommendations(issue_counts)
        }
    
    def _generate_recommendations(self, issue_counts: Counter) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if issue_counts.get("genre_compliance", 0) > 10:
            recommendations.append(
                "建议：在Prompt中加强题材约束说明，增加负面示例"
            )
        
        if issue_counts.get("text_quality", 0) > 10:
            recommendations.append(
                "建议：在Prompt中添加文本质量要求，提供优秀范例"
            )
        
        return recommendations
```

### 3. A/B测试框架

```python
class ABTestManager:
    """A/B测试管理器"""
    
    def __init__(self):
        self.variants = {}  # variant_id -> config
        self.assignments = {}  # user_id -> variant_id
    
    def create_test(
        self,
        test_id: str,
        control_config: Dict,
        variant_configs: List[Dict],
        traffic_split: List[float]
    ):
        """创建A/B测试
        
        Args:
            test_id: 测试ID
            control_config: 对照组配置
            variant_configs: 实验组配置列表
            traffic_split: 流量分配比例 [50, 25, 25]
        """
        self.variants[test_id] = {
            "control": control_config,
            "variants": variant_configs,
            "split": traffic_split,
            "metrics": []
        }
    
    def assign_variant(self, user_id: str, test_id: str) -> str:
        """为用户分配variant"""
        # 哈希一致性分配
        import hashlib
        hash_val = int(hashlib.md5(f"{user_id}{test_id}".encode()).hexdigest(), 16)
        
        split = self.variants[test_id]["split"]
        cumsum = 0
        threshold = hash_val % 100
        
        for i, pct in enumerate(split):
            cumsum += pct
            if threshold < cumsum:
                variant = "control" if i == 0 else f"variant_{i}"
                self.assignments[f"{user_id}:{test_id}"] = variant
                return variant
        
        return "control"
    
    async def collect_metrics(
        self,
        test_id: str,
        variant: str,
        quality_metrics: Dict
    ):
        """收集指标"""
        self.variants[test_id]["metrics"].append({
            "variant": variant,
            "metrics": quality_metrics,
            "timestamp": datetime.now()
        })
    
    def analyze_results(self, test_id: str) -> Dict[str, any]:
        """分析A/B测试结果"""
        metrics = self.variants[test_id]["metrics"]
        
        # 按variant分组
        from collections import defaultdict
        by_variant = defaultdict(list)
        
        for m in metrics:
            by_variant[m["variant"]].append(m["metrics"])
        
        # 计算平均值
        results = {}
        for variant, metric_list in by_variant.items():
            avg_score = sum(
                m.get("overall_score", 0) for m in metric_list
            ) / len(metric_list)
            
            results[variant] = {
                "count": len(metric_list),
                "avg_score": avg_score
            }
        
        # 计算显著性（简化版）
        control_score = results["control"]["avg_score"]
        best_variant = max(
            [v for v in results.keys() if v != "control"],
            key=lambda v: results[v]["avg_score"]
        )
        improvement = (results[best_variant]["avg_score"] - control_score) / control_score * 100
        
        return {
            "results": results,
            "best_variant": best_variant,
            "improvement": improvement,
            "recommendation": "deploy" if improvement > 5 else "continue_testing"
        }
```

---

## 📊 质量监控Dashboard

### 关键指标

```python
class QualityMetricsDashboard:
    """质量指标看板"""
    
    async def get_daily_metrics(self, date: str) -> Dict[str, any]:
        """获取每日质量指标"""
        
        # 从数据库查询
        chapters = await self.db.get_chapters_by_date(date)
        
        metrics = {
            "total_chapters": len(chapters),
            "avg_score": 0,
            "score_distribution": {
                "A": 0,  # 90-100
                "B": 0,  # 75-89
                "C": 0,  # 60-74
                "D": 0   # <60
            },
            "genre_compliance_rate": 0,
            "human_review_rate": 0,
            "revision_rate": 0,
            "regeneration_rate": 0
        }
        
        scores = []
        genre_compliant = 0
        human_reviewed = 0
        revised = 0
        regenerated = 0
        
        for chapter in chapters:
            score = chapter.quality_score
            scores.append(score)
            
            # 分级
            if score >= 90:
                metrics["score_distribution"]["A"] += 1
            elif score >= 75:
                metrics["score_distribution"]["B"] += 1
            elif score >= 60:
                metrics["score_distribution"]["C"] += 1
            else:
                metrics["score_distribution"]["D"] += 1
            
            # 统计
            if chapter.genre_compliant:
                genre_compliant += 1
            if chapter.human_reviewed:
                human_reviewed += 1
            if chapter.revision_count > 0:
                revised += 1
            if chapter.generation_attempts > 1:
                regenerated += 1
        
        # 计算平均值和比率
        total = len(chapters)
        metrics["avg_score"] = sum(scores) / total if total > 0 else 0
        metrics["genre_compliance_rate"] = genre_compliant / total if total > 0 else 0
        metrics["human_review_rate"] = human_reviewed / total if total > 0 else 0
        metrics["revision_rate"] = revised / total if total > 0 else 0
        metrics["regeneration_rate"] = regenerated / total if total > 0 else 0
        
        return metrics
```

### Dashboard示例

```
┌────────────────────────────────────────────────────────────┐
│ ANovel V2 质量监控 - 2026-09-18                             │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ 📊 今日概览                                                 │
│   总章节数: 156                                             │
│   平均评分: 82.3                                            │
│   题材符合率: 94.2%                                         │
│                                                            │
│ 📈 评分分布                                                 │
│   A级(90-100): ████████████████ 45 (28.8%)                │
│   B级(75-89):  ████████████████████████ 78 (50.0%)        │
│   C级(60-74):  ████████ 28 (17.9%)                        │
│   D级(<60):    ██ 5 (3.2%)                                 │
│                                                            │
│ 🔍 人工审核                                                 │
│   审核率: 23.1% (36章)                                      │
│   通过率: 72.2%                                             │
│   修订率: 19.4%                                             │
│   重生成率: 8.3%                                            │
│                                                            │
│ ⚠️ 待处理                                                  │
│   待审核: 8章                                               │
│   待修订: 3章                                               │
│   待重生成: 2章                                             │
│                                                            │
│ 📉 趋势（近7天）                                            │
│   平均评分: 78.5 → 82.3 ↑                                  │
│   题材符合率: 91.2% → 94.2% ↑                              │
│   人工审核率: 28.3% → 23.1% ↓                              │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 🎯 质量保证工作流

### 完整流程

```
[1. 章节生成]
     ↓
[2. 自动检测]
     ├─ 题材符合度 → GenreComplianceChecker
     ├─ 文本质量 → TextQualityChecker
     ├─ 角色一致性 → CharacterConsistencyChecker
     └─ 情节合理性 → PlotConsistencyChecker
     ↓
[3. 综合评分]
     ├─ A级(≥90) → 直接发布 ✅
     ├─ B级(75-89) → 小幅修订或直接发布
     ├─ C级(60-74) → 人工审核
     └─ D级(<60) → 自动拒绝，重新生成
     ↓
[4. 人工审核]（C级或触发条件）
     ├─ 审核员评估
     ├─ 决策：通过/修订/重生成
     └─ 记录反馈
     ↓
[5. 修订/重生成]
     ├─ 根据反馈修订
     └─ 或者重新生成
     ↓
[6. 最终发布]
     ├─ 保存到数据库
     ├─ 记录质量指标
     └─ 更新监控Dashboard
     ↓
[7. 持续优化]
     ├─ 分析反馈数据
     ├─ 优化Prompt
     └─ A/B测试新策略
```

---

## 🎯 实施建议

### Phase 1（MVP）

**实现**：
- 基础自动检测（题材、文本、字数）
- 简单人工审核界面
- 基础质量指标收集

**不做**：
- 复杂的LLM检测
- 高级一致性检查
- A/B测试框架

### Phase 2（优化）

**添加**：
- LLM辅助检测
- 角色一致性检查
- 完整反馈循环
- 质量Dashboard

### Phase 3（高级）

**添加**：
- A/B测试平台
- 自动Prompt优化
- 机器学习质量预测

---

## 📚 附录

### A. 质量评分卡模板

```yaml
quality_scorecard:
  genre_compliance:
    weight: 30%
    score: 0-100
    auto_check: true
    
  text_quality:
    weight: 25%
    score: 0-100
    metrics:
      - word_count
      - paragraph_structure
      - dialogue_ratio
      - repetition
      - punctuation
      
  plot_consistency:
    weight: 20%
    score: 0-100
    auto_check: false
    
  character_consistency:
    weight: 15%
    score: 0-100
    auto_check: true
    
  reader_appeal:
    weight: 10%
    score: 0-100
    auto_check: false
```

---

**质量保证框架文档完成！** ✅

下一步：**18_DATABASE_SCHEMA_DESIGN.md**（数据库Schema设计）
