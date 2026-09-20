# ANovel V2 LLM集成策略

**版本**: v1.0  
**制定日期**: 2026-09-18  
**状态**: Draft  
**用途**: 定义LLM集成的完整策略和最佳实践  

---

## 📋 文档目的

本文档定义ANovel V2的LLM集成策略，包括：
1. **Prompt工程** - 提示词设计最佳实践
2. **多模型策略** - 不同任务选择不同模型
3. **成本优化** - Token使用和费用控制
4. **质量保证** - 输出质量监控和改进
5. **错误处理** - 失败重试和降级策略
6. **缓存策略** - 减少重复调用

基于：
- Claude API最佳实践
- 行业经验（Sudowrite、NovelAI）
- V1项目经验教训
- 成本效益分析

---

## 🎯 LLM集成核心原则

### 1. 成本意识优先

**现实**：LLM是最大成本项
- Claude Opus 4: $15/MTok输入，$75/MTok输出
- Claude Sonnet 4: $3/MTok输入，$15/MTok输出
- Claude Haiku 4: $0.25/MTok输入，$1.25/MTok输出

**策略**：
```
✅ 简单任务用便宜模型（Haiku）
✅ 核心任务用优质模型（Opus/Sonnet）
✅ 大量使用缓存
✅ 批处理降低调用次数
✅ Token优化压缩Prompt
```

### 2. 质量优先于速度

**原则**：宁可慢一点，不要质量差
- 大纲生成：用Opus，可等待2分钟
- 章节生成：用Sonnet，可等待30秒
- 快速验证：用Haiku，秒级响应

### 3. Genre-Aware Prompting

**核心思想**：Prompt必须包含题材上下文
```python
# ❌ 错误：通用Prompt
prompt = "生成一个主角"

# ✅ 正确：Genre-Aware Prompt
prompt = f"""
{genre_config.to_prompt_context()}

基于以上题材设定，生成主角：
- 必须符合题材约束
- 必须有明确的进阶路径
...
"""
```

---

## 🤖 多模型策略

### 模型选择矩阵

| 任务类型 | 推荐模型 | Token预算 | 原因 | 成本/次 |
|---------|---------|----------|------|---------|
| **创世阶段** |
| 大纲生成 | Opus 4 | 8K输入 + 8K输出 | 需要深度推理和创意 | ~$1.20 |
| 角色生成 | Sonnet 4 | 4K输入 + 2K输出 | 平衡质量与成本 | ~$0.18 |
| 世界观生成 | Sonnet 4 | 4K输入 + 2K输出 | 平衡质量与成本 | ~$0.18 |
| **生产阶段** |
| 章节生成 | Sonnet 4 | 8K输入 + 4K输出 | 主力模型 | ~$0.84 |
| 章节修订 | Sonnet 4 | 6K输入 + 2K输出 | 质量改进 | ~$0.48 |
| **验证阶段** |
| 题材验证 | Haiku 4 | 2K输入 + 0.5K输出 | 快速检查 | ~$0.01 |
| 质量检查 | Haiku 4 | 2K输入 + 0.5K输出 | 批量处理 | ~$0.01 |
| 内容检测 | GPT-4o mini | 2K输入 + 0.5K输出 | 更便宜 | ~$0.001 |

### 成本估算

**单本小说成本**（1000章，200万字）：
```
创世阶段：
- 大纲生成: 1次 × $1.20 = $1.20
- 角色生成: 5次 × $0.18 = $0.90
- 世界观生成: 1次 × $0.18 = $0.18
小计：$2.28

生产阶段：
- 章节生成: 1000次 × $0.84 = $840
- 章节修订（20%）: 200次 × $0.48 = $96
小计：$936

验证阶段：
- 题材验证: 1000次 × $0.01 = $10
- 质量检查: 1000次 × $0.01 = $10
小计：$20

总计：$958.28
```

**优化后成本**（使用缓存、批处理）：
- 缓存命中率30%：节省$281
- 最终成本：**~$677**

