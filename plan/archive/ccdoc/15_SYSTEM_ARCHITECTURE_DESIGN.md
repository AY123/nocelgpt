# ANovel V2 系统架构设计

**版本**: v1.0  
**制定日期**: 2026-09-18  
**状态**: Draft  
**用途**: 定义系统整体架构和模块划分  

---

## 📋 文档目的

本文档定义ANovel V2的系统架构，包括：
1. **整体架构** - 系统层级和组件关系
2. **模块划分** - 核心模块和职责
3. **数据流设计** - 数据在系统中的流动
4. **API设计** - 接口规范和约定
5. **部署架构** - 物理部署方案

基于：
- Genre-First架构原则
- AI-First开发模式
- V1项目经验教训
- 行业最佳实践

---

## 🏗️ 整体架构

### 架构风格：**分层单体架构（Modular Monolith）**

**选择理由**：
- ✅ MVP阶段简单高效
- ✅ 开发部署容易
- ✅ AI易于理解
- ✅ 未来可拆分微服务
- ❌ 避免过早微服务化

### 三层架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Presentation Layer                      │
│                   (API + WebSocket + Admin)                  │
├─────────────────────────────────────────────────────────────┤
│                       Business Layer                         │
│              (Genesis + Production + Services)               │
├─────────────────────────────────────────────────────────────┤
│                        Data Layer                            │
│              (Database + Cache + External APIs)              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 核心模块划分

### 模块全景图

```
anovel-v2/
├── api/                    # API层（表现层）
│   ├── routes/            # 路由
│   ├── schemas/           # Pydantic模型
│   ├── dependencies.py    # 依赖注入
│   └── middleware.py      # 中间件
│
├── core/                   # 核心层（领域层）
│   ├── genesis/           # 创世流程
│   ├── production/        # 生产流程
│   ├── genre/             # Genre系统
│   ├── models/            # 数据模型
│   └── services/          # 业务服务
│
├── infrastructure/         # 基础设施层
│   ├── database/          # 数据库
│   ├── cache/             # 缓存
│   ├── llm/               # LLM集成
│   ├── storage/           # 文件存储
│   └── tasks/             # 异步任务
│
├── domain/                 # 领域模型
│   ├── character.py       # 角色
│   ├── worldview.py       # 世界观
│   ├── outline.py         # 大纲
│   ├── chapter.py         # 章节
│   └── relationship.py    # 关系
│
├── shared/                 # 共享模块
│   ├── config.py          # 配置
│   ├── exceptions.py      # 异常
│   ├── utils.py           # 工具
│   └── constants.py       # 常量
│
├── tests/                  # 测试
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
└── prompts/                # Prompt模板
    ├── genesis/
    ├── production/
    └── validation/
```

---

## 📊 详细模块设计

### 1. API层（Presentation Layer）

#### 职责
- 接收HTTP请求
- 参数验证
- 权限检查
- 响应格式化
- WebSocket连接管理

#### 目录结构

```python
api/
├── __init__.py
├── main.py                 # FastAPI应用入口
│
├── routes/                 # 路由模块
│   ├── __init__.py
│   ├── genesis.py          # 创世相关API
│   ├── production.py       # 生产相关API
│   ├── novels.py           # 小说管理API
│   ├── characters.py       # 角色管理API
│   ├── worldviews.py       # 世界观管理API
│   ├── outlines.py         # 大纲管理API
│   ├── chapters.py         # 章节管理API
│   ├── tasks.py            # 任务查询API
│   ├── users.py            # 用户管理API
│   └── health.py           # 健康检查API
│
├── schemas/                # Pydantic Schema
│   ├── __init__.py
│   ├── requests/           # 请求模型
│   │   ├── genesis.py
│   │   ├── production.py
│   │   └── ...
│   └── responses/          # 响应模型
│       ├── genesis.py
│       ├── production.py
│       └── ...
│
├── dependencies.py         # 依赖注入
├── middleware.py           # 中间件
└── websocket.py            # WebSocket处理
```

#### 示例：main.py

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import (
    genesis, production, novels, characters,
    worldviews, outlines, chapters, tasks, users, health
)
from api.middleware import LoggingMiddleware, ErrorHandlerMiddleware

