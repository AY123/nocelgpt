# Genre 系统架构设计文档

**版本**: v2.0  
**状态**: 设计阶段  
**优先级**: P0（核心架构缺陷修复）  
**预计工期**: 2-3 周  

---

## 一、问题诊断

### 1.1 V1 架构缺陷

**根本问题**: Genre 被当作字符串标签，而非领域模型

```python
# ❌ V1 错误方式
genre = "都市"  # 只是个字符串
prompt = UNIVERSAL_TEMPLATE.format(genre=genre)  # 通用模板
outline = model.call(prompt)  # 生成什么是什么，无约束
```

**后果**:
- 都市小说生成修炼内容
- 玄幻小说出现现代公司
- 类型污染无法检测
- 无法在生成前强制约束

### 1.2 核心矛盾

**Power System 被错误通用化**:

```python
# ❌ V1 的错误假设
class Character:
    power_level: int          # 所有题材都用"力量等级"
    cultivation_stage: str    # 所有题材都用"修炼阶段"
```

这对玄幻小说是对的，但对都市小说完全错误。

都市小说的进阶应该是：
- 财富等级：贫困 → 小康 → 富裕 → 富豪
- 社会地位：学生 → 职员 → 经理 → 老板 → 企业家
- 影响力：无名 → 小有名气 → 业界大佬

### 1.3 设计目标

**V2 必须实现**:
1. ✅ Genre 是一等公民领域模型
2. ✅ 每个题材有独立的约束、进阶模型、Prompt 模板
3. ✅ 题材约束可执行、可验证
4. ✅ 跨题材污染可检测、可阻断
5. ✅ 题材检测准确率 > 90%

---

## 二、核心概念模型

### 2.1 GenreConfig（题材配置）

**定义**: 一个题材的完整规范，包含约束、进阶模型、模板、检测器

```python
@dataclass
class GenreConfig:
    """题材完整配置"""
    
    # 元数据
    genre_id: str              # 题材 ID（urban/xuanhuan/xianxia）
    genre_name: str            # 题材中文名（都市/玄幻/仙侠）
    parent_genre: Optional[str] # 父题材（如"都市重生"的父题材是"都市"）
    
    # 约束系统
    constraints: GenreConstraints
    
    # 进阶模型
    progression_model: GenreProgressionModel
    
    # Prompt 模板
    prompt_templates: Dict[str, str]  # outline/chapter/revision
    
    # 检测器
    keyword_detector: KeywordDetector
    reference_analyzer: ReferenceAnalyzer
    
    # 质量标准
    quality_rubric: Optional[QualityRubric]
```

### 2.2 GenreConstraints（题材约束）

**定义**: 题材的硬约束规则，用于生成时验证