---

## 📝 Prompt工程最佳实践

### 1. Prompt结构模板

#### 标准Prompt结构

```xml
<system_context>
你是一个专业的{genre_name}网络小说作者。
</system_context>

<genre_definition>
{genre_config.to_prompt_context()}
</genre_definition>

<task>
{具体任务描述}
</task>

<constraints>
- 严格遵守题材约束
- 字数要求：{target_words}字
- 必须包含：{required_elements}
</constraints>

<context>
{当前故事上下文}
</context>

<examples>
{few-shot示例（可选）}
</examples>

<output_format>
{期望的输出格式}
</output_format>
```

#### 实际示例：章节生成Prompt

```python
# prompts/production/urban_chapter.j2
<system_context>
你是一位经验丰富的都市网络小说作者，擅长创作现实感强、情节紧凑的商战故事。
</system_context>

<genre_definition>
【题材】都市
【时代】现代中国（2020-2030）
【世界观】遵循现实规律，无超自然力量
【核心】商战、创业、职场奋斗

【严格禁止】
- ❌ 修炼、灵气、法宝等玄幻元素
- ❌ 超能力、异能
- ❌ 过于夸张不真实的情节
</genre_definition>

<task>
生成第{{ chapter_number }}章内容。
</task>

<constraints>
- 字数：1800-2200字
- 视角：{{ pov_character }}的第三人称视角
- 必须推进主线剧情
- 章末必须有悬念或钩子
</constraints>

<story_context>
【主角】{{ protagonist.name }}
- 当前状态：{{ protagonist.current_status }}
- 财富等级：{{ protagonist.wealth_tier }}
- 主要目标：{{ protagonist.goal }}

【故事进展】
- 当前故事弧：{{ current_arc.title }}
- 上一章摘要：{{ previous_chapter_summary }}

【本章大纲】
{{ chapter_outline }}
</story_context>

<style_guide>
- 语言：现代汉语，口语化但不粗俗
- 节奏：快节奏，避免拖沓
- 对话：自然真实，符合人物性格
- 细节：适度，不过度描写环境
</style_guide>

<output_format>
直接输出章节正文，不要任何前缀或后缀说明。
</output_format>
```

### 2. Few-Shot Prompting

**何时使用**：
- 需要特定风格
- 输出格式复杂
- 模型理解不准确

**示例：角色生成**

```python
<examples>
示例1（都市主角）：
{
  "name": "陈阳",
  "age": 25,
  "background": "贫困家庭，刚毕业的程序员",
  "personality": ["坚韧", "聪明", "不服输"],
  "goal": "通过创业改变命运",
  "wealth_tier": "温饱",
  "occupation": "初级程序员",
  "skills": ["Python编程", "架构设计", "快速学习"]
}

示例2（都市反派）：
{
  "name": "李天豪",
  "age": 35,
  "background": "富二代，继承家族企业",
  "personality": ["傲慢", "狠辣", "聪明"],
  "goal": "打压新兴竞争对手",
  "wealth_tier": "富豪",
  "occupation": "集团副总裁",
  "skills": ["商业谈判", "人脉资源", "资本运作"]
}
</examples>

现在，基于以下信息生成角色：
{user_input}
```

### 3. Chain-of-Thought Prompting

**用途**：复杂推理任务（大纲生成、情节设计）

```xml
<task>
生成都市商战小说的完整大纲。

请按以下步骤思考：

第1步：分析用户输入
- 核心冲突是什么？
- 主角的起点和终点？
- 目标读者期待什么？

第2步：设计故事结构
- 分几个故事弧？
- 每个故事弧的主要冲突？
- 如何安排高潮和低谷？

第3步：设计角色成长
- 主角如何从{{ start_tier }}进阶到{{ end_tier }}？
- 每个阶段需要多少章节？
- 关键转折点在哪里？

第4步：输出完整大纲
- 按照标准格式输出
- 每个故事弧包含章节范围、冲突、目标

让我们开始：
</task>
```

