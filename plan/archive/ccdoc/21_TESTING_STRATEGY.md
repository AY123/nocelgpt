# ANovel V2 测试策略

**版本**: v1.0  
**制定日期**: 2026-09-18  
**状态**: Draft  
**用途**: 定义完整的测试策略和方法  

---

## 📋 文档目的

本文档定义ANovel V2的测试策略，包括：
1. **测试金字塔** - 单元/集成/端到端测试
2. **测试框架** - Pytest + 相关工具
3. **测试用例** - 核心功能测试
4. **LLM测试** - AI输出质量测试
5. **CI集成** - 自动化测试
6. **性能测试** - 负载和压力测试

测试原则：
- 快速反馈
- 高覆盖率（>80%）
- 可维护性
- 自动化优先

---

## 🏗️ 测试金字塔

```
        /\
       /  \      E2E测试（5%）
      /────\     - 完整用户流程
     /      \    - UI + API + 数据库
    /────────\   
   /          \  集成测试（25%）
  /────────────\ - API端到端
 /              \- 数据库集成
/────────────────\ 
|                | 单元测试（70%）
|                | - 函数级别
|________________| - 快速执行
```

### 测试分布目标

| 测试类型 | 占比 | 数量目标 | 执行时间 |
|---------|------|---------|---------|
| 单元测试 | 70% | 500+ | <2分钟 |
| 集成测试 | 25% | 100+ | <5分钟 |
| E2E测试 | 5% | 20+ | <10分钟 |

---

## 🧪 测试框架选择

### 核心工具

```toml
[tool.poetry.group.test.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-cov = "^4.1.0"
pytest-mock = "^3.11.0"
httpx = "^0.25.0"  # 异步HTTP客户端测试
faker = "^19.0.0"  # 生成测试数据
factory-boy = "^3.3.0"  # 数据工厂
freezegun = "^1.2.2"  # 时间Mock
hypothesis = "^6.92.0"  # 属性测试
```

### pytest配置

```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# 异步支持
asyncio_mode = auto

# 覆盖率
addopts = 
    --cov=.
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
    -v
    --tb=short

# 标记
markers =
    unit: 单元测试
    integration: 集成测试
    e2e: 端到端测试
    slow: 慢速测试
    llm: 需要LLM API的测试（跳过CI）
    
# 忽略
norecursedirs = .git .venv __pycache__ dist build
```

---

## 🔧 单元测试

### 1. Genre系统测试

#### GenreConfig测试

```python
# tests/unit/genre/test_config.py
import pytest
from core.genre import GenreID, GenreConfig
from core.genre.configs.urban import URBAN_CONFIG

class TestGenreConfig:
    """测试GenreConfig"""
    
    def test_create_config(self):
        """测试创建配置"""
        config = GenreConfig(
            genre_id=GenreID.URBAN,
            genre_name="都市",
            description="现代都市题材"
        )
        
        assert config.genre_id == GenreID.URBAN
        assert config.genre_name == "都市"
    
    def test_urban_config_valid(self):
        """测试都市配置有效性"""
        assert URBAN_CONFIG.genre_id == GenreID.URBAN
        assert len(URBAN_CONFIG.forbidden_elements) > 0
        assert "修炼" in URBAN_CONFIG.forbidden_elements
    
    def test_to_prompt_context(self):
        """测试转换为Prompt上下文"""
        context = URBAN_CONFIG.to_prompt_context()
        
        assert "都市" in context
        assert "禁止元素" in context
        assert "修炼" in context
    
    def test_get_prompt_template(self):
        """测试获取Prompt模板"""
        template = URBAN_CONFIG.get_prompt_template("outline")
        
        assert template is not None
        assert isinstance(template, str)


class TestGenreConstraints:
    """测试GenreConstraints"""
    
    def test_validate_urban_content_pass(self):
        """测试都市内容验证（通过）"""
        content = "陈阳在公司开会，讨论新项目的融资计划。"
        
        violations = URBAN_CONFIG.validate_content(content)
        
        assert len(violations) == 0
    
    def test_validate_urban_content_fail(self):
        """测试都市内容验证（失败）"""
        content = "陈阳开始修炼灵气，突破到筑基期。"
        
        violations = URBAN_CONFIG.validate_content(content)
        
        assert len(violations) > 0
        assert any("修炼" in v.element for v in violations)
        assert any(v.is_blocking() for v in violations)
```

