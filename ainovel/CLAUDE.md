# AINovel 项目架构改进计划

## 当前严重缺陷
项目设计时隐含假设了玄幻/奇幻题材，导致无法正确生成都市、历史、科幻等其他题材。这是架构层面的失误。

## 紧急修复计划（P0）

### 1. 题材系统重构
**目标**：让每个题材有独立的配置和生成逻辑

#### 1.1 创建题材配置系统
```
runtime/genre/
  ├── base.py          # 题材基类
  ├── urban.py         # 都市题材配置
  ├── fantasy.py       # 奇幻题材配置
  ├── xuanhuan.py      # 玄幻题材配置
  ├── historical.py    # 历史题材配置
  └── scifi.py         # 科幻题材配置
```

每个题材配置包含：
- 关键词库（用于参考小说识别）
- 核心要素定义（都市=财富/地位，玄幻=境界/修为）
- Prompt 模板（题材专用）
- Schema 变体（power_system vs wealth_system）

#### 1.2 修复 analyzer.py
**当前问题**：关键词过于简单，《我真没想重生啊》被误判为奇幻

**改进方案**：
```python
GENRE_HINTS = {
    "都市": {
        "positive": ["公司", "创业", "职场", "商业", "投资", "股票", 
                    "房地产", "互联网", "校园", "高考", "大学"],
        "negative": ["灵气", "修炼", "魔法", "穿越时空"],
        "keywords_重生": ["重生", "回到过去", "再来一次"]
    },
    "玄幻": {
        "positive": ["灵气", "修炼", "宗门", "丹药", "境界", "突破"],
        "negative": ["公司", "股票", "互联网"]
    }
}
```

添加：
- 正向关键词（强化题材识别）
- 负向关键词（排除其他题材）
- 子类型标签（重生、穿越、系统）

#### 1.3 重构 LLM Prompt 模板
**当前问题**：通用模板无法约束题材

**改进方案**：
```python
# runtime/outline/prompts/
urban_rebirth_template.txt   # 都市重生专用
urban_system_template.txt    # 都市系统流专用
fantasy_leveling_template.txt # 奇幻升级流专用
```

每个模板：
- 明确题材定义和禁忌
- 提供该题材的示例结构
- 强制约束（如都市禁止魔法）

#### 1.4 Power System 题材化
**当前问题**：强制所有题材使用 power_system（力量层级）

**改进方案**：
```python
# 抽象基类
class ProgressionSystem:
    tiers: List[str]
    breakthrough_condition: str
    
# 题材专用实现
class PowerSystem(ProgressionSystem):  # 玄幻/奇幻
    """灵气修炼、境界突破"""
    
class WealthSystem(ProgressionSystem):  # 都市
    """财富积累、社会地位"""
    tiers = ["打工仔", "小老板", "企业家", "资本家", "商业帝国"]
    
class TechSystem(ProgressionSystem):  # 科幻
    """科技等级、文明进化"""
```

### 2. Genesis 流程题材感知
**当前问题**：genesis 不关心题材，生成逻辑是通用的

**改进方案**：
```python
def run_genesis(project_path, model=None, genre_override=None):
    # 1. 识别题材
    genre = genre_override or detect_genre_from_references(project_path)
    
    # 2. 加载题材配置
    genre_config = load_genre_config(genre)
    
    # 3. 使用题材专用分析器
    analyzer = genre_config.get_analyzer()
    
    # 4. 使用题材专用 Prompt
    prompt_template = genre_config.get_prompt_template()
    
    # 5. 使用题材专用 Schema
    schema = genre_config.get_schema()
```

### 3. 测试覆盖
**当前问题**：没有跨题材的集成测试

**新增测试**：
```
tests/
  ├── test_genre_urban_rebirth.py      # 都市重生
  ├── test_genre_fantasy_leveling.py   # 奇幻升级
  ├── test_genre_xuanhuan_sect.py      # 玄幻宗门
  └── test_genre_detection.py          # 题材识别准确率
```

每个测试：
- 提供该题材的参考小说
- 验证 genesis 生成的内容符合题材
- 检查没有其他题材的元素混入

## 实施优先级

### P0（紧急，必须立即修复）
1. ✅ 临时方案：手动创建 facts（已完成）
2. 🔴 修复 analyzer.py 关键词库
3. 🔴 为都市/玄幻创建独立 Prompt 模板
4. 🔴 添加题材检测覆盖测试