```python
@dataclass
class GenreConstraints:
    """题材硬约束"""
    
    # 元素约束
    allowed_elements: List[str]      # 允许的核心元素
    forbidden_elements: List[str]    # 禁止的元素（跨题材污染源）
    
    # 世界规则约束
    required_world_rules: List[str]  # 必需的世界规则
    forbidden_world_rules: List[str] # 禁止的世界规则
    
    # 场景约束
    allowed_scenes: List[str]        # 允许的场景类型
    forbidden_scenes: List[str]      # 禁止的场景
    
    # 角色约束
    allowed_character_types: List[str]
    forbidden_character_types: List[str]
    
    # 冲突约束
    allowed_conflict_types: List[str]
    forbidden_conflict_types: List[str]

# 示例：都市题材约束
URBAN_CONSTRAINTS = GenreConstraints(
    allowed_elements=[
        "重生", "系统", "预知", "超强记忆", "商业天赋",
        "校园", "职场", "商战", "感情", "家庭"
    ],
    forbidden_elements=[
        "灵气", "修炼", "魔法", "境界", "法宝", "丹药",
        "宗门", "仙门", "异能", "超自然力量"
    ],
    required_world_rules=[
        "现代物理规律", "真实社会结构", "市场经济规则"
    ],
    forbidden_world_rules=[
        "修仙体系", "魔法体系", "力量等级压制"
    ],
    allowed_scenes=[
        "学校", "公司", "商场", "居民区", "CBD", "创业园区",
        "酒店", "餐厅", "机场", "高档小区"
    ],
    forbidden_scenes=[
        "修炼洞府", "宗门", "秘境", "魔法学院", "异世界"
    ],
    allowed_character_types=[
        "学生", "职员", "老板", "企业家", "明星", "网红",
        "教师", "医生", "律师", "投资人"
    ],
    forbidden_character_types=[
        "修炼者", "魔法师", "剑客", "宗门长老", "仙人"
    ],
    allowed_conflict_types=[
        "商业竞争", "职场斗争", "情感纠葛", "家庭矛盾",
        "阶层跨越", "资源争夺", "利益冲突"
    ],
    forbidden_conflict_types=[
        "境界突破", "宗门大比", "夺宝争斗", "天劫渡劫"
    ]
)

# 示例：玄幻题材约束
XUANHUAN_CONSTRAINTS = GenreConstraints(
    allowed_elements=[
        "灵气", "修炼", "境界", "丹药", "法宝", "功法",
        "宗门", "秘境", "天才", "废材逆袭"
    ],
    forbidden_elements=[
        "公司", "股票", "互联网", "现代科技", "创业",
        "职场", "商战"
    ],
    required_world_rules=[
        "修炼体系", "力量等级", "境界压制"
    ],
    forbidden_world_rules=[
        "现代物理规律（在修炼世界）", "市场经济（在宗门）"
    ],
    allowed_scenes=[
        "宗门", "秘境", "古城", "修炼洞府", "争霸大陆",
        "炼丹房", "藏经阁", "试炼场"
    ],
    forbidden_scenes=[
        "现代学校", "公司办公室", "商场", "CBD", "互联网公司"
    ],
    allowed_character_types=[
        "修炼者", "宗门弟子", "长老", "掌门", "散修",
        "炼丹师", "炼器师"
    ],
    forbidden_character_types=[
        "现代学生", "公司职员", "企业家", "程序员"
    ],
    allowed_conflict_types=[
        "境界突破", "宗门争斗", "天才之战", "机缘争夺",
        "复仇崛起", "天劫"
    ],
    forbidden_conflict_types=[
        "商业竞争", "职场斗争", "创业融资"
    ]
)
```

### 2.3 GenreProgressionModel（进阶模型抽象）

**设计理念**: 不同题材的"进阶"有完全不同的语义

```python
from abc import ABC, abstractmethod

class GenreProgressionModel(ABC):
    """题材进阶模型抽象基类"""
    
    @property
    @abstractmethod
    def tiers(self) -> List[str]:
        """等级列表"""
        pass
    
    @property
    @abstractmethod
    def tier_descriptions(self) -> Dict[str, str]:
        """每个等级的描述"""
        pass
    
    @property
    @abstractmethod
    def breakthrough_mechanics(self) -> str:
        """晋级机制描述"""
        pass
    
    @abstractmethod
    def validate_transition(self, from_tier: str, to_tier: str) -> Tuple[bool, str]:
        """
        验证晋级是否合理
        
        Returns:
            (是否合理, 原因)
        """
        pass
    
    @abstractmethod
    def get_tier_index(self, tier: str) -> int:
        """获取等级序号"""
        pass
    
    def can_skip_tier(self) -> bool:
        """是否允许跳级"""
        return False
```

#### 2.3.1 PowerProgressionModel（力量进阶 - 玄幻/奇幻/仙侠）

