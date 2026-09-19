# ANovel V2 创作模式架构设计

**版本**: v1.0  
**制定日期**: 2026-09-18  
**状态**: 设计阶段  

---

## 📋 问题定义

### 当前V1的局限

**问题**: V1需要人工提供参考章节，无法从零开始创作

**用户痛点**:
1. 用户有创意但不想写参考章节
2. 用户想基于已有小说创作类似作品
3. 系统无法完全自主创作

### V2需求

**需求1: 创意驱动模式**
- 用户只提供：题材 + 核心创意
- 系统自主完成：世界设定 → 人物设计 → 大纲规划 → 连续生产

**需求2: 参考学习模式**
- 用户提供：1本或多本参考小说
- 系统自主完成：风格学习 → 模式提取 → 创作生产

---

## 🎯 两种创作模式设计

---

## 模式1: 创意驱动模式（Creative Mode）

### 1.1 用户输入

**最小输入**:
```yaml
mode: creative
genre: urban          # 题材
core_idea:            # 核心创意
  premise: "2024年重生回2008年，利用先知优势创业"
  protagonist: "30岁失败创业者"
  core_conflict: "如何在不改变历史的前提下积累财富"
```

**可选输入**:
```yaml
preferences:          # 用户偏好
  tone: serious       # 严肃 / 轻松 / 热血
  pacing: fast        # 快节奏 / 慢节奏
  focus: business     # 商战 / 情感 / 权谋
  target_length: 100  # 目标章节数
```

---

### 1.2 Genesis扩展：从创意到Story Bible

**新增阶段**: Creative Genesis Pipeline

```
用户创意
  ↓
Stage 1: Genre Detection & Validation（题材检测）
  ↓
Stage 2: World Building（世界构建）
  ↓
Stage 3: Character Design（角色设计）
  ↓
Stage 4: Story Bible Generation（故事圣经生成）
  ↓
Stage 5: Long Arc Planning（长弧规划）
  ↓
Stage 6: Outline Generation（大纲生成）
  ↓
Stage 7: First 3 Chapters Mint（前3章铸造）
  ↓
连续生产
```

---

### 1.3 详细设计

#### Stage 1: Genre Detection & Validation

**目的**: 从核心创意推断题材，验证一致性

```python
class CreativeGenreDetector:
    """从创意推断题材"""
    
    def detect_from_idea(self, core_idea: dict) -> GenreDetectionResult:
        """从核心创意检测题材"""
        
        prompt = f"""
分析以下创意，判断最适合的题材。

【创意】
前提: {core_idea['premise']}
主角: {core_idea['protagonist']}
核心冲突: {core_idea['core_conflict']}

【任务】
1. 判断题材（urban/xuanhuan/scifi/...）
2. 识别核心元素（重生/系统/异界/...）
3. 检测题材冲突（如都市设定中出现修炼）
4. 给出置信度

【输出JSON】
{{
    "genre": "urban",
    "confidence": 0.95,
    "core_elements": ["rebirth", "business", "foresight"],
    "conflicts": [],
    "reason": "明确的现代都市背景，重生题材，商业创业主线"
}}
"""
        
        result = llm.generate(prompt, response_format="json")
        
        # 验证题材一致性
        if result["confidence"] < 0.8:
            raise AmbiguousGenreError("创意题材不明确")
        
        if result["conflicts"]:
            raise GenreConflictError(f"创意中存在题材冲突: {result['conflicts']}")
        
        return GenreDetectionResult(**result)
```

---

#### Stage 2: World Building

**目的**: 从创意推导完整世界设定