#### ProgressionModel测试

```python
# tests/unit/genre/test_progression.py
import pytest
from core.genre.progression import WealthProgressionModel, CultivationProgressionModel

class TestWealthProgressionModel:
    """测试财富进阶模型"""
    
    def test_get_tiers(self):
        """测试获取等级列表"""
        model = WealthProgressionModel()
        tiers = model.get_tiers()
        
        assert len(tiers) == 6
        assert tiers[0] == "贫困线"
        assert tiers[-1] == "富豪"
    
    def test_validate_reasonable_progression(self):
        """测试合理进阶"""
        model = WealthProgressionModel()
        
        result = model.validate_progression(
            "温饱", "小康",
            context={"chapter_count": 15, "time_span_months": 6}
        )
        
        assert result.is_valid
        assert len(result.issues) == 0
    
    def test_validate_too_fast_progression(self):
        """测试进阶过快"""
        model = WealthProgressionModel()
        
        result = model.validate_progression(
            "贫困线", "富豪",
            context={"chapter_count": 5, "time_span_months": 2}
        )
        
        assert not result.is_valid
        assert len(result.issues) > 0
        assert any("跨越等级过多" in issue for issue in result.issues)
    
    def test_calculate_tier_gap(self):
        """测试计算等级差距"""
        model = WealthProgressionModel()
        
        gap = model.calculate_tier_gap("贫困线", "富豪")
        assert gap == 5
        
        gap = model.calculate_tier_gap("温饱", "小康")
        assert gap == 1


class TestCultivationProgressionModel:
    """测试修炼进阶模型"""
    
    def test_validate_normal_breakthrough(self):
        """测试正常突破"""
        model = CultivationProgressionModel()
        
        result = model.validate_progression(
            "炼气期", "筑基期",
            context={"chapter_count": 25, "has_special_opportunity": False}
        )
        
        assert result.is_valid
    
    def test_validate_too_fast_breakthrough(self):
        """测试突破过快"""
        model = CultivationProgressionModel()
        
        result = model.validate_progression(
            "炼气期", "金丹期",
            context={"chapter_count": 10, "has_special_opportunity": False}
        )
        
        assert not result.is_valid
        assert any("境界提升过快" in issue for issue in result.issues)
```

### 2. 数据模型测试

```python
# tests/unit/domain/test_character.py
import pytest
from domain.character import CharacterBase, UrbanCharacter, Gender, CharacterRole

class TestCharacterBase:
    """测试角色基础模型"""
    
    def test_create_character(self):
        """测试创建角色"""
        character = CharacterBase(
            character_id="char_001",
            name="陈阳",
            gender=Gender.MALE,
            age=25,
            role=CharacterRole.PROTAGONIST
        )
        
        assert character.name == "陈阳"
        assert character.age == 25
        assert character.gender == Gender.MALE
    
    def test_to_dict(self):
        """测试序列化"""
        character = CharacterBase(
            character_id="char_001",
            name="陈阳",
            gender=Gender.MALE,
            age=25
        )
        
        data = character.to_dict()
        
        assert data["character_id"] == "char_001"
        assert data["name"] == "陈阳"
        assert data["gender"] == "male"
    
    def test_to_prompt_context(self):
        """测试转换为Prompt上下文"""
        character = CharacterBase(
            character_id="char_001",
            name="陈阳",
            gender=Gender.MALE,
            age=25,
            personality_traits=["果断", "聪明"],
            background="贫困家庭",
            motivation="改变命运"
        )
        
        context = character.to_prompt_context()
        
        assert "陈阳" in context
        assert "25岁" in context
        assert "果断" in context


class TestUrbanCharacter:
    """测试都市角色"""
    
    def test_create_urban_character(self):
        """测试创建都市角色"""
        character = UrbanCharacter(
            character_id="urban_001",
            name="陈阳",
            age=25,
            wealth_tier="温饱",
            occupation="程序员"
        )
        
        assert character.wealth_tier == "温饱"
        assert character.occupation == "程序员"
    
    def test_progress_wealth(self):
        """测试财富进阶"""
        character = UrbanCharacter(
            character_id="urban_001",
            name="陈阳",
            wealth_tier="温饱",
            wealth_details={"annual_income": 80000}
        )
        
        character.progress_wealth("小康", 150000)
        
        assert character.wealth_tier == "小康"
        assert character.get_wealth_numeric() == 150000
    
    def test_add_skill(self):
        """测试添加技能"""
        character = UrbanCharacter(
            character_id="urban_001",
            name="陈阳",
            skills=["Python"]
        )
        
        character.add_skill("架构设计")
        
        assert "架构设计" in character.skills
        assert len(character.skills) == 2
```