```python
class PowerProgressionModel(GenreProgressionModel):
    """力量进阶模型（修炼体系）"""
    
    @property
    def tiers(self) -> List[str]:
        return [
            "炼气期",
            "筑基期", 
            "金丹期",
            "元婴期",
            "化神期",
            "合体期",
            "渡劫期",
            "大乘期"
        ]
    
    @property
    def tier_descriptions(self) -> Dict[str, str]:
        return {
            "炼气期": "修炼入门，吸收天地灵气，淬炼肉身",
            "筑基期": "构建修炼根基，灵力初成",
            "金丹期": "凝聚金丹，灵力质变，寿命延长",
            "元婴期": "元婴出窍，神识大增，初步掌握空间",
            "化神期": "元婴化神，法则初悟，可御空飞行",
            "合体期": "人法合一，天地之力为我所用",
            "渡劫期": "面临天劫考验，生死一线",
            "大乘期": "渡劫成功，圆满境界，飞升在即"
        }
    
    @property
    def breakthrough_mechanics(self) -> str:
        return """
修炼突破需要：
1. 足够的修炼积累（灵力/感悟）
2. 机缘（天材地宝/丹药/传承）
3. 生死磨练（战斗/试炼）
4. 心境突破（顿悟/执念解开）
5. 天劫考验（高阶需要）
"""
    
    def validate_transition(self, from_tier: str, to_tier: str) -> Tuple[bool, str]:
        """验证修为突破是否合理"""
        if from_tier not in self.tiers or to_tier not in self.tiers:
            return False, f"无效的境界: {from_tier} -> {to_tier}"
        
        from_idx = self.get_tier_index(from_tier)
        to_idx = self.get_tier_index(to_tier)
        
        # 修炼体系一般不允许跳级
        if to_idx - from_idx > 1:
            return False, f"境界跨度过大，不符合修炼规律"
        
        if to_idx <= from_idx:
            return False, f"境界倒退或原地踏步"
        
        return True, "合理的境界突破"
    
    def get_tier_index(self, tier: str) -> int:
        return self.tiers.index(tier)
```

#### 2.3.2 WealthProgressionModel（财富进阶 - 都市）

```python
class WealthProgressionModel(GenreProgressionModel):
    """财富进阶模型（都市体系）"""
    
    @property
    def tiers(self) -> List[str]:
        return [
            "贫困线",
            "温饱",
            "小康",
            "中产",
            "富裕",
            "富豪",
            "资本家",
            "商业帝国"
        ]
    
    @property
    def tier_descriptions(self) -> Dict[str, str]:
        return {
            "贫困线": "月入 < 3000，勉强维持生活",
            "温饱": "月入 5000-10000，基本生活无忧",
            "小康": "月入 2-5 万，有一定储蓄",
            "中产": "年入 50-100 万，有房有车",
            "富裕": "资产 500 万-5000 万，财务自由",
            "富豪": "资产 5000 万-10 亿，影响一方",
            "资本家": "资产 10 亿+，掌控产业链",
            "商业帝国": "资产千亿+，行业定义者"
        }
    
    @property
    def breakthrough_mechanics(self) -> str:
        return """
财富进阶需要：
1. 商业机会（风口/内幕消息/独特洞察）
2. 资源整合（人脉/资金/技术/渠道）
3. 战略眼光（市场判断/时机把握）
4. 执行能力（团队/管理/落地）
5. 风险控制（不能一夜爆雷）
"""
    
    def validate_transition(self, from_tier: str, to_tier: str) -> Tuple[bool, str]:
        """验证财富增长是否合理"""
        if from_tier not in self.tiers or to_tier not in self.tiers:
            return False, f"无效的财富等级: {from_tier} -> {to_tier}"
        
        from_idx = self.get_tier_index(from_tier)
        to_idx = self.get_tier_index(to_tier)
        
        # 都市题材可以跳级（抓住风口、重生优势）
        if to_idx - from_idx > 2:
            return False, f"财富跨度过大（{from_tier} -> {to_tier}），即使有金手指也需要合理过程"
        
        if to_idx <= from_idx:
            return False, f"财富倒退或停滞"
        
        return True, "合理的财富增长"
    
    def get_tier_index(self, tier: str) -> int:
        return self.tiers.index(tier)
    
    def can_skip_tier(self) -> bool:
        """都市题材允许跳级（抓住风口）"""
        return True
```

#### 2.3.3 TechProgressionModel（科技进阶 - 科幻）