```python
class WorldBuilder:
    """世界构建器"""
    
    def build_world(self, core_idea: dict, genre_config: GenreConfig) -> WorldSetting:
        """从创意构建世界"""
        
        # 2.1 时空设定
        temporal_setting = self._build_temporal_setting(core_idea)
        
        # 2.2 地理设定
        geographical_setting = self._build_geography(core_idea, genre_config)
        
        # 2.3 社会设定
        social_setting = self._build_society(core_idea, genre_config)
        
        # 2.4 规则设定（题材专用）
        rules = self._build_rules(core_idea, genre_config)
        
        # 2.5 科技/力量体系
        power_system = self._build_power_system(core_idea, genre_config)
        
        return WorldSetting(
            temporal=temporal_setting,
            geography=geographical_setting,
            society=social_setting,
            rules=rules,
            power_system=power_system
        )
    
    def _build_temporal_setting(self, core_idea):
        """构建时空设定"""
        
        prompt = f"""
根据创意，设计时空设定。

【创意】
{format_core_idea(core_idea)}

【设计时空设定】
1. 时间背景（具体年代）
2. 时间跨度（故事覆盖多长时间）
3. 重要时间点（历史事件、转折点）
4. 时间特性（线性/非线性，是否有重生/穿越）

【输出JSON】
{{
    "time_period": "2008-2018",
    "current_time": "2008年1月",
    "time_span": "10年",
    "key_time_points": [
        {{"date": "2008-09", "event": "金融危机"}},
        {{"date": "2010-01", "event": "移动互联网兴起"}},
        ...
    ],
    "time_mechanics": {{
        "type": "rebirth",
        "rebirth_date": "2008-01-01",
        "original_timeline": "2024",
        "can_change_history": false
    }}
}}
"""
        
        return llm.generate(prompt, response_format="json")
    
    def _build_geography(self, core_idea, genre_config):
        """构建地理设定"""
        
        # 都市题材：真实城市 + 虚构细节
        # 玄幻题材：虚构大陆 + 宗门分布
        
        if genre_config.genre_id == "urban":
            return self._build_urban_geography(core_idea)
        elif genre_config.genre_id == "xuanhuan":
            return self._build_xuanhuan_geography(core_idea)
    
    def _build_rules(self, core_idea, genre_config):
        """构建世界规则（题材专用）"""
        
        prompt = f"""
根据题材和创意，定义世界规则。

【题材】{genre_config.genre_name}
【创意】{format_core_idea(core_idea)}

【定义规则】
1. 核心规则（如重生规则、系统规则）
2. 限制条件（主角能做什么、不能做什么）
3. 因果关系（改变过去是否影响未来）
4. 特殊机制（金手指、外挂、系统）

【都市重生规则示例】
{{
    "core_rules": [
        "主角保留前世记忆",
        "历史大势不可改变",
        "小范围可以影响个人命运"
    ],
    "limitations": [
        "不能预知未来彩票号码（太破坏平衡）",
        "不能直接干预国家大事",
        "改变历史有蝴蝶效应风险"
    ],
    "golden_finger": {{
        "type": "foresight",
        "scope": "商业趋势、科技发展、投资机会",
        "limitation": "只知道大方向，不知道具体细节"
    }}
}}
"""
        
        return llm.generate(prompt, response_format="json")
```

---

#### Stage 3: Character Design

**目的**: 设计主要角色

```python
class CharacterDesigner:
    """角色设计器"""
    
    def design_characters(self, 
                         core_idea: dict, 
                         world_setting: WorldSetting,
                         genre_config: GenreConfig) -> List[Character]:
        """设计角色"""
        
        characters = []
        
        # 3.1 主角设计
        protagonist = self._design_protagonist(core_idea, world_setting, genre_config)
        characters.append(protagonist)
        
        # 3.2 主要配角设计（3-5个）
        supporting = self._design_supporting_characters(
            core_idea, 
            protagonist, 
            world_setting,
            genre_config
        )
        characters.extend(supporting)
        
        # 3.3 反派设计（1-2个）
        antagonists = self._design_antagonists(
            core_idea,
            protagonist,
            world_setting,
            genre_config
        )
        characters.extend(antagonists)
        
        return characters
    
    def _design_protagonist(self, core_idea, world_setting, genre_config):
        """设计主角"""
        
        prompt = f"""
设计主角。

【创意】
前提: {core_idea['premise']}
主角设定: {core_idea['protagonist']}
核心冲突: {core_idea['core_conflict']}

【世界设定】
{format_world_setting(world_setting)}

【题材约束】
{format_genre_constraints(genre_config)}

【设计主角】
1. 基础信息（姓名、年龄、性别、外貌）
2. 背景故事（前世经历、重生动机）
3. 性格特点（3-5个核心特质）
4. 能力与技能（起点能力 + 成长方向）
5. 目标与动机（短期目标 + 长期目标）
6. 弱点与缺陷（避免完美主角）
7. 成长弧光（如何从A成长到B）

【都市重生主角示例】
{{
    "name": "陈阳",
    "age": 18,  # 重生后的年龄
    "gender": "male",
    "appearance": "普通大学生外貌，但眼神成熟",
    
    "backstory": {{
        "previous_life": "30岁创业失败，负债累累",
        "rebirth_reason": "意外车祸触发重生",
        "kept_memories": "12年商业经验 + 互联网发展趋势",
        "lost_memories": "具体技术细节、个人隐私"
    }},
    
    "personality": [
        "谨慎（经历过失败，不再冲动）",
        "务实（重视利益，不再理想主义）",
        "善于隐藏（不暴露重生秘密）",
        "有底线（不做违法乱纪的事）",
        "重视人际（知道关系的重要性）"
    ],
    
    "abilities": {{
        "starting": [
            "2024年的商业眼光",
            "互联网产品思维",
            "基础的商业谈判技巧"
        ],
        "growth_direction": [
            "从小创业到商业帝国",
            "从个人到团队领导者",
            "从隐藏到逐步展现实力"
        ]
    }},
    
    "goals": {{
        "short_term": ["考上好大学", "赚第一桶金", "建立人脉"],
        "mid_term": ["创办互联网公司", "布局未来产业"],
        "long_term": ["成为商业巨头", "改变家人命运", "实现财务自由"]
    }},
    
    "flaws": [
        "过于依赖前世记忆（历史可能偏离）",
        "难以与同龄人共情（心理年龄差异）",
        "害怕暴露重生秘密（心理负担）"
    ],
    
    "arc": {{
        "chapter_1_10": "谨慎试探，小规模创业",
        "chapter_11_30": "初步成功，建立公司",
        "chapter_31_60": "快速扩张，遇到强敌",
        "chapter_61_100": "商业帝国，行业领袖"
    }}
}}
"""
        
        result = llm.generate(prompt, response_format="json")
        return Character(**result)
    
    def _design_supporting_characters(self, core_idea, protagonist, world_setting, genre_config):
        """设计主要配角"""
        
        prompt = f"""
设计3-5个主要配角，构成主角的核心关系网。

【主角】
{format_character(protagonist)}

【创意】
{format_core_idea(core_idea)}

【设计配角】
为主角设计以下类型的配角：
1. 导师型（引导主角成长）
2. 伙伴型（并肩作战）
3. 爱情型（情感线）
4. 竞争型（良性竞争）
5. 路人转核心型（随剧情成长为核心）

每个角色需要：
- 与主角的关系定位
- 独特的性格特点
- 自己的目标和动机
- 与主角的冲突或互补

【都市重生配角示例】
{{
    "characters": [
        {{
            "name": "林晓",
            "role": "伙伴型",
            "relation": "大学室友 → 创业伙伴",
            "personality": ["技术天才", "社恐", "忠诚"],
            "goal": "实现技术理想",
            "function": "负责技术实现，弥补主角技术短板"
        }},
        {{
            "name": "苏雨",
            "role": "爱情型",
            "relation": "高中同学 → 女友 → 商业伙伴",
            "personality": ["聪明", "独立", "敏感"],
            "goal": "证明自己的能力",
            "function": "情感线 + 商业视角补充"
        }},
        {{
            "name": "王教授",
            "role": "导师型",
            "relation": "大学导师",
            "personality": ["睿智", "正直", "人脉广"],
            "goal": "培养优秀学生",
            "function": "提供指导、引荐人脉、关键时刻帮助"
        }}
    ]
}}
"""
        
        result = llm.generate(prompt, response_format="json")
        return [Character(**char) for char in result["characters"]]
```