### 4. 结构化输出

**使用JSON Schema约束输出**

```python
# 定义Schema
CHARACTER_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer", "minimum": 1, "maximum": 100},
        "gender": {"type": "string", "enum": ["male", "female", "other"]},
        "personality_traits": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 5
        },
        "wealth_tier": {
            "type": "string",
            "enum": ["贫困线", "温饱", "小康", "中产", "富裕", "富豪"]
        }
    },
    "required": ["name", "age", "gender", "personality_traits", "wealth_tier"]
}

# Prompt中指定
<output_format>
输出必须是有效的JSON，符合以下Schema：
{json.dumps(CHARACTER_SCHEMA, indent=2, ensure_ascii=False)}
</output_format>
```

### 5. 负面示例（避免错误）

```xml
<negative_examples>
❌ 错误示例1（违反题材）：
"陈阳突然感觉体内灵气涌动，修为突破到了筑基期。"
→ 都市题材禁止修炼元素

❌ 错误示例2（过于夸张）：
"陈阳一夜之间就从月薪5000变成了身价百亿的富豪。"
→ 违反合理性，缺少过渡

❌ 错误示例3（字数不够）：
"陈阳去公司上班。他很努力。老板很满意。"
→ 内容过于简单，缺少细节

请避免以上错误。
</negative_examples>
```

---

## 🎨 Prompt模板管理

### 1. 模板组织结构

```
prompts/
├── genesis/                    # 创世阶段
│   ├── urban/
│   │   ├── outline.j2
│   │   ├── character.j2
│   │   └── worldview.j2
│   ├── xuanhuan/
│   │   ├── outline.j2
│   │   ├── character.j2
│   │   └── worldview.j2
│   └── base/                   # 基础模板（继承）
│       ├── outline_base.j2
│       └── character_base.j2
│
├── production/                 # 生产阶段
│   ├── urban/
│   │   ├── chapter.j2
│   │   ├── dialogue.j2
│   │   └── revision.j2
│   └── xuanhuan/
│       ├── chapter.j2
│       └── battle_scene.j2
│
├── validation/                 # 验证阶段
│   ├── genre_check.j2
│   ├── quality_check.j2
│   └── consistency_check.j2
│
└── shared/                     # 共享片段
    ├── genre_definitions/
    │   ├── urban.j2
    │   └── xuanhuan.j2
    └── style_guides/
        ├── dialogue.j2
        └── description.j2
```

### 2. Jinja2模板使用

#### 基础模板（继承）

```jinja2
{# prompts/genesis/base/character_base.j2 #}
<system_context>
你是一位专业的{{ genre_name }}网络小说作者。
</system_context>

<genre_definition>
{% include 'shared/genre_definitions/' + genre_id + '.j2' %}
</genre_definition>

<task>
{% block task %}
{# 子模板覆盖 #}
{% endblock %}
</task>

<constraints>
{% block constraints %}
- 角色必须符合题材设定
- 性格鲜明，有成长空间
{% endblock %}
</constraints>

<output_format>
{% block output_format %}
输出JSON格式的角色信息
{% endblock %}
</output_format>
```

#### 具体模板（继承基础模板）

```jinja2
{# prompts/genesis/urban/character.j2 #}
{% extends "genesis/base/character_base.j2" %}

{% block task %}
生成都市题材的{{ role }}角色。

用户需求：
{{ user_input }}

角色定位：
- 在故事中的作用：{{ role_description }}
- 与主角的关系：{{ relationship_to_protagonist }}
{% endblock %}

{% block constraints %}
{{ super() }}  {# 继承父模板的约束 #}
- 必须有明确的财富等级（贫困线/温饱/小康/中产/富裕/富豪）
- 必须有具体的职业和社会地位
- 背景故事要真实可信
{% endblock %}

{% block output_format %}
输出JSON格式，包含以下字段：
- name: 姓名
- age: 年龄
- gender: 性别
- personality_traits: 性格特征（3-5个）
- background: 背景故事
- wealth_tier: 财富等级
- occupation: 职业
- skills: 技能列表
{% endblock %}
```