### 3. 质量检测测试

```python
# tests/unit/quality/test_checker.py
import pytest
from core.quality import TextQualityChecker, GenreComplianceChecker

class TestTextQualityChecker:
    """测试文本质量检查器"""
    
    def test_check_good_quality(self):
        """测试高质量文本"""
        checker = TextQualityChecker()
        
        content = "陈阳走进会议室。" * 100  # 约2000字
        metrics = checker.check(content)
        
        assert metrics["word_count"] >= 1800
        assert metrics["overall_score"] > 70
    
    def test_check_too_short(self):
        """测试文本过短"""
        checker = TextQualityChecker()
        
        content = "陈阳走进会议室。"  # 太短
        metrics = checker.check(content)
        
        assert metrics["word_count_score"] < 0.5
    
    def test_detect_repetition(self):
        """测试检测重复"""
        checker = TextQualityChecker()
        
        content = "陈阳说话。" * 200  # 大量重复
        metrics = checker.check(content)
        
        assert metrics["repetition_score"] < 0.5


class TestGenreComplianceChecker:
    """测试题材符合度检查器"""
    
    @pytest.mark.asyncio
    async def test_check_compliant_content(self):
        """测试符合题材的内容"""
        checker = GenreComplianceChecker()
        
        content = "陈阳在公司讨论融资方案，准备见投资人。"
        result = await checker.check("urban", content)
        
        assert result["score"] >= 90
        assert not result["has_blocking"]
    
    @pytest.mark.asyncio
    async def test_check_violation(self):
        """测试违规内容"""
        checker = GenreComplianceChecker()
        
        content = "陈阳开始修炼灵气，炼化丹药。"
        result = await checker.check("urban", content)
        
        assert result["score"] < 50
        assert result["has_blocking"]
        assert len(result["violations"]) > 0
```

---

## 🔗 集成测试

### 1. API集成测试

```python
# tests/integration/api/test_novels_api.py
import pytest
from httpx import AsyncClient
from main import app

@pytest.fixture
async def client():
    """异步HTTP客户端"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def auth_headers(client):
    """认证头"""
    # 登录获取Token
    response = await client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "testpass"
    })
    token = response.json()["data"]["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


class TestNovelsAPI:
    """测试小说API"""
    
    @pytest.mark.asyncio
    async def test_create_novel(self, client, auth_headers):
        """测试创建小说"""
        response = await client.post(
            "/api/v1/novels",
            headers=auth_headers,
            json={
                "title": "测试小说",
                "genre_id": "urban",
                "description": "测试描述"
            }
        )
        
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["title"] == "测试小说"
        assert data["genre_id"] == "urban"
    
    @pytest.mark.asyncio
    async def test_get_novels(self, client, auth_headers):
        """测试获取小说列表"""
        response = await client.get(
            "/api/v1/novels",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
    
    @pytest.mark.asyncio
    async def test_get_novel_detail(self, client, auth_headers):
        """测试获取小说详情"""
        # 先创建
        create_response = await client.post(
            "/api/v1/novels",
            headers=auth_headers,
            json={"title": "测试", "genre_id": "urban"}
        )
        novel_id = create_response.json()["data"]["id"]
        
        # 再获取
        response = await client.get(
            f"/api/v1/novels/{novel_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == novel_id
    
    @pytest.mark.asyncio
    async def test_update_novel(self, client, auth_headers):
        """测试更新小说"""
        # 创建
        create_response = await client.post(
            "/api/v1/novels",
            headers=auth_headers,
            json={"title": "原标题", "genre_id": "urban"}
        )
        novel_id = create_response.json()["data"]["id"]
        
        # 更新
        response = await client.patch(
            f"/api/v1/novels/{novel_id}",
            headers=auth_headers,
            json={"title": "新标题"}
        )
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["title"] == "新标题"
    
    @pytest.mark.asyncio
    async def test_delete_novel(self, client, auth_headers):
        """测试删除小说"""
        # 创建
        create_response = await client.post(
            "/api/v1/novels",
            headers=auth_headers,
            json={"title": "待删除", "genre_id": "urban"}
        )
        novel_id = create_response.json()["data"]["id"]
        
        # 删除
        response = await client.delete(
            f"/api/v1/novels/{novel_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # 验证已删除
        get_response = await client.get(
            f"/api/v1/novels/{novel_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404
```