---

#### Stage 4: Story Bible Generation

**目的**: 生成完整的Story Bible

```python
class StoryBibleGenerator:
    """故事圣经生成器"""
    
    def generate(self,
                core_idea: dict,
                world_setting: WorldSetting,
                characters: List[Character],
                genre_config: GenreConfig) -> StoryBible:
        """生成Story Bible"""
        
        return StoryBible(
            # 基础信息
            title=self._generate_title(core_idea),
            genre=genre_config.genre_id,
            premise=core_idea['premise'],
            
            # 世界设定
            world_setting=world_setting,
            
            # 角色
            characters={char.char_id: char for char in characters},
            
            # 主题与调性
            theme=self._define_theme(core_idea),
            tone=self._define_tone(core_idea),
            
            # 叙事风格
            narrative_style=self._define_narrative_style(genre_config),
            
            # 爽点设计
            pleasure_points=self._design_pleasure_points(core_idea, genre_config),
            
            # 禁忌与红线
            taboos=self._define_taboos(genre_config),
            
            # 目标读者
            target_audience=self._define_target_audience(genre_config)
        )
    
    def _design_pleasure_points(self, core_idea, genre_config):
        """设计爽点"""
        
        if genre_config.genre_id == "urban":
            return {
                "primary": [
                    "先知优势（提前布局）",
                    "商战智斗（智商碾压）",
                    "打脸反转（前世轻视者跪舔）",
                    "财富增长（看得见的变强）"
                ],
                "secondary": [
                    "美女青睐（魅力提升）",
                    "敌人惊讶（低估主角）",
                    "预言成真（主角预测应验）"
                ]
            }
        elif genre_config.genre_id == "xuanhuan":
            return {
                "primary": [
                    "废材逆袭（被羞辱后崛起）",
                    "等级碾压（越级挑战）",
                    "境界突破（看得见的变强）",
                    "打脸反转（看不起者跪舔）"
                ],
                "secondary": [
                    "宝物获得",
                    "美女追求",
                    "敌人惊惧"
                ]
            }
```

---

#### Stage 5: Long Arc Planning

**目的**: 规划长期剧情弧光