### 3. 模板版本控制

```python
# core/prompts/manager.py
from jinja2 import Environment, FileSystemLoader
from typing import Dict, Any
import hashlib

class PromptManager:
    """Prompt模板管理器"""
    
    def __init__(self, templates_dir: str = "prompts"):
        self.env = Environment(loader=FileSystemLoader(templates_dir))
        self.cache = {}  # 渲染缓存
    
    def render(
        self,
        template_path: str,
        context: Dict[str, Any],
        version: str = "latest"
    ) -> str:
        """渲染Prompt模板
        
        Args:
            template_path: 模板路径（如"genesis/urban/character.j2"）
            context: 上下文变量
            version: 模板版本（用于A/B测试）
        
        Returns:
            渲染后的Prompt
        """
        # 生成缓存键
        cache_key = self._get_cache_key(template_path, context, version)
        
        # 检查缓存
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # 加载模板
        if version != "latest":
            template_path = f"{version}/{template_path}"
        
        template = self.env.get_template(template_path)
        
        # 渲染
        result = template.render(**context)
        
        # 存缓存
        self.cache[cache_key] = result
        
        return result
    
    def _get_cache_key(
        self,
        template_path: str,
        context: Dict[str, Any],
        version: str
    ) -> str:
        """生成缓存键"""
        key_data = f"{template_path}:{version}:{str(sorted(context.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
```

---

## 💰 成本优化策略

### 1. 缓存策略

#### Redis缓存层

```python
from infrastructure.cache import RedisCache
import hashlib

class LLMCache:
    """LLM响应缓存"""
    
    def __init__(self, redis: RedisCache):
        self.redis = redis
    
    async def get_or_generate(
        self,
        prompt: str,
        generator_func,
        ttl: int = 3600,
        cache_key_extra: str = ""
    ):
        """获取缓存或生成新内容"""
        # 生成缓存键
        cache_key = self._make_key(prompt, cache_key_extra)
        
        # 检查缓存
        cached = await self.redis.get(cache_key)
        if cached:
            return cached
        
        # 生成新内容
        result = await generator_func(prompt)
        
        # 存缓存
        await self.redis.set(cache_key, result, ttl=ttl)
        
        return result
    
    def _make_key(self, prompt: str, extra: str = "") -> str:
        """生成缓存键"""
        key_data = f"llm:{prompt}{extra}"
        return hashlib.sha256(key_data.encode()).hexdigest()
```

#### 缓存策略矩阵

| 内容类型 | 是否缓存 | TTL | 原因 |
|---------|---------|-----|------|
| 大纲生成 | ✅ | 7天 | 相同输入结果相似 |
| 角色生成 | ✅ | 7天 | 可复用 |
| 世界观生成 | ✅ | 7天 | 可复用 |
| 章节生成 | ❌ | - | 每次都应该不同 |
| 题材验证 | ✅ | 1小时 | 相同内容结果一致 |
| 质量检查 | ✅ | 1小时 | 相同内容结果一致 |

### 2. Prompt压缩

#### Token计数和优化

```python
import tiktoken

class PromptOptimizer:
    """Prompt优化器"""
    
    def __init__(self):
        self.encoder = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """计算Token数"""
        return len(self.encoder.encode(text))
    
    def compress_context(
        self,
        context: str,
        max_tokens: int = 4000
    ) -> str:
        """压缩上下文"""
        current_tokens = self.count_tokens(context)
        
        if current_tokens <= max_tokens:
            return context
        
        # 策略1：移除示例
        if "<examples>" in context:
            context = self._remove_section(context, "examples")
            if self.count_tokens(context) <= max_tokens:
                return context
        
        # 策略2：缩短描述
        context = self._shorten_descriptions(context)
        if self.count_tokens(context) <= max_tokens:
            return context
        
        # 策略3：截断
        return self._truncate_to_tokens(context, max_tokens)
    
    def optimize_for_cost(self, prompt: str) -> str:
        """成本优化"""
        # 移除多余空白
        prompt = self._remove_extra_whitespace(prompt)
        
        # 使用缩写（在不影响理解的情况下）
        prompt = self._use_abbreviations(prompt)
        
        return prompt
```