### 2. 数据库集成测试

```python
# tests/integration/database/test_repositories.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from infrastructure.database.repositories import CharacterRepository
from domain.character import UrbanCharacter

@pytest.fixture
async def db_session():
    """测试数据库会话"""
    # 使用测试数据库
    engine = create_async_engine(
        "postgresql+asyncpg://test:test@localhost/test_anovel",
        echo=True
    )
    
    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()


class TestCharacterRepository:
    """测试角色仓储"""
    
    @pytest.mark.asyncio
    async def test_create_character(self, db_session):
        """测试创建角色"""
        repo = CharacterRepository(db_session)
        
        character = UrbanCharacter(
            character_id="test_001",
            name="测试角色",
            age=25,
            wealth_tier="温饱"
        )
        
        created = await repo.create(character)
        
        assert created.character_id == "test_001"
        assert created.name == "测试角色"
    
    @pytest.mark.asyncio
    async def test_get_by_id(self, db_session):
        """测试根据ID查询"""
        repo = CharacterRepository(db_session)
        
        # 创建
        character = UrbanCharacter(
            character_id="test_002",
            name="测试角色2",
            age=26
        )
        await repo.create(character)
        
        # 查询
        found = await repo.get_by_id("test_002")
        
        assert found is not None
        assert found.name == "测试角色2"
    
    @pytest.mark.asyncio
    async def test_get_by_novel(self, db_session):
        """测试查询小说的所有角色"""
        repo = CharacterRepository(db_session)
        
        # 创建多个角色
        for i in range(3):
            character = UrbanCharacter(
                character_id=f"test_{i}",
                name=f"角色{i}",
                novel_id="novel_test"
            )
            await repo.create(character)
        
        # 查询
        characters = await repo.get_by_novel("novel_test")
        
        assert len(characters) == 3
```

### 3. LLM集成测试（需要真实API Key）

```python
# tests/integration/llm/test_llm_client.py
import pytest
from infrastructure.llm import LLMClient

@pytest.mark.llm  # 标记为LLM测试，CI中跳过
class TestLLMClient:
    """测试LLM客户端"""
    
    @pytest.mark.asyncio
    async def test_simple_generation(self):
        """测试简单生成"""
        client = LLMClient(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        result = await client.generate(
            prompt="生成一个都市主角的名字",
            model="claude-haiku-4",
            max_tokens=50
        )
        
        assert result is not None
        assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_generation_with_cache(self):
        """测试带缓存的生成"""
        from infrastructure.cache import RedisCache
        
        cache = RedisCache()
        client = LLMClient(api_key=os.getenv("ANTHROPIC_API_KEY"), cache=cache)
        
        prompt = "测试Prompt"
        
        # 第一次调用（未缓存）
        result1 = await client.generate(prompt, use_cache=True)
        
        # 第二次调用（应该命中缓存）
        result2 = await client.generate(prompt, use_cache=True)
        
        assert result1 == result2
```

---

## 🌐 端到端测试

### E2E测试场景