```python
class LongArcPlanner:
    """长弧规划器"""
    
    def plan(self,
            story_bible: StoryBible,
            target_length: int,
            genre_config: GenreConfig) -> LongArc:
        """规划长期剧情"""
        
        # 5.1 分幕结构
        acts = self._plan_acts(story_bible, target_length, genre_config)
        
        # 5.2 主要剧情线
        plot_threads = self._plan_plot_threads(story_bible, acts)
        
        # 5.3 角色成长线
        character_arcs = self._plan_character_arcs(story_bible, acts)
        
        # 5.4 高潮点规划
        climax_points = self._plan_climax_points(acts)
        
        return LongArc(
            acts=acts,
            plot_threads=plot_threads,
            character_arcs=character_arcs,
            climax_points=climax_points
        )
    
    def _plan_acts(self, story_bible, target_length, genre_config):
        """规划分幕结构"""
        
        if genre_config.genre_id == "urban":
            # 都市：起步 → 发展 → 扩张 → 巅峰
            return [
                Act(
                    name="第一幕：重生起步",
                    chapters=range(1, 21),
                    goal="利用先知优势赚第一桶金",
                    ending="成功创办第一家公司"
                ),
                Act(
                    name="第二幕：快速发展",
                    chapters=range(21, 51),
                    goal="在互联网浪潮中站稳脚跟",
                    ending="成为行业新星"
                ),
                Act(
                    name="第三幕：商业帝国",
                    chapters=range(51, 81),
                    goal="多元化布局，建立商业帝国",
                    ending="成为商业巨头"
                ),
                Act(
                    name="第四幕：巅峰对决",
                    chapters=range(81, target_length + 1),
                    goal="与顶级势力博弈",
                    ending="站上商业之巅"
                )
            ]
        elif genre_config.genre_id == "xuanhuan":
            # 玄幻：崛起 → 称雄 → 飞升
            return [
                Act(
                    name="第一幕：废材崛起",
                    chapters=range(1, 31),
                    goal="摆脱废材标签，踏上修炼之路",
                    ending="筑基成功，宗门大比夺冠"
                ),
                Act(
                    name="第二幕：闯荡江湖",
                    chapters=range(31, 61),
                    goal="历练成长，结交强者",
                    ending="金丹境界，成为一方强者"
                ),
                Act(
                    name="第三幕：称雄大陆",
                    chapters=range(61, 91),
                    goal="统一势力，成为大陆霸主",
                    ending="元婴巅峰，准备飞升"
                ),
                Act(
                    name="第四幕：仙界征途",
                    chapters=range(91, target_length + 1),
                    goal="飞升仙界，再创辉煌",
                    ending="仙界立足"
                )
            ]
```

---

#### Stage 6: Outline Generation

**目的**: 生成详细大纲

```python
class CreativeOutlineGenerator:
    """创意驱动的大纲生成器"""
    
    def generate(self,
                story_bible: StoryBible,
                long_arc: LongArc,
                genre_config: GenreConfig) -> Outline:
        """生成大纲"""
        
        chapters = []
        
        for act in long_arc.acts:
            for chapter_num in act.chapters:
                chapter_outline = self._generate_chapter_outline(
                    chapter_num,
                    act,
                    story_bible,
                    long_arc,
                    genre_config
                )
                chapters.append(chapter_outline)
        
        return Outline(chapters=chapters)
    
    def _generate_chapter_outline(self, 
                                  chapter_num,
                                  act,
                                  story_bible,
                                  long_arc,
                                  genre_config):
        """生成单章大纲"""
        
        # 获取当前章节的剧情线进展
        plot_progress = self._get_plot_progress(chapter_num, long_arc)
        
        # 获取角色成长进展
        character_progress = self._get_character_progress(chapter_num, long_arc)
        
        # 生成章节大纲
        prompt = f"""
生成第{chapter_num}章大纲。

【幕次】{act.name}
【幕目标】{act.goal}

【剧情进展】
{format_plot_progress(plot_progress)}

【角色进展】
{format_character_progress(character_progress)}

【Story Bible】
{format_story_bible_excerpt(story_bible)}

【题材】{genre_config.genre_name}

【生成章节大纲】
1. 章节标题
2. 场景列表（2-4个场景）
3. 每个场景的：地点、参与角色、目标、冲突、结果
4. 本章推进的剧情线
5. 本章的爽点设计
6. 章末钩子（吸引读者继续）

【输出JSON】
"""
        
        result = llm.generate(prompt, response_format="json")
        return ChapterOutline(**result)
```

---

#### Stage 7: First 3 Chapters Mint

**目的**: 铸造前3章的Canon状态