```python
class TechProgressionModel(GenreProgressionModel):
    """科技进阶模型（文明等级）"""
    
    @property
    def tiers(self) -> List[str]:
        return [
            "前工业文明",
            "工业时代",
            "信息时代",
            "星际殖民时代",
            "恒星文明",
            "星系文明",
            "高维文明"
        ]
    
    @property
    def tier_descriptions(self) -> Dict[str, str]:
        return {
            "前工业文明": "农业社会，手工业为主",
            "工业时代": "机械化生产，化石能源",
            "信息时代": "互联网、人工智能、核能",
            "星际殖民时代": "突破光速，殖民太阳系",
            "恒星文明": "戴森球，恒星能源利用",
            "星系文明": "跨星系航行，暗物质利用",
            "高维文明": "维度操控，因果律武器"
        }
    
    @property
    def breakthrough_mechanics(self) -> str:
        return """
科技突破需要：
1. 理论创新（物理学/数学突破）
2. 资源获取（稀有元素/能源）
3. 文明升级（社会结构/生产力）
4. 外部接触（遗迹/外星科技）
5. 危机倒逼（生存威胁）
"""
    
    def validate_transition(self, from_tier: str, to_tier: str) -> Tuple[bool, str]:
        if from_tier not in self.tiers or to_tier not in self.tiers:
            return False, f"无效的科技等级: {from_tier} -> {to_tier}"
        
        from_idx = self.get_tier_index(from_tier)
        to_idx = self.get_tier_index(to_tier)
        
        # 科技树一般不能跳级（除非有外星科技）
        if to_idx - from_idx > 1:
            return False, f"科技等级跨越过大，缺少过渡"
        
        if to_idx <= from_idx:
            return False, f"科技倒退"
        
        return True, "合理的科技进步"
    
    def get_tier_index(self, tier: str) -> int:
        return self.tiers.index(tier)
```

---

## 三、GenreRegistry（题材注册表）

### 3.1 设计目标

**单一职责**: 管理所有题材配置，提供检测和查询

```python
class GenreRegistry:
    """题材注册表（全局单例）"""
    
    _genres: Dict[str, GenreConfig] = {}
    _initialized: bool = False
    
    @classmethod
    def register(cls, config: GenreConfig) -> None:
        """注册一个题材"""
        if config.genre_id in cls._genres:
            raise ValueError(f"Genre {config.genre_id} already registered")
        cls._genres[config.genre_id] = config
        print(f"✅ 注册题材: {config.genre_name} ({config.genre_id})")
    
    @classmethod
    def get(cls, genre_id: str) -> GenreConfig:
        """获取题材配置"""
        if genre_id not in cls._genres:
            raise ValueError(f"Unknown genre: {genre_id}")
        return cls._genres[genre_id]
    
    @classmethod
    def list_all(cls) -> List[str]:
        """列出所有已注册题材"""
        return list(cls._genres.keys())
    
    @classmethod
    def detect_from_references(cls, references: List[str]) -> str:
        """
        从参考文本检测题材
        
        Returns:
            最匹配的 genre_id
        """
        if not cls._genres:
            raise RuntimeError("No genres registered. Call init_genres() first.")
        
        scores = {}
        for genre_id, config in cls._genres.items():
            score = config.keyword_detector.score(references)
            scores[genre_id] = score
        
        best_genre = max(scores, key=scores.get)
        best_score = scores[best_genre]
        
        print(f"📊 题材检测结果: {best_genre} (置信度: {best_score:.2%})")
        for genre_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {genre_id}: {score:.2%}")
        
        return best_genre
    
    @classmethod
    def validate_constraints(cls, genre_id: str, content: str) -> List[str]:
        """
        验证内容是否违反题材约束
        
        Returns:
            违规列表
        """
        config = cls.get(genre_id)
        violations = []
        
        # 检查禁止元素
        for forbidden in config.constraints.forbidden_elements:
            if forbidden in content:
                violations.append(f"包含禁止元素: {forbidden}")
        
        # 检查禁止场景
        for forbidden in config.constraints.forbidden_scenes:
            if forbidden in content:
                violations.append(f"包含禁止场景: {forbidden}")
        
        return violations
```