```python
# tests/e2e/test_complete_flow.py
import pytest
from httpx import AsyncClient

@pytest.mark.e2e
class TestCompleteNovelFlow:
    """测试完整小说创建流程"""
    
    @pytest.mark.asyncio
    async def test_complete_genesis_to_chapter(self, client, auth_headers):
        """测试从创世到章节生成的完整流程"""
        
        # 1. 创建创世任务
        genesis_response = await client.post(
            "/api/v1/genesis",
            headers=auth_headers,
            json={
                "genre_id": "urban",
                "user_input": "一个程序员创业的故事",
                "title": "都市创业记"
            }
        )
        
        assert genesis_response.status_code == 202
        task_id = genesis_response.json()["data"]["task_id"]
        
        # 2. 等待创世完成
        import asyncio
        for _ in range(30):  # 最多等待30秒
            task_response = await client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers
            )
            
            status = task_response.json()["data"]["status"]
            if status == "completed":
                break
            
            await asyncio.sleep(1)
        
        assert task_response.json()["data"]["status"] == "completed"
        novel_id = task_response.json()["data"]["result"]["novel_id"]
        
        # 3. 验证小说已创建
        novel_response = await client.get(
            f"/api/v1/novels/{novel_id}",
            headers=auth_headers
        )
        
        assert novel_response.status_code == 200
        novel_data = novel_response.json()["data"]
        assert novel_data["title"] == "都市创业记"
        assert novel_data["genre_id"] == "urban"
        
        # 4. 验证角色已创建
        characters_response = await client.get(
            f"/api/v1/novels/{novel_id}/characters",
            headers=auth_headers
        )
        
        assert characters_response.status_code == 200
        characters = characters_response.json()["data"]
        assert len(characters) > 0
        
        # 5. 验证大纲已创建
        outline_response = await client.get(
            f"/api/v1/novels/{novel_id}/outline",
            headers=auth_headers
        )
        
        assert outline_response.status_code == 200
        outline = outline_response.json()["data"]
        assert len(outline["arcs"]) > 0
        
        # 6. 生成第一章
        chapter_response = await client.post(
            f"/api/v1/novels/{novel_id}/chapters",
            headers=auth_headers,
            json={"chapter_number": 1}
        )
        
        assert chapter_response.status_code == 202
        chapter_task_id = chapter_response.json()["data"]["task_id"]
        
        # 7. 等待章节生成完成
        for _ in range(60):
            chapter_task_response = await client.get(
                f"/api/v1/tasks/{chapter_task_id}",
                headers=auth_headers
            )
            
            if chapter_task_response.json()["data"]["status"] == "completed":
                break
            
            await asyncio.sleep(1)
        
        # 8. 验证章节已生成
        chapter_id = chapter_response.json()["data"]["chapter_id"]
        chapter_detail_response = await client.get(
            f"/api/v1/chapters/{chapter_id}",
            headers=auth_headers
        )
        
        assert chapter_detail_response.status_code == 200
        chapter = chapter_detail_response.json()["data"]
        assert chapter["chapter_number"] == 1
        assert len(chapter["content"]) >= 1800  # 至少1800字
        assert chapter["status"] == "published"
```

---

## ⚡ 性能测试

### 使用Locust进行负载测试

```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between
import random

class ANovelUser(HttpUser):
    """模拟用户行为"""
    
    wait_time = between(1, 3)  # 请求间隔1-3秒
    
    def on_start(self):
        """登录"""
        response = self.client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "testpass"
        })
        
        self.token = response.json()["data"]["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(10)
    def get_novels(self):
        """获取小说列表（高频操作）"""
        self.client.get("/api/v1/novels", headers=self.headers)
    
    @task(5)
    def get_novel_detail(self):
        """获取小说详情"""
        novel_id = random.choice(self.novel_ids)
        self.client.get(f"/api/v1/novels/{novel_id}", headers=self.headers)
    
    @task(3)
    def get_chapters(self):
        """获取章节列表"""
        novel_id = random.choice(self.novel_ids)
        self.client.get(f"/api/v1/novels/{novel_id}/chapters", headers=self.headers)
    
    @task(1)
    def create_chapter(self):
        """生成章节（低频但重要）"""
        novel_id = random.choice(self.novel_ids)
        self.client.post(
            f"/api/v1/novels/{novel_id}/chapters",
            headers=self.headers,
            json={"auto_generate": True}
        )
```

运行负载测试：