```python
def mint_first_3_chapters(outline: Outline,
                         story_bible: StoryBible,
                         genre_config: GenreConfig):
    """铸造前3章"""
    
    # 从Story Bible提取Canon事实
    canon_facts = []
    
    # 1. 世界设定事实
    world_facts = extract_world_facts(story_bible.world_setting)
    canon_facts.extend(world_facts)
    
    # 2. 角色事实
    character_facts = extract_character_facts(story_bible.characters)
    canon_facts.extend(character_facts)
    
    # 3. 规则事实
    rule_facts = extract_rule_facts(story_bible.world_setting.rules)
    canon_facts.extend(rule_facts)
    
    # 4. 前3章大纲事实
    for i in range(1, 4):
        chapter_facts = extract_chapter_outline_facts(
            outline.chapters[i-1],
            chapter_num=i
        )
        canon_facts.extend(chapter_facts)
    
    # Mint到Canon
    mint_executor.execute(canon_facts)
    
    return CanonState(
        story_bible=story_bible,
        outline=outline,
        minted_chapters=0
    )
```

---

### 1.4 完整流程示例

**用户输入**:
```yaml
mode: creative
genre: urban
core_idea:
  premise: "2024年重生回2008年，利用先知优势创业"
  protagonist: "30岁失败创业者"
  core_conflict: "如何在不改变历史的前提下积累财富"
preferences:
  tone: serious
  pacing: fast
  focus: business
  target_length: 100
```

**系统输出（Creative Genesis Pipeline）**:

```
Step 1: Genre Detection ✅
- 检测题材: urban
- 置信度: 0.95
- 核心元素: rebirth, business, foresight

Step 2: World Building ✅
- 时空: 2008-2018, 重生机制
- 地理: 中国一线城市（杭州）
- 社会: 互联网创业热潮
- 规则: 重生规则 + 先知限制

Step 3: Character Design ✅
- 主角: 陈阳（18岁，重生者，商业眼光）
- 配角: 林晓（技术伙伴）、苏雨（情感线）、王教授（导师）
- 反派: 竞争对手、传统势力

Step 4: Story Bible ✅
- 书名: 《重生之商业帝国》
- 主题: 机遇与选择
- 调性: 严肃商战
- 爽点: 先知优势、商战智斗、财富增长

Step 5: Long Arc Planning ✅
- 第一幕（1-20章）: 重生起步，第一桶金
- 第二幕（21-50章）: 快速发展，互联网布局
- 第三幕（51-80章）: 商业帝国，多元化
- 第四幕（81-100章）: 巅峰对决

Step 6: Outline Generation ✅
- 100章详细大纲
- 每章: 场景、冲突、爽点、钩子

Step 7: First 3 Chapters Mint ✅
- Canon事实: 世界设定 + 角色 + 规则 + 前3章大纲
- 状态铸造完成

准备开始生产！
```

---

## 模式2: 参考学习模式（Reference Learning Mode）

### 2.1 用户输入

**输入**:
```yaml
mode: reference_learning
references:                      # 参考小说
  - novel_id: "novel_001"       # 小说ID
    title: "斗破苍穹"
    weight: 0.6                  # 权重（主要参考）
    focus: ["plot_structure", "power_system"]  # 学习重点
  
  - novel_id: "novel_002"
    title: "武动乾坤"
    weight: 0.4                  # 权重（次要参考）
    focus: ["character_development", "pacing"]

learning_mode: blend            # 学习模式
                                # - blend: 融合多本小说风格
                                # - mimic: 模仿单本小说风格
                                # - inspired: 受启发创作

creative_freedom: medium        # 创意自由度
                                # - low: 紧密模仿
                                # - medium: 借鉴框架，内容原创
                                # - high: 只借鉴核心理念
```

---

### 2.2 Reference Learning Pipeline

```
参考小说
  ↓
Stage 1: Novel Analysis（小说分析）
  ↓
Stage 2: Pattern Extraction（模式提取）
  ↓
Stage 3: Style Learning（风格学习）
  ↓
Stage 4: Adaptive Story Bible（自适应故事圣经）
  ↓
Stage 5: Reference-Guided Outline（参考引导大纲）
  ↓
Stage 6: Style-Consistent Generation（风格一致生成）
  ↓
连续生产
```

---

### 2.3 详细设计

#### Stage 1: Novel Analysis

**目的**: 深度分析参考小说