# 创建应用
app = FastAPI(
    title="ANovel V2 API",
    version="2.0.0",
    description="AI小说生成平台",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# 中间件
app.add_middleware(CORSMiddleware, allow_origins=["*"])
app.add_middleware(LoggingMiddleware)
app.add_middleware(ErrorHandlerMiddleware)

# 注册路由
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(genesis.router, prefix="/api/v1/genesis", tags=["Genesis"])
app.include_router(production.router, prefix="/api/v1/production", tags=["Production"])
app.include_router(novels.router, prefix="/api/v1/novels", tags=["Novels"])
app.include_router(characters.router, prefix="/api/v1/characters", tags=["Characters"])
app.include_router(worldviews.router, prefix="/api/v1/worldviews", tags=["Worldviews"])
app.include_router(outlines.router, prefix="/api/v1/outlines", tags=["Outlines"])
app.include_router(chapters.router, prefix="/api/v1/chapters", tags=["Chapters"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])

# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动"""
    from infrastructure.database import init_db
    from core.genre import initialize_genre_system
    
    await init_db()
    initialize_genre_system()

# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭"""
    from infrastructure.database import close_db
    await close_db()
```

#### 示例：routes/genesis.py

```python
from fastapi import APIRouter, Depends, HTTPException
from api.schemas.requests.genesis import GenesisRequest
from api.schemas.responses.genesis import GenesisResponse
from api.dependencies import get_current_user, get_genesis_service
from core.services.genesis import GenesisService

router = APIRouter()

@router.post("/create", response_model=GenesisResponse)
async def create_genesis(
    request: GenesisRequest,
    user_id: str = Depends(get_current_user),
    service: GenesisService = Depends(get_genesis_service)
):
    """
    创建创世任务
    
    - **genre_id**: 题材ID（urban/xuanhuan/...）
    - **user_input**: 用户输入的故事想法
    - **title**: 小说标题（可选）
    """
    try:
        result = await service.create_genesis(
            user_id=user_id,
            genre_id=request.genre_id,
            user_input=request.user_input,
            title=request.title
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{genesis_id}", response_model=GenesisResponse)
async def get_genesis(
    genesis_id: str,
    user_id: str = Depends(get_current_user),
    service: GenesisService = Depends(get_genesis_service)
):
    """查询创世任务状态"""
    result = await service.get_genesis(genesis_id, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Genesis not found")
    return result
```

---

### 2. 核心层（Business Layer）

#### 职责
- 业务逻辑实现
- 流程编排
- 规则验证
- LLM调用封装

#### 2.1 Genesis（创世流程）

```python
core/genesis/
├── __init__.py
├── service.py              # Genesis服务
├── generator.py            # 生成器
├── validator.py            # 验证器
└── prompts.py              # Prompt构建
```

**核心流程**：
```
用户输入 → 题材检测 → 大纲生成 → 角色生成 → 世界观生成 → 验证 → 保存
```

**代码示例**：
```python
# core/genesis/service.py
from core.genre import get_genre_config, GenreDetector
from core.models import Outline, Character, Worldview
from infrastructure.llm import LLMClient
from infrastructure.database import DatabaseSession

class GenesisService:
    """创世服务"""
    
    def __init__(
        self,
        llm_client: LLMClient,
        db_session: DatabaseSession
    ):
        self.llm = llm_client
        self.db = db_session
        self.detector = GenreDetector()
    
    async def create_genesis(
        self,
        user_id: str,
        genre_id: str,
        user_input: str,
        title: Optional[str] = None
    ) -> dict:
        """创建创世任务"""
        
        # 1. 获取题材配置
        genre_config = get_genre_config(genre_id)
        
        # 2. 生成大纲
        outline = await self._generate_outline(
            genre_config=genre_config,
            user_input=user_input,
            title=title
        )
        
        # 3. 生成角色
        characters = await self._generate_characters(
            genre_config=genre_config,
            outline=outline
        )
        
        # 4. 生成世界观
        worldview = await self._generate_worldview(
            genre_config=genre_config,
            outline=outline
        )
        
        # 5. 验证
        validation_result = await self._validate_genesis(
            outline=outline,
            characters=characters,
            worldview=worldview
        )
        
        if not validation_result.is_valid:
            # 重新生成或修正
            pass
        
        # 6. 保存到数据库
        novel_id = await self._save_to_database(
            user_id=user_id,
            outline=outline,
            characters=characters,
            worldview=worldview
        )
        
        return {
            "novel_id": novel_id,
            "outline": outline.to_dict(),
            "characters": [c.to_dict() for c in characters],
            "worldview": worldview.to_dict()
        }
    
    async def _generate_outline(
        self,
        genre_config,
        user_input: str,
        title: Optional[str]
    ) -> Outline:
        """生成大纲"""
        # 获取Prompt模板
        prompt_template = genre_config.get_prompt_template("outline")
        
        # 构建完整Prompt
        prompt = self._build_outline_prompt(
            template=prompt_template,
            genre_config=genre_config,
            user_input=user_input,
            title=title
        )
        
        # 调用LLM
        result = await self.llm.generate(
            prompt=prompt,
            model="claude-opus-4",
            max_tokens=8000,
            temperature=0.7
        )
        
        # 解析为Outline对象
        outline = self._parse_outline(result)
        
        return outline
```

#### 2.2 Production（生产流程）

```python
core/production/
├── __init__.py
├── service.py              # Production服务
├── generator.py            # 章节生成器
├── validator.py            # 章节验证器
├── reviser.py              # 章节修订器
└── prompts.py              # Prompt构建
```

**核心流程**：
```
章节大纲 → 章节生成 → 题材验证 → 质量检查 → 修订（可选）→ 保存
```

**代码示例**：
```python
# core/production/service.py
class ProductionService:
    """生产服务"""
    
    async def generate_chapter(
        self,
        novel_id: str,
        chapter_number: int,
        user_id: str
    ) -> Chapter:
        """生成章节"""
        
        # 1. 获取上下文
        context = await self._get_chapter_context(novel_id, chapter_number)
        
        # 2. 获取章节大纲
        chapter_outline = context["chapter_outline"]
        
        # 3. 构建Prompt
        prompt = await self._build_chapter_prompt(context)
        
        # 4. 生成章节
        content = await self.llm.generate(
            prompt=prompt,
            model="claude-sonnet-4",
            max_tokens=4096
        )
        
        # 5. 题材验证
        validation_result = await self._validate_genre_constraints(
            genre_id=context["genre_id"],
            content=content
        )
        
        if validation_result.has_blocking_violations:
            # 重新生成
            return await self._regenerate_chapter(prompt, validation_result)
        
        # 6. 质量检查
        quality_score = await self._check_quality(content)
        
        # 7. 保存
        chapter = await self._save_chapter(
            novel_id=novel_id,
            chapter_number=chapter_number,
            content=content,
            quality_score=quality_score
        )
        
        return chapter
```

#### 2.3 Genre System（题材系统）

```python
core/genre/
├── __init__.py
├── config.py               # 题材配置
├── constraints.py          # 题材约束
├── progression.py          # 进阶模型
├── registry.py             # 注册表
├── detector.py             # 检测器
├── validator.py            # 验证器
└── configs/                # 具体题材配置
    ├── urban.py
    ├── xuanhuan.py
    └── ...
```

**参考**：已在 `13_DATA_MODEL_COMPLETE_DEFINITION.md` 详细定义

#### 2.4 Services（业务服务）

```python
core/services/
├── __init__.py
├── novel_service.py        # 小说服务
├── character_service.py    # 角色服务
├── worldview_service.py    # 世界观服务
├── outline_service.py      # 大纲服务
├── chapter_service.py      # 章节服务
└── user_service.py         # 用户服务
```

---

### 3. 基础设施层（Infrastructure Layer）

#### 职责
- 数据持久化
- 外部服务集成
- 技术实现细节

#### 3.1 Database（数据库）

```python
infrastructure/database/
├── __init__.py
├── session.py              # 数据库会话
├── models/                 # SQLAlchemy模型
│   ├── novel.py
│   ├── character.py
│   ├── worldview.py
│   ├── outline.py
│   ├── chapter.py
│   └── user.py
└── repositories/           # 数据访问层
    ├── novel_repository.py
    ├── character_repository.py
    └── ...
```

**示例：repositories/character_repository.py**

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.database.models import CharacterModel
from domain.character import Character

class CharacterRepository:
    """角色仓储"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, character: Character) -> Character:
        """创建角色"""
        model = CharacterModel(**character.to_dict())
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_domain(model)
    
    async def get_by_id(self, character_id: str) -> Optional[Character]:
        """根据ID查询角色"""
        stmt = select(CharacterModel).where(CharacterModel.id == character_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None
    
    async def get_by_novel(self, novel_id: str) -> List[Character]:
        """查询小说的所有角色"""
        stmt = select(CharacterModel).where(CharacterModel.novel_id == novel_id)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]
    
    def _to_domain(self, model: CharacterModel) -> Character:
        """模型转领域对象"""
        # 根据genre_id动态创建对应的Character类
        if model.genre_id == "urban":
            return UrbanCharacter(**model.to_dict())
        elif model.genre_id == "xuanhuan":
            return XuanhuanCharacter(**model.to_dict())
        else:
            return Character(**model.to_dict())
```

#### 3.2 LLM（LLM集成）

```python
infrastructure/llm/
├── __init__.py
├── client.py               # LLM客户端
├── providers/              # 不同提供商
│   ├── anthropic.py
│   ├── openai.py
│   └── litellm.py
├── cache.py                # 响应缓存
├── token_counter.py        # Token计数
└── cost_tracker.py         # 成本跟踪
```

**示例：client.py**

```python
from typing import Optional, Dict, Any
import anthropic
from infrastructure.cache import RedisCache

class LLMClient:
    """LLM客户端"""
    
    def __init__(
        self,
        anthropic_api_key: str,
        cache: Optional[RedisCache] = None
    ):
        self.client = anthropic.AsyncAnthropic(api_key=anthropic_api_key)
        self.cache = cache
    
    async def generate(
        self,
        prompt: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        use_cache: bool = True
    ) -> str:
        """生成内容"""
        
        # 检查缓存
        if use_cache and self.cache:
            cache_key = self._get_cache_key(prompt, model, max_tokens, temperature)
            cached = await self.cache.get(cache_key)
            if cached:
                return cached
        
        # 调用LLM
        message = await self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result = message.content[0].text
        
        # 存缓存
        if use_cache and self.cache:
            await self.cache.set(cache_key, result, ttl=3600)
        
        # 记录成本
        await self._track_cost(model, message.usage)
        
        return result
    
    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """生成结构化输出"""
        # 使用JSON Schema约束输出
        result = await self.generate(prompt, **kwargs)
        # 验证和解析
        return self._parse_json(result, schema)
```

#### 3.3 Cache（缓存）

```python
infrastructure/cache/
├── __init__.py
├── redis_cache.py          # Redis缓存
└── memory_cache.py         # 内存缓存（开发用）
```

#### 3.4 Tasks（异步任务）

```python
infrastructure/tasks/
├── __init__.py
├── celery_app.py           # Celery应用
├── tasks/                  # 任务定义
│   ├── genesis_tasks.py
│   ├── production_tasks.py
│   └── batch_tasks.py
└── utils.py                # 任务工具
```

**示例：tasks/production_tasks.py**

```python
from infrastructure.tasks.celery_app import celery_app
from core.production import ProductionService

@celery_app.task(bind=True, max_retries=3)
async def generate_chapter_task(
    self,
    novel_id: str,
    chapter_number: int,
    user_id: str
):
    """异步生成章节任务"""
    try:
        # 更新状态
        self.update_state(
            state='GENERATING',
            meta={'progress': 0, 'chapter_number': chapter_number}
        )
        
        # 生成章节
        service = ProductionService()
        chapter = await service.generate_chapter(
            novel_id=novel_id,
            chapter_number=chapter_number,
            user_id=user_id
        )
        
        return {
            "status": "success",
            "chapter_id": chapter.id,
            "word_count": chapter.word_count
        }
    except Exception as exc:
        # 重试
        raise self.retry(exc=exc, countdown=60)
```

---

### 4. 领域层（Domain Layer）

```python
domain/
├── __init__.py
├── character.py            # 角色领域模型
├── worldview.py            # 世界观领域模型
├── outline.py              # 大纲领域模型
├── chapter.py              # 章节领域模型
├── relationship.py         # 关系领域模型
└── novel.py                # 小说领域模型
```

**参考**：已在 `13_DATA_MODEL_COMPLETE_DEFINITION.md` 详细定义

---

## 🔄 数据流设计

### 1. Genesis流程数据流

```
┌──────────┐
│  用户输入  │
└─────┬────┘
      │
      ▼
┌──────────────────┐
│   API层           │
│  - 参数验证        │
│  - 权限检查        │
└─────┬────────────┘
      │
      ▼
┌──────────────────┐
│  GenesisService  │
│  - 获取Genre配置  │
│  - 编排流程       │
└─────┬────────────┘
      │
      ├──────────────────┐
      │                  │
      ▼                  ▼
┌──────────┐      ┌──────────┐
│ 生成大纲   │      │ 生成角色   │
└─────┬────┘      └─────┬────┘
      │                  │
      └────────┬─────────┘
               │
               ▼
         ┌──────────┐
         │ 生成世界观 │
         └─────┬────┘
               │
               ▼
         ┌──────────┐
         │   验证    │
         └─────┬────┘
               │
               ▼
         ┌──────────┐
         │ 保存数据库 │
         └─────┬────┘
               │
               ▼
         ┌──────────┐
         │ 返回结果  │
         └──────────┘
```

### 2. Production流程数据流

```
┌──────────────┐
│ 章节生成请求  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   API层       │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ 创建异步任务  │ ──────┐
└──────┬───────┘       │
       │               │
       │               ▼
       │         ┌────────────┐
       │         │ Celery队列  │
       │         └─────┬──────┘
       │               │
       │               ▼
       │         ┌────────────────┐
       │         │ ProductionService│
       │         │ - 获取上下文     │
       │         │ - 构建Prompt    │
       │         │ - 调用LLM       │
       │         │ - 验证          │
       │         │ - 保存          │
       │         └─────┬──────────┘
       │               │
       │               ▼
       │         ┌────────────┐
       │         │   数据库    │
       │         └────────────┘
       │
       ▼
┌──────────────┐
│ 返回任务ID    │
└──────────────┘
```

### 3. 查询流程数据流

```
┌──────────┐
│ 查询请求  │
└─────┬────┘
      │
      ▼
┌──────────────┐
│   API层       │
│  - 权限检查    │
└──────┬───────┘
      │
      ▼
┌──────────────┐     ┌────────┐
│   Service     │────▶│  Cache │
│  - 查询缓存    │◀────│        │
└──────┬───────┘     └────────┘
      │
      │ (缓存未命中)
      ▼
┌──────────────┐     ┌────────┐
│  Repository   │────▶│Database│
│  - 查询数据库  │◀────│        │
└──────┬───────┘     └────────┘
      │
      ▼
┌──────────────┐
│  写入缓存      │
└──────┬───────┘
      │
      ▼
┌──────────────┐
│  返回结果     │
└──────────────┘
```

---

## 🌐 API设计规范

### RESTful API约定

#### 资源命名

```
GET    /api/v1/novels                    # 列出小说
POST   /api/v1/novels                    # 创建小说
GET    /api/v1/novels/{novel_id}         # 获取小说详情
PUT    /api/v1/novels/{novel_id}         # 更新小说
DELETE /api/v1/novels/{novel_id}         # 删除小说

GET    /api/v1/novels/{novel_id}/characters        # 获取小说的角色列表
POST   /api/v1/novels/{novel_id}/characters        # 创建角色
GET    /api/v1/characters/{character_id}           # 获取角色详情

GET    /api/v1/novels/{novel_id}/chapters          # 获取章节列表
POST   /api/v1/novels/{novel_id}/chapters          # 生成新章节
GET    /api/v1/chapters/{chapter_id}               # 获取章节内容
```

#### 响应格式

**成功响应**：
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "都市之巅",
    "genre_id": "urban",
    "created_at": "2026-09-18T10:00:00Z"
  },
  "meta": {
    "timestamp": "2026-09-18T10:00:00Z"
  }
}
```

**错误响应**：
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid genre_id",
    "details": {
      "field": "genre_id",
      "value": "invalid"
    }
  },
  "meta": {
    "timestamp": "2026-09-18T10:00:00Z",
    "request_id": "req_xxx"
  }
}
```

#### 分页

```
GET /api/v1/novels?page=1&page_size=20&sort=created_at&order=desc

Response:
{
  "success": true,
  "data": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5
  }
}
```

---

## 🚀 部署架构

### 开发环境

```
┌─────────────────────────────────────────┐
│          开发机 (localhost)              │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │   Docker Compose                   │ │
│  │                                    │ │
│  │  ┌──────┐  ┌──────┐  ┌────────┐  │ │
│  │  │ API  │  │Worker│  │Postgres│  │ │
│  │  │:8000 │  │      │  │  :5432 │  │ │
│  │  └──────┘  └──────┘  └────────┘  │ │
│  │                                    │ │
│  │  ┌──────┐                         │ │
│  │  │Redis │                         │ │
│  │  │:6379 │                         │ │
│  │  └──────┘                         │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### 生产环境（MVP阶段）

```
┌────────────────────────────────────────────────┐
│                   VPS / Cloud                   │
│                                                 │
│  ┌────────┐                                    │
│  │ Nginx  │  (反向代理 + SSL)                  │
│  │  :80   │                                    │
│  │  :443  │                                    │
│  └───┬────┘                                    │
│      │                                          │
│  ┌───▼──────────────────────────────────────┐ │
│  │   Docker Compose                         │ │
│  │                                          │ │
│  │  ┌────────┐  ┌────────┐  ┌──────────┐  │ │
│  │  │  API   │  │ Worker │  │PostgreSQL│  │ │
│  │  │  x2    │  │  x2    │  │          │  │ │
│  │  └────────┘  └────────┘  └──────────┘  │ │
│  │                                          │ │
│  │  ┌────────┐                             │ │
│  │  │ Redis  │                             │ │
│  │  └────────┘                             │ │
│  └──────────────────────────────────────────┘ │
│                                                 │
│  ┌──────────────┐                              │
│  │  备份脚本     │                              │
│  │  (PostgreSQL)│                              │
│  └──────────────┘                              │
└────────────────────────────────────────────────┘
```

### 生产环境（扩展阶段）

```
                    ┌──────────────┐
                    │ Load Balancer│
                    │   (Nginx)    │
                    └──────┬───────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐       ┌────▼────┐       ┌────▼────┐
   │  API    │       │  API    │       │  API    │
   │Instance1│       │Instance2│       │Instance3│
   └────┬────┘       └────┬────┘       └────┬────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                    ┌──────▼───────┐
                    │   Message    │
                    │    Queue     │
                    │  (RabbitMQ)  │
                    └──────┬───────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐       ┌────▼────┐       ┌────▼────┐
   │ Worker  │       │ Worker  │       │ Worker  │
   │    1    │       │    2    │       │    3    │
   └─────────┘       └─────────┘       └─────────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐       ┌────▼────┐       ┌────▼────┐
   │PostgreSQL│       │  Redis  │       │  S3     │
   │ (Master) │       │ Cluster │       │ Storage │
   └────┬────┘       └─────────┘       └─────────┘
        │
   ┌────▼────┐
   │PostgreSQL│
   │ (Replica)│
   └─────────┘
```

---

## 🔐 安全架构

### 认证授权流程

```
┌──────┐                    ┌──────┐                   ┌──────┐
│Client│                    │ API  │                   │ Auth │
└──┬───┘                    └──┬───┘                   └──┬───┘
   │                           │                          │
   │ 1. Login (username/pwd)   │                          │
   ├──────────────────────────>│                          │
   │                           │ 2. Verify credentials    │
   │                           ├─────────────────────────>│
   │                           │                          │
   │                           │ 3. Return JWT            │
   │                           │<─────────────────────────┤
   │ 4. Return JWT             │                          │
   │<──────────────────────────┤                          │
   │                           │                          │
   │ 5. Request + JWT          │                          │
   ├──────────────────────────>│                          │
   │                           │ 6. Validate JWT          │
   │                           ├─────────────────────────>│
   │                           │                          │
   │                           │ 7. JWT valid             │
   │                           │<─────────────────────────┤
   │                           │                          │
   │                           │ 8. Process request       │
   │                           │                          │
   │ 9. Response               │                          │
   │<──────────────────────────┤                          │
```

---

## 📊 架构评估

### 优势

✅ **简单易懂** - AI可快速理解
✅ **快速开发** - MVP阶段高效
✅ **易于部署** - Docker Compose搞定
✅ **模块化** - 职责清晰，易于维护
✅ **可扩展** - 未来可拆分微服务

### 劣势与应对

❌ **单体性能限制**
- 应对：水平扩展（多实例）
- 未来：拆分微服务

❌ **数据库瓶颈**
- 应对：读写分离、缓存
- 未来：分库分表

❌ **LLM调用成本高**
- 应对：缓存、批处理
- 未来：模型优化

---

## 🎯 实施路线

### Phase 1（MVP）- 2周

**实现**：
- API层基础框架
- Genesis核心流程
- Production核心流程
- PostgreSQL + Redis
- 基础部署

**不做**：
- 复杂权限
- 高级监控
- 微服务拆分

### Phase 2（优化）- 2周

**添加**：
- 完整测试
- 异步任务队列
- 缓存优化
- 日志监控

### Phase 3（扩展）- 按需

**添加**：
- 微服务拆分（可选）
- 多区域部署
- 高级功能

---

**系统架构设计文档完成！** ✅

下一步：**16_LLM_INTEGRATION_STRATEGY.md**（LLM集成策略）