### 3.2 初始化流程

```python
def init_genres() -> None:
    """初始化所有题材（系统启动时调用）"""
    
    print("🚀 初始化题材系统...")
    
    # 注册都市题材
    register_urban_genre()
    
    # 注册玄幻题材
    register_xuanhuan_genre()
    
    # 注册仙侠题材
    register_xianxia_genre()
    
    # 注册科幻题材
    register_scifi_genre()
    
    # 注册历史题材
    register_historical_genre()
    
    GenreRegistry._initialized = True
    print(f"✅ 题材系统初始化完成，已注册 {len(GenreRegistry.list_all())} 个题材")
```

---

## 四、Prompt 模板系统

### 4.1 题材专用模板结构

```
prompts/
├── urban/
│   ├── outline_v1.txt      # 都市大纲生成
│   ├── chapter_v1.txt      # 都市章节生成
│   └── revision_v1.txt     # 都市修订指导
├── xuanhuan/
│   ├── outline_v1.txt      # 玄幻大纲生成
│   ├── chapter_v1.txt      # 玄幻章节生成
│   └── revision_v1.txt     # 玄幻修订指导
└── shared/
    └── constraints_injection.txt  # 约束注入模板
```

### 4.2 都市 Outline 模板示例

```txt
你是起点中文网资深都市频道主编，拥有 10 年都市题材选稿经验。

## 严格题材约束

### 必须遵守
1. **背景**: 现代都市（2000 年后），真实城市场景
2. **场景**: {allowed_scenes}
3. **冲突**: {allowed_conflicts}
4. **金手指**: {allowed_elements}（不违反物理规律）

### 绝对禁止
- ❌ 元素: {forbidden_elements}
- ❌ 场景: {forbidden_scenes}
- ❌ 世界规则: {forbidden_world_rules}

**违反以上约束将导致大纲被拒绝**

## 都市进阶体系

主角成长不是"修炼突破"，而是：
{progression_tiers_description}

突破机制：
{breakthrough_mechanics}

## 都市爽点设计

### 核心爽点
1. **装逼打脸**: 低调扫货、隐藏身份、碾压质疑者
2. **商战智斗**: 并购、狙击、布局、反杀
3. **美女投怀**: 校花、女总裁、明星、豪门千金
4. **财富暴涨**: 炒股、投资、创业、风口

### 起点都市爆款套路
- 重生都市: 主角重生回到过去，利用先知优势改写人生
- 系统流: 获得系统辅助，完成任务获得奖励
- 预知流: 知道未来风口，提前布局

## 你的任务

基于以下参考分析：
{reference_analysis}

设计一个都市题材大纲，要求：
1. 主角是普通人（可有金手指，但身体是凡人）
2. 前三章在真实场景（学校/公司/家）
3. 每个冲突有现实依据（不能靠魔法解决）
4. 进阶路线是财富/地位/影响力，不是境界/修为

## 约束检查清单（输出前自查）

- [ ] 大纲中没有出现禁止元素？
- [ ] 场景都是现代都市？
- [ ] 冲突都有现实依据？
- [ ] 进阶是财富/地位，不是境界/修为？

输出 JSON 格式大纲...
```

### 4.3 玄幻 Outline 模板示例