```python
class ReferenceNovelAnalyzer:
    """参考小说分析器"""
    
    def analyze(self, novel_content: str, focus: List[str]) -> NovelAnalysis:
        """分析参考小说"""
        
        analysis = NovelAnalysis()
        
        # 1. 题材识别
        analysis.genre = self._detect_genre(novel_content)
        
        # 2. 结构分析
        if "plot_structure" in focus:
            analysis.plot_structure = self._analyze_plot_structure(novel_content)
        
        # 3. 力量体系分析
        if "power_system" in focus:
            analysis.power_system = self._analyze_power_system(novel_content)
        
        # 4. 角色发展分析
        if "character_development" in focus:
            analysis.character_patterns = self._analyze_character_patterns(novel_content)
        
        # 5. 叙事风格分析
        if "narrative_style" in focus:
            analysis.narrative_style = self._analyze_narrative_style(novel_content)
        
        # 6. 节奏分析
        if "pacing" in focus:
            analysis.pacing = self._analyze_pacing(novel_content)
        
        # 7. 爽点模式分析
        analysis.pleasure_patterns = self._analyze_pleasure_patterns(novel_content)
        
        # 8. 语言风格分析
        analysis.language_style = self._analyze_language_style(novel_content)
        
        return analysis
    
    def _analyze_plot_structure(self, novel_content):
        """分析剧情结构"""
        
        # 使用LLM分析前30章
        prompt = f"""
分析小说的剧情结构模式。

【小说内容】（前30章）
{novel_content[:MAX_CONTEXT]}

【分析任务】
1. 开篇模式（前3章如何开局）
2. 起承转合节奏（每幕多少章）
3. 高潮点设置（多少章一个小高潮）
4. 转折点设置（何时出现重大转折）
5. 伏笔与回收（如何埋伏笔，何时回收）
6. 副线设置（主线vs副线比例）

【输出JSON】
{{
    "opening_pattern": {{
        "chapter_1": "废材被退婚，受辱",
        "chapter_2": "获得奇遇，得到传承",
        "chapter_3": "初步崛起，打脸报仇"
    }},
    "act_structure": {{
        "act_length": "20-30章一幕",
        "total_acts": 4,
        "pattern": "起步 → 宗门 → 大陆 → 更高位面"
    }},
    "climax_frequency": "每5-8章一个小高潮，每20-30章一个大高潮",
    "turning_points": [
        {{"chapter": 3, "event": "获得传承"}},
        {{"chapter": 15, "event": "宗门大比"}},
        {{"chapter": 30, "event": "离开宗门"}}
    ]
}}
"""
        
        return llm.generate(prompt, response_format="json")
    
    def _analyze_power_system(self, novel_content):
        """分析力量体系"""
        
        prompt = f"""
提取小说的力量体系。

【小说内容】
{novel_content[:MAX_CONTEXT]}

【提取力量体系】
1. 等级划分（如炼气、筑基、金丹...）
2. 晋级条件（如何突破）
3. 晋级难度（多少章一个境界）
4. 力量差距（高一级vs低一级的实力差）
5. 特殊能力（功法、武技、血脉）
6. 外物辅助（丹药、法宝、天材地宝）

【输出JSON】
{{
    "ranks": [
        {{"name": "斗者", "stage_range": [1, 9]}},
        {{"name": "斗师", "stage_range": [1, 9]}},
        {{"name": "大斗师", "stage_range": [1, 9]}},
        ...
    ],
    "breakthrough": {{
        "difficulty": "需要机缘、资源、感悟",
        "frequency": "每10-15章突破一个大境界"
    }},
    "power_gap": "高一个大境界可以碾压",
    "special_abilities": ["斗技", "异火", "血脉"]
}}
"""
        
        return llm.generate(prompt, response_format="json")
```

---

#### Stage 2: Pattern Extraction

**目的**: 提取可复用的模式

```python
class PatternExtractor:
    """模式提取器"""
    
    def extract(self, analyses: List[NovelAnalysis], weights: List[float]) -> ExtractedPatterns:
        """提取模式（支持多本小说融合）"""
        
        patterns = ExtractedPatterns()
        
        # 2.1 加权融合剧情结构
        patterns.plot_structure = self._merge_plot_structures(
            [a.plot_structure for a in analyses],
            weights
        )
        
        # 2.2 融合力量体系（如果题材一致）
        if self._same_genre(analyses):
            patterns.power_system = self._merge_power_systems(
                [a.power_system for a in analyses],
                weights
            )
        
        # 2.3 融合角色发展模式
        patterns.character_patterns = self._merge_character_patterns(
            [a.character_patterns for a in analyses],
            weights
        )
        
        # 2.4 融合爽点模式
        patterns.pleasure_patterns = self._merge_pleasure_patterns(
            [a.pleasure_patterns for a in analyses],
            weights
        )
        
        # 2.5 融合叙事风格
        patterns.narrative_style = self._merge_narrative_styles(
            [a.narrative_style for a in analyses],
            weights
        )
        
        return patterns
    
    def _merge_plot_structures(self, structures, weights):
        """融合剧情结构"""
        
        # 使用LLM融合多个结构
        prompt = f"""
融合多本小说的剧情结构，创造一个新的但保留精华的结构。

【参考结构1】（权重{weights[0]}）
{format_structure(structures[0])}

【参考结构2】（权重{weights[1]}）
{format_structure(structures[1])}

【融合要求】
1. 保留两本小说的优点
2. 避免两本小说的缺点
3. 创造性地结合，不是简单平均
4. 输出一个新的、连贯的剧情结构

【输出JSON】
"""
        
        return llm.generate(prompt, response_format="json")
```