### P1（重要，本周内完成）
1. 创建 runtime/genre/ 模块
2. 重构 ProgressionSystem 抽象
3. 修改 genesis 支持题材配置注入

### P2（优化，迭代改进）
1. 扩展更多题材支持（历史、科幻、仙侠）
2. LLM 辅助题材识别
3. 题材混搭支持（都市修仙）

## 责任追溯
**架构师失职点**：
1. ❌ 初期设计未考虑题材多样性
2. ❌ 将玄幻范式（power system）硬编码为通用设计
3. ❌ 缺少题材隔离的架构分层
4. ❌ 测试覆盖不足，未发现题材偏向

## 改进措施
1. 所有新功能必须明确"是否题材相关"
2. Schema 设计必须考虑跨题材适用性
3. Prompt 模板按题材分目录管理
4. 集成测试必须覆盖至少3种题材

## 当前状态
- 🔴 都市题材：genesis 失败，手动创建 facts 可生成
- 🟡 玄幻题材：未经测试（推测可以，因为代码隐含偏向玄幻）
- 🔴 其他题材：完全不支持

---
**修复承诺**：7天内完成 P0+P1 改造，让项目支持都市/玄幻/奇幻三大题材独立生成。

## 立即行动项（今天完成）

### Action 1: 修复 analyzer.py 关键词库
**文件**：`AI-Novel-Runtime/runtime/outline/analyzer.py`

**修改**：
```python
GENRE_HINTS = {
    "都市": ["公司", "创业", "职场", "商业", "投资", "股票", "城市", 
             "校园", "高考", "大学", "互联网", "房地产", "金融"],
    "都市重生": ["重生", "回到", "再来一次", "前世", "这一世"],
    "玄幻": ["灵气", "修炼", "宗门", "丹药", "神通", "境界", "法宝"],
    "仙侠": ["飞剑", "道心", "仙门", "渡劫", "元婴", "天劫", "仙缘"],
    "奇幻": ["王国", "魔法", "骑士", "龙", "精灵", "诅咒", "魔导"],
    "科幻": ["星舰", "宇宙", "殖民", "人工智能", "量子", "机甲", "星际"],
}

# 添加负向关键词排除
GENRE_CONFLICTS = {
    "都市": ["灵气", "修炼", "魔法", "修仙"],  # 都市不能有这些
    "玄幻": ["公司", "股票", "互联网"],       # 玄幻不能有这些
}
```

### Action 2: 为都市题材创建专用 Prompt
**新建文件**：`AI-Novel-Runtime/runtime/outline/prompts/urban.py`

```python
URBAN_PROPOSE_TEMPLATE = """你是都市网文主编，为都市现实题材小说设计大纲。

# 严格约束
1. 必须是现代都市背景（2000年后）
2. 场景必须真实：公司、学校、商场、居民区等
3. 冲突必须现实：商业竞争、职场斗争、感情纠葛、家庭矛盾
4. 可以有重生/系统等金手指，但不能违反物理规律
5. **绝对禁止**：魔法、修仙、异能、灵气、境界、法宝等超自然元素

# 都市题材金手指示例
- 重生（回到过去，记忆完整）
- 系统（提供任务和奖励，但奖励是现实的）
- 预知未来（知道股票、彩票、商机）
- 特殊技能（超强记忆力、商业天赋）

# 都市题材进阶系统
都市小说的"升级"体现在：
- 财富等级：贫困 → 温饱 → 小康 → 富裕 → 富豪 → 资本家
- 社会地位：学生 → 职员 → 主管 → 经理 → 老板 → 企业家
- 影响力：无名小卒 → 小有名气 → 行业新秀 → 业界大佬 → 传奇人物

请生成 {n} 个都市题材候选大纲...
"""
```

### Action 3: 修改 llm_agents.py 使用题材专用模板
**文件**：`AI-Novel-Runtime/runtime/outline/llm_agents.py`

在 `propose` 方法中：
```python
def propose(self, merged_analysis: dict) -> List[dict]:
    genre_signals = merged_analysis.get("genre_signals", [])
    primary_genre = genre_signals[0] if genre_signals else "待判定"
    
    # 选择题材专用模板
    if primary_genre == "都市" or "重生" in str(genre_signals):
        from .prompts.urban import URBAN_PROPOSE_TEMPLATE
        template = URBAN_PROPOSE_TEMPLATE
    else:
        template = _PROPOSE_TEMPLATE  # 默认通用模板
    
    prompt = template.format(analysis=_analysis_brief(merged_analysis), n=self.n)
    ...
```