```bash
# 模拟100个并发用户
locust -f tests/performance/locustfile.py --users 100 --spawn-rate 10

# Web UI访问
# http://localhost:8089
```

---

## 🤖 测试数据工厂

### Factory Boy使用

```python
# tests/factories.py
import factory
from faker import Faker
from domain.character import UrbanCharacter, Gender, CharacterRole
from domain.novel import Novel

fake = Faker('zh_CN')

class CharacterFactory(factory.Factory):
    """角色工厂"""
    
    class Meta:
        model = UrbanCharacter
    
    character_id = factory.Sequence(lambda n: f"char_{n}")
    name = factory.LazyAttribute(lambda _: fake.name())
    gender = Gender.MALE
    age = factory.LazyAttribute(lambda _: fake.random_int(min=20, max=60))
    role = CharacterRole.SUPPORTING
    
    personality_traits = factory.LazyAttribute(
        lambda _: [fake.word() for _ in range(3)]
    )
    background = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=100))
    
    wealth_tier = "温饱"
    occupation = factory.LazyAttribute(lambda _: fake.job())


class NovelFactory(factory.Factory):
    """小说工厂"""
    
    class Meta:
        model = Novel
    
    id = factory.Sequence(lambda n: f"novel_{n}")
    title = factory.LazyAttribute(lambda _: fake.sentence(nb_words=4))
    genre_id = "urban"
    description = factory.LazyAttribute(lambda _: fake.text())
    status = "writing"


# 使用示例
def test_with_factory():
    # 创建单个角色
    character = CharacterFactory()
    
    # 创建多个角色
    characters = CharacterFactory.create_batch(5)
    
    # 覆盖属性
    protagonist = CharacterFactory(
        name="陈阳",
        role=CharacterRole.PROTAGONIST
    )
```

---

## 🎯 测试覆盖率目标

### 覆盖率要求

| 模块 | 目标覆盖率 | 当前 | 状态 |
|------|-----------|------|------|
| core/genre/ | 90% | - | 🔴 待实施 |
| domain/ | 85% | - | 🔴 待实施 |
| api/ | 80% | - | 🔴 待实施 |
| infrastructure/ | 75% | - | 🔴 待实施 |
| **总体** | **80%** | **-** | **🔴 待实施** |

### 生成覆盖率报告

```bash
# 运行测试并生成覆盖率报告
pytest --cov=. --cov-report=html --cov-report=term

# 查看HTML报告
open htmlcov/index.html
```

---

## 🔄 CI/CD集成

### GitHub Actions测试工作流

```yaml
# .github/workflows/test.yml
name: Test

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Cache dependencies
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      
      - name: Run unit tests
        run: pytest tests/unit -v --cov --cov-report=xml
      
      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost/test
          REDIS_URL: redis://localhost:6379/0
        run: pytest tests/integration -v
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: unittests
      
      - name: Check coverage threshold
        run: |
          coverage report --fail-under=80
```

---

## 📚 最佳实践

### 1. 测试命名规范

```python
# ✅ 好的命名
def test_create_character_with_valid_data():
    """使用有效数据创建角色"""
    pass

def test_validate_progression_fails_when_gap_too_large():
    """当等级差距过大时，进阶验证应该失败"""
    pass

# ❌ 不好的命名
def test1():
    pass

def test_character():
    pass
```

### 2. AAA模式

```python
def test_example():
    # Arrange（准备）
    character = CharacterFactory()
    model = WealthProgressionModel()
    
    # Act（执行）
    result = model.validate_progression("温饱", "小康")
    
    # Assert（断言）
    assert result.is_valid
```

### 3. 独立性

```python
# ✅ 每个测试独立
def test_a():
    character = CharacterFactory()
    # 测试A的逻辑

def test_b():
    character = CharacterFactory()
    # 测试B的逻辑

# ❌ 测试间有依赖
shared_character = None

def test_a():
    global shared_character
    shared_character = CharacterFactory()

def test_b():
    # 依赖test_a的结果
    assert shared_character is not None
```

---

**测试策略文档完成！** ✅

第三批（2个文档）全部完成：
1. ✅ 20_DEPLOYMENT_OPERATIONS_GUIDE.md
2. ✅ 21_TESTING_STRATEGY.md