---

#### Stage 3: Style Learning

**目的**: 学习叙事风格

```python
class StyleLearner:
    """风格学习器"""
    
    def learn(self, novel_content: str, creative_freedom: str) -> StyleGuide:
        """学习叙事风格"""
        
        # 3.1 句式分析
        sentence_patterns = self._analyze_sentence_patterns(novel_content)
        
        # 3.2 描写风格分析
        description_style = self._analyze_description_style(novel_content)
        
        # 3.3 对话风格分析
        dialogue_style = self._analyze_dialogue_style(novel_content)
        
        # 3.4 节奏控制分析
        pacing_style = self._analyze_pacing_style(novel_content)
        
        # 根据创意自由度调整
        if creative_freedom == "low":
            # 紧密模仿
            adherence = 0.9
        elif creative_freedom == "medium":
            # 借鉴框架
            adherence = 0.6
        else:  # high
            # 只借鉴理念
            adherence = 0.3
        
        return StyleGuide(
            sentence_patterns=sentence_patterns,
            description_style=description_style,
            dialogue_style=dialogue_style,
            pacing_style=pacing_style,
            adherence=adherence
        )
    
    def _analyze_sentence_patterns(self, novel_content):
        """分析句式"""
        
        prompt = f"""
分析小说的句式特点。

【小说片段】
{get_representative_excerpts(novel_content)}

【分析句式】
1. 句子长度分布（短句/中句/长句比例）
2. 常用句式（如"xxx，不由得xxx"）
3. 段落结构（每段几句话）
4. 修辞手法（比喻、排比、对比）
5. 语气特点（平铺直叙/激情澎湃/幽默诙谐）

【输出JSON】
{{
    "sentence_length": {{"short": 0.3, "medium": 0.5, "long": 0.2}},
    "common_patterns": [
        "当...时，...",
        "xxx，不由得xxx",
        "望着xxx，xxx心中暗道"
    ],
    "paragraph_structure": "2-4句一段，动作描写紧凑",
    "rhetoric": ["比喻常用", "少用排比", "对比突出"],
    "tone": "平铺直叙为主，高潮时激情渲染"
}}
"""
        
        return llm.generate(prompt, response_format="json")
```

---

#### Stage 4: Adaptive Story Bible

**目的**: 基于参考小说生成Story Bible

```python
class AdaptiveStoryBibleGenerator:
    """自适应故事圣经生成器"""
    
    def generate(self,
                patterns: ExtractedPatterns,
                style_guide: StyleGuide,
                user_input: dict) -> StoryBible:
        """生成自适应故事圣经"""
        
        # 4.1 基于参考小说的世界设定
        world_setting = self._build_world_from_patterns(patterns)
        
        # 4.2 基于参考小说的角色设计
        characters = self._design_characters_from_patterns(patterns)
        
        # 4.3 基于参考小说的力量体系
        power_system = patterns.power_system
        
        # 4.4 基于参考小说的爽点设计
        pleasure_points = patterns.pleasure_patterns
        
        return StoryBible(
            title=self._generate_title(),
            genre=patterns.genre,
            
            world_setting=world_setting,
            characters=characters,
            power_system=power_system,
            
            # 参考小说的风格
            narrative_style=style_guide,
            pleasure_points=pleasure_points,
            
            # 结构模式
            plot_structure_template=patterns.plot_structure
        )
```

---

#### Stage 5: Reference-Guided Outline

**目的**: 基于参考结构生成大纲

```python
class ReferenceGuidedOutlineGenerator:
    """参考引导的大纲生成器"""
    
    def generate(self,
                story_bible: StoryBible,
                patterns: ExtractedPatterns,
                target_length: int) -> Outline:
        """生成大纲"""
        
        # 使用参考小说的结构模板
        structure_template = patterns.plot_structure
        
        chapters = []
        for chapter_num in range(1, target_length + 1):
            chapter_outline = self._generate_chapter_from_template(
                chapter_num,
                structure_template,
                story_bible
            )
            chapters.append(chapter_outline)
        
        return Outline(chapters=chapters)
    
    def _generate_chapter_from_template(self, chapter_num, template, story_bible):
        """从模板生成章节"""
        
        # 判断当前章节在结构中的位置
        position = self._determine_position(chapter_num, template)
        
        # 获取该位置的模板
        chapter_template = template.get_template_for_position(position)
        
        # 生成章节
        prompt = f"""
参考模板生成第{chapter_num}章大纲。

【参考模板】
位置: {position}
模板: {format_template(chapter_template)}

【Story Bible】
{format_story_bible(story_bible)}

【生成章节】
按照模板结构，但内容原创。

【输出JSON】
"""
        
        return llm.generate(prompt, response_format="json")
```

---

#### Stage 6: Style-Consistent Generation

**目的**: 风格一致的章节生成