### 3. 批处理

**场景**：一次生成多个相似内容

```python
async def batch_generate_characters(
    character_descriptions: List[str],
    genre_id: str
) -> List[Character]:
    """批量生成角色"""
    # 合并为一个Prompt
    prompt = f"""
生成以下{len(character_descriptions)}个角色：

{% for desc in character_descriptions %}
角色{{ loop.index }}：
{desc}

{% endfor %}

输出JSON数组，每个元素是一个角色对象。
"""
    
    # 一次调用生成多个
    result = await llm.generate(prompt, max_tokens=8000)
    
    # 解析
    characters_data = json.loads(result)
    
    return [Character(**data) for data in characters_data]
```

**节省**：
- 10个角色分别生成：10次调用 = $1.80
- 10个角色批量生成：1次调用 = $0.36
- **节省80%**

---

## 🔄 错误处理与重试

### 1. 重试策略

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import anthropic

class LLMClient:
    """LLM客户端（带重试）"""
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((
            anthropic.RateLimitError,
            anthropic.APIConnectionError,
            anthropic.APITimeoutError
        ))
    )
    async def generate_with_retry(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """带重试的生成"""
        try:
            return await self.client.messages.create(
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
        except anthropic.RateLimitError as e:
            # 速率限制，等待后重试
            logger.warning(f"Rate limit hit: {e}")
            raise
        except anthropic.APIError as e:
            # API错误，记录后重试
            logger.error(f"API error: {e}")
            raise
```

### 2. 降级策略

```python
async def generate_with_fallback(
    prompt: str,
    primary_model: str = "claude-sonnet-4",
    fallback_model: str = "claude-haiku-4"
) -> str:
    """带降级的生成"""
    try:
        # 尝试主模型
        return await llm.generate(prompt, model=primary_model)
    except Exception as e:
        logger.warning(f"Primary model failed: {e}, falling back to {fallback_model}")
        
        # 降级到备用模型
        try:
            return await llm.generate(prompt, model=fallback_model)
        except Exception as e2:
            logger.error(f"Fallback model also failed: {e2}")
            raise
```

### 3. 输出验证

```python
async def generate_with_validation(
    prompt: str,
    validator_func,
    max_retries: int = 3
) -> str:
    """带验证的生成"""
    for attempt in range(max_retries):
        # 生成
        result = await llm.generate(prompt)
        
        # 验证
        is_valid, errors = validator_func(result)
        
        if is_valid:
            return result
        
        # 验证失败，添加反馈重新生成
        logger.warning(f"Validation failed (attempt {attempt + 1}): {errors}")
        
        prompt = self._add_feedback_to_prompt(prompt, errors)
    
    raise ValueError(f"Failed to generate valid output after {max_retries} attempts")

def _add_feedback_to_prompt(self, original_prompt: str, errors: List[str]) -> str:
    """添加反馈到Prompt"""
    feedback = "\n".join(f"- {error}" for error in errors)
    
    return f"""{original_prompt}

<previous_attempt_issues>
上一次生成有以下问题：
{feedback}

请修正这些问题后重新生成。
</previous_attempt_issues>
"""
```

---

## 📊 质量监控

### 1. LLM调用追踪

```python
from dataclasses import dataclass
from datetime import datetime
import uuid

@dataclass
class LLMCallLog:
    """LLM调用日志"""
    call_id: str
    timestamp: datetime
    model: str
    prompt: str
    response: str
    input_tokens: int
    output_tokens: int
    cost: float
    latency_ms: int
    success: bool
    error: Optional[str] = None

class LLMTracker:
    """LLM调用追踪器"""
    
    async def track_call(
        self,
        model: str,
        prompt: str,
        generate_func
    ) -> tuple[str, LLMCallLog]:
        """追踪一次LLM调用"""
        call_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            # 执行调用
            result = await generate_func()
            
            # 计算指标
            latency = (datetime.now() - start_time).total_seconds() * 1000
            input_tokens = self._count_tokens(prompt)
            output_tokens = self._count_tokens(result)
            cost = self._calculate_cost(model, input_tokens, output_tokens)
            
            # 记录
            log = LLMCallLog(
                call_id=call_id,
                timestamp=start_time,
                model=model,
                prompt=prompt,
                response=result,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                latency_ms=int(latency),
                success=True
            )
            
            await self._save_log(log)
            
            return result, log
        
        except Exception as e:
            # 记录失败
            log = LLMCallLog(
                call_id=call_id,
                timestamp=start_time,
                model=model,
                prompt=prompt,
                response="",
                input_tokens=self._count_tokens(prompt),
                output_tokens=0,
                cost=0,
                latency_ms=0,
                success=False,
                error=str(e)
            )
            
            await self._save_log(log)
            
            raise
```

### 2. 质量指标

```python
async def evaluate_chapter_quality(chapter_content: str) -> Dict[str, float]:
    """评估章节质量"""
    metrics = {}
    
    # 1. 字数检查
    word_count = len(chapter_content)
    metrics["word_count_score"] = min(1.0, word_count / 2000)
    
    # 2. 对话比例
    dialogue_ratio = calculate_dialogue_ratio(chapter_content)
    metrics["dialogue_ratio"] = dialogue_ratio  # 期望20-40%
    
    # 3. 段落长度分布
    paragraph_lengths = [len(p) for p in chapter_content.split("\n\n")]
    avg_paragraph_length = sum(paragraph_lengths) / len(paragraph_lengths)
    metrics["paragraph_balance"] = 1.0 if 50 < avg_paragraph_length < 200 else 0.5
    
    # 4. 题材符合度（使用LLM快速检查）
    genre_check_prompt = f"""
请快速评估以下内容是否符合都市题材（0-10分）：
{chapter_content[:500]}...

只回答分数，不要解释。
"""
    genre_score_str = await llm.generate(genre_check_prompt, model="claude-haiku-4", max_tokens=10)
    genre_score = float(genre_score_str.strip()) / 10.0
    metrics["genre_compliance"] = genre_score
    
    # 5. 综合评分
    metrics["overall_score"] = sum(metrics.values()) / len(metrics)
    
    return metrics
```

---

## 🎯 实施建议

### Phase 1（MVP）

**实现**：
- Anthropic SDK集成
- 基础Prompt模板（Jinja2）
- 简单缓存（Redis）
- 基础错误处理
- Sonnet为主力模型

**不做**：
- 复杂的Prompt优化
- 多模型切换
- 高级监控

### Phase 2（优化）

**添加**：
- LiteLLM多模型
- Prompt版本管理
- A/B测试
- 成本优化
- 质量监控

### Phase 3（高级）

**添加**：
- 自动Prompt优化
- 强化学习反馈
- 自定义模型微调

---

## 📚 参考资源

### 官方文档
- Anthropic Prompt Engineering: https://docs.anthropic.com/claude/docs/prompt-engineering
- Claude Best Practices: https://docs.anthropic.com/claude/docs/best-practices

### 工具
- Jinja2: https://jinja.palletsprojects.com/
- tiktoken: https://github.com/openai/tiktoken
- LiteLLM: https://docs.litellm.ai/

---

**LLM集成策略文档完成！** ✅

今天第一批（3个核心文档）全部完成：
1. ✅ 14_TECHNICAL_STACK_SELECTION.md（933行）
2. ✅ 15_SYSTEM_ARCHITECTURE_DESIGN.md（1,147行）
3. ✅ 16_LLM_INTEGRATION_STRATEGY.md（当前文档）

总计：~3,300行高质量架构文档