```txt
你是起点中文网资深玄幻频道主编，拥有 10 年东方玄幻选稿经验。

## 严格题材约束

### 必须遵守
1. **背景**: 架空修炼世界，有完整修炼体系
2. **场景**: {allowed_scenes}
3. **冲突**: {allowed_conflicts}
4. **核心元素**: {allowed_elements}

### 绝对禁止
- ❌ 元素: {forbidden_elements}
- ❌ 场景: {forbidden_scenes}
- ❌ 世界规则: {forbidden_world_rules}

**违反以上约束将导致大纲被拒绝**

## 玄幻进阶体系

主角成长是"修炼突破"：
{progression_tiers_description}

突破机制：
{breakthrough_mechanics}

## 玄幻爽点设计

### 核心爽点
1. **废材逆袭**: 被退婚、遭驱逐、受羞辱，后归来碾压
2. **越级战斗**: 筑基斩金丹、金丹战元婴
3. **奇遇连连**: 秘境、传承、神器、高人
4. **美女环绕**: 仙子、圣女、郡主、魔女

### 起点玄幻爆款套路
- 废材流: 《斗破苍穹》- 退婚 + 老师 + 逆袭
- 穿越流: 《凡人修仙传》- 小人物 + 苟道 + 机缘
- 扮猪吃虎: 《一念永恒》- 隐藏实力 + 搞笑 + 碾压

## 你的任务

基于以下参考分析：
{reference_analysis}

设计一个玄幻题材大纲，要求：
1. 主角是修炼者
2. 前三章在修炼世界场景（宗门/家族/秘境）
3. 每个冲突与修炼体系相关
4. 进阶路线是境界/修为/战力，不是财富/地位

## 约束检查清单（输出前自查）

- [ ] 大纲中没有出现禁止元素？
- [ ] 场景都是修炼世界？
- [ ] 冲突都与修炼相关？
- [ ] 进阶是境界/修为，不是财富/地位？

输出 JSON 格式大纲...
```

---

## 五、题材检测系统

### 5.1 KeywordDetector（关键词检测器）

```python
class KeywordDetector:
    """基于关键词的题材检测"""
    
    def __init__(
        self,
        positive_keywords: List[str],
        negative_keywords: List[str],
        weights: Optional[Dict[str, float]] = None
    ):
        self.positive_keywords = positive_keywords
        self.negative_keywords = negative_keywords
        self.weights = weights or {}
    
    def score(self, texts: List[str]) -> float:
        """
        计算文本与题材的匹配度
        
        Returns:
            匹配分数 [0, 1]
        """
        combined_text = " ".join(texts).lower()
        
        positive_score = 0.0
        for keyword in self.positive_keywords:
            if keyword in combined_text:
                weight = self.weights.get(keyword, 1.0)
                positive_score += weight
        
        negative_score = 0.0
        for keyword in self.negative_keywords:
            if keyword in combined_text:
                negative_score += 1.0
        
        # 正向得分 - 负向惩罚
        total_score = positive_score - negative_score * 2  # 负向惩罚加倍
        
        # 归一化到 [0, 1]
        max_possible = len(self.positive_keywords) * max(self.weights.values() or [1.0])
        normalized = max(0, total_score) / max_possible if max_possible > 0 else 0
        
        return min(1.0, normalized)

# 都市题材检测器
URBAN_DETECTOR = KeywordDetector(
    positive_keywords=[
        "重生", "回到", "再来一次", "前世", "这一世",  # 重生关键词（高权重）
        "公司", "创业", "职场", "商业", "投资", "股票",
        "校园", "高考", "大学", "学生", "教室",
        "互联网", "房地产", "金融", "风投",
        "都市", "城市", "CBD", "写字楼",
        "系统", "任务", "奖励", "积分"  # 系统流
    ],
    negative_keywords=[
        "灵气", "修炼", "宗门", "境界", "突破", "丹药",
        "魔法", "魔导", "魔力", "法术", "法宝",
        "仙人", "仙门", "飞升", "渡劫"
    ],
    weights={
        "重生": 3.0,  # 重生是都市题材的强信号
        "系统": 2.0,
        "创业": 2.0,
        "公司": 1.5,
        "校园": 1.5
    }
)

# 玄幻题材检测器
XUANHUAN_DETECTOR = KeywordDetector(
    positive_keywords=[
        "灵气", "修炼", "宗门", "丹药", "境界", "突破",
        "法宝", "功法", "神通", "秘境", "传承",
        "废材", "逆袭", "退婚", "家族", "长老",
        "玄幻", "修仙", "仙侠", "东方玄幻"
    ],
    negative_keywords=[
        "公司", "创业", "股票", "互联网", "职场",
        "CBD", "写字楼", "互联网公司", "融资",
        "现代", "都市", "2020", "2021"  # 现代年份
    ],
    weights={
        "修炼": 3.0,
        "境界": 3.0,
        "宗门": 2.5,
        "废材": 2.0,  # 玄幻常见套路
        "退婚": 2.0
    }
)
```