```python
class StyleConsistentGenerator:
    """风格一致生成器"""
    
    def generate(self,
                chapter_outline: ChapterOutline,
                story_bible: StoryBible,
                style_guide: StyleGuide) -> str:
        """生成章节（保持风格一致）"""
        
        prompt = f"""
生成第{chapter_outline.chapter_num}章，严格遵循参考风格。

【章节大纲】
{format_outline(chapter_outline)}

【Story Bible】
{format_story_bible(story_bible)}

【风格指南】（必须严格遵守）
句式模式: {style_guide.sentence_patterns}
描写风格: {style_guide.description_style}
对话风格: {style_guide.dialogue_style}
节奏控制: {style_guide.pacing_style}

【参考示例】（模仿这种风格）
{get_reference_examples(style_guide)}

【要求】
1. 句式模仿参考风格（遵守度{style_guide.adherence}）
2. 描写风格与参考一致
3. 对话符合参考风格
4. 节奏把控参考示例

开始生成：
"""
        
        return llm.generate(prompt)
```

---

### 2.4 完整流程示例

**用户输入**:
```yaml
mode: reference_learning
references:
  - novel_id: "novel_001"
    title: "斗破苍穹"
    weight: 0.6
    focus: ["plot_structure", "power_system", "pleasure_patterns"]

learning_mode: mimic
creative_freedom: medium
target_length: 100
```

**系统输出**:
```
Step 1: Novel Analysis ✅
- 分析《斗破苍穹》前50章
- 提取: 剧情结构、力量体系、爽点模式

Step 2: Pattern Extraction ✅
- 剧情结构: 废材逆袭 → 宗门崛起 → 大陆称雄
- 力量体系: 斗者 → 斗师 → 大斗师...（共9级）
- 爽点模式: 退婚打脸、境界突破、越级战斗

Step 3: Style Learning ✅
- 句式: 中短句为主，动作描写紧凑
- 描写: 细腻的心理描写 + 激情的战斗场面
- 对话: 简洁有力，突出性格

Step 4: Adaptive Story Bible ✅
- 世界: 玄幻大陆，宗门林立
- 主角: 废材少年，有奇遇
- 力量: 采用类似斗破的等级体系
- 爽点: 废材逆袭、打脸、越级战斗

Step 5: Reference-Guided Outline ✅
- 第1章: 废材被退婚（模仿斗破开局）
- 第2章: 奇遇获得传承
- 第3章: 初露锋芒，打脸
- ...
- 100章完整大纲

Step 6: Style-Consistent Generation ✅
- 准备开始生产
- 风格遵守度: 60%（medium creative freedom）

准备开始生产！
```

---

## 🔄 两种模式对比

| 维度 | 创意驱动模式 | 参考学习模式 |
|------|-------------|-------------|
| **输入** | 题材 + 核心创意 | 参考小说 |
| **原创性** | 高（完全原创） | 中（借鉴参考） |
| **难度** | 高（需要AI创造） | 中（有模板参考） |
| **质量** | 不确定（依赖AI） | 相对稳定（有参考） |
| **适用场景** | 用户有明确创意 | 用户想模仿优秀作品 |
| **风险** | 可能不符合预期 | 可能过于相似 |

---

## 📝 实施建议

### 优先级

**M1-M3**: 不实施（优先完成Genre-First基础）

**M4**: 实施创意驱动模式（基础版）
- Creative Genesis Pipeline
- 自动世界构建
- 自动角色设计
- 自动大纲生成

**M5-M6**: 实施参考学习模式
- Reference Learning Pipeline
- 风格分析与学习
- 模式提取与融合

### 技术依赖

1. **强大的LLM**: 需要GPT-4级别以上的模型
2. **长上下文**: 需要处理完整小说（10-50章）
3. **结构化输出**: 需要可靠的JSON输出
4. **成本控制**: 分析参考小说成本较高

### 风险控制

1. **创意驱动模式风险**:
   - AI生成的世界可能不连贯
   - 角色设计可能不吸引人
   - **缓解**: 人工审核Story Bible后再生产

2. **参考学习模式风险**:
   - 过度模仿导致抄袭风险
   - 风格僵硬不灵活
   - **缓解**: creative_freedom参数控制，抄袭检测

---

## 🎯 最终建议

### 短期（M1-M3）

**不实施**，专注Genre-First基础架构

### 中期（M4）

**实施创意驱动模式（简化版）**:
- 只实现Story Bible自动生成
- 大纲仍需人工确认
- 作为M4的增强功能

### 长期（M5-M6）

**实施完整的两种模式**:
- 创意驱动模式（完整版）
- 参考学习模式（基础版）
- 作为ANovel的差异化功能

---

**制定人**: Claude Opus 4.8  
**文档版本**: v1.0  
**状态**: 设计完成，等待M4实施