### 5.2 检测准确率测试

```python
def test_genre_detection_accuracy():
    """题材检测准确率测试"""
    
    test_cases = [
        # 都市题材
        (["我真没想重生啊", "主角重生回到2006年"], "urban", 0.8),
        (["重生之财源滚滚", "利用重生优势炒股"], "urban", 0.8),
        (["从学霸开始", "校园创业系统流"], "urban", 0.7),
        
        # 玄幻题材
        (["斗破苍穹", "废材少年被退婚，获得药老"], "xuanhuan", 0.8),
        (["武动乾坤", "符石炼体，宗门争斗"], "xuanhuan", 0.8),
        (["一念永恒", "炼丹搞笑流，扮猪吃虎"], "xuanhuan", 0.7),
        
        # 混淆案例（关键测试）
        (["重生之都市修仙", "主角回到高中，却带着修仙记忆"], "?", 0.5),  # 难以判断
    ]
    
    correct = 0
    total = len(test_cases)
    
    for references, expected_genre, min_confidence in test_cases:
        detected = GenreRegistry.detect_from_references(references)
        
        if expected_genre == "?":
            # 混淆案例，只要有输出就算对
            correct += 1
        elif detected == expected_genre:
            correct += 1
        else:
            print(f"❌ 检测错误: {references}")
            print(f"   期望: {expected_genre}, 实际: {detected}")
    
    accuracy = correct / total
    print(f"\n📊 题材检测准确率: {accuracy:.1%} ({correct}/{total})")
    
    assert accuracy >= 0.9, f"准确率低于 90%: {accuracy:.1%}"
```

---

## 六、实施计划

### Week 1: 核心数据结构

**目标**: GenreConfig、GenreConstraints、ProgressionModel 抽象

```
Day 1-2: 数据结构定义
Day 3-4: Power/Wealth/Tech 三个具体实现
Day 5: 单元测试
```

### Week 2: 题材注册与检测

**目标**: GenreRegistry、KeywordDetector

```
Day 1-2: GenreRegistry 实现
Day 3: 都市/玄幻两个完整配置
Day 4-5: 题材检测测试（准确率 > 90%）
```

### Week 3: Prompt 模板集成

**目标**: 题材专用模板，约束注入

```
Day 1-2: 都市专用模板
Day 3: 玄幻专用模板
Day 4-5: Genesis 流程集成测试
```

---

## 七、验收标准

### M1: Genre 核心重构完成

✅ **数据结构**:
- GenreConfig、GenreConstraints、ProgressionModel 实现
- Power/Wealth/Tech 三个具体模型

✅ **注册表**:
- GenreRegistry 可注册、查询、检测
- 都市、玄幻两个完整配置

✅ **检测准确率**:
- 题材检测准确率 > 90%（10 个测试用例）

✅ **约束验证**:
- 都市题材 5 个测试用例：不生成修炼内容
- 玄幻题材 5 个测试用例：不生成现代商业

✅ **Prompt 模板**:
- 都市、玄幻各有专用 outline/chapter 模板
- 约束自动注入到 prompt

---

## 八、后续扩展

### 8.1 更多题材

- 仙侠（与玄幻的差异：道心、飞剑、天劫更重）
- 科幻（星际、机甲、赛博朋克）
- 历史（架空历史、真实历史）
- 奇幻（西幻、魔法、龙与地下城）
- 游戏（网游、电竞、虚拟现实）

### 8.2 复合题材

- 都市修仙：都市 + 修炼元素（需特殊处理）
- 科幻修仙：科技 + 修炼（星际修仙）
- 历史玄幻：历史背景 + 修炼体系

### 8.3 题材智能

- LLM 辅助题材检测（关键词 + 语义理解）
- 题材融合度检测（判断是否可以合理融合）
- 题材纯度检测（是否偏离核心题材）

---

**文档状态**: 设计完成，待实施  
**下一步**: 生成战略重构路线图
