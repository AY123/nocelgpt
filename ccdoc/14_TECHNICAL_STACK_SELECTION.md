# ANovel V2 技术栈选型分析

**版本**: v1.0  
**制定日期**: 2026-09-18  
**状态**: Draft  
**用途**: 为新项目选择最优技术栈  

---

## 📋 文档目的

本文档基于以下因素进行技术栈选型：
1. **AI-First特性** - 项目从头到尾基于AI搭建
2. **V1项目经验** - 吸取失败教训
3. **行业最佳实践** - 参考Sudowrite、NovelAI等成功案例
4. **可维护性** - 适合AI理解和修改
5. **可扩展性** - 支持未来增长
6. **成本效益** - LLM调用成本可控

---

## 🎯 技术选型原则

### 核心原则

1. **AI可读性优先**
   - 代码结构清晰
   - 类型标注完整
   - 文档详尽
   - 命名语义化

2. **简单胜于复杂**
   - 避免过度工程
   - 优先成熟稳定方案
   - 减少技术栈碎片

3. **Python生态为主**
   - LLM集成友好
   - AI工具链丰富
   - 开发效率高

4. **异步优先**
   - LLM调用是I/O密集
   - 高并发需求
   - 用户体验更好

---

## 🐍 编程语言：Python 3.11+

### 选择理由

✅ **强类型支持**（Python 3.10+）
```python
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class Character:
    name: str
    age: int
    traits: List[str]
```
- 完整类型标注
- IDE智能提示
- AI更易理解代码结构

✅ **异步原生支持**
```python
async def generate_chapter(prompt: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(llm_api, json={"prompt": prompt})
        return response.json()["content"]
```

✅ **LLM生态最佳**
- LangChain
- LlamaIndex
- Anthropic SDK
- OpenAI SDK

✅ **V1经验验证**
- ainovel项目使用Python
- 开发效率高
- 问题在架构不在语言

### 版本选择：**Python 3.11**

- 性能提升（比3.10快10-60%）
- 更好的错误提示
- TaskGroup等新特性
- 稳定版本（避免3.12的兼容性问题）

---

## 🌐 Web框架：FastAPI

### 选型对比

| 框架 | 优势 | 劣势 | 评分 |
|------|------|------|------|
| **FastAPI** | 异步原生、类型安全、自动文档、性能高 | 相对年轻 | ⭐⭐⭐⭐⭐ |
| Django | 生态成熟、Admin强大 | 同步为主、过重 | ⭐⭐⭐ |
| Flask | 轻量灵活 | 异步支持弱、功能少 | ⭐⭐ |

### 选择：**FastAPI**

#### 核心优势

1. **异步原生**
```python
@app.post("/generate/chapter")
async def generate_chapter(request: ChapterRequest) -> ChapterResponse:
    # 并发调用多个LLM
    async with asyncio.TaskGroup() as tg:
        task1 = tg.create_task(llm.generate_plot(request))
        task2 = tg.create_task(llm.generate_dialogue(request))
    
    return combine_results(task1.result(), task2.result())
```

2. **类型驱动开发**
```python
from pydantic import BaseModel, Field

class ChapterRequest(BaseModel):
    genre_id: str = Field(..., description="题材ID")
    outline: str = Field(..., min_length=10)
    chapter_number: int = Field(..., gt=0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "genre_id": "urban",
                "outline": "主角创业...",
                "chapter_number": 1
            }
        }
```
- 自动验证
- 自动文档生成
- AI易于理解

3. **自动API文档**
- Swagger UI（/docs）
- ReDoc（/redoc）
- OpenAPI 3.0规范
- 前端直接使用

4. **性能卓越**
- 基于Starlette + Uvicorn
- 性能接近Go/Node.js
- 适合高并发LLM调用

#### 使用场景

```python
# main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="ANovel V2 API",
    version="2.0.0",
    description="AI小说生成平台"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由组织
app.include_router(genesis_router, prefix="/api/v1/genesis", tags=["Genesis"])
app.include_router(production_router, prefix="/api/v1/production", tags=["Production"])
```

---

## 🤖 LLM集成方案

### 多模型策略

**核心思想**：不同任务使用不同模型，成本与质量平衡

| 任务类型 | 推荐模型 | 原因 | 成本 |
|---------|---------|------|------|
| 大纲生成 | Claude Opus 4 | 需要深度推理 | 高 |
| 章节生成 | Claude Sonnet 4 | 平衡质量与成本 | 中 |
| 内容验证 | Claude Haiku 4 | 快速简单任务 | 低 |
| 批量检测 | GPT-4o mini | 便宜高效 | 极低 |

### SDK选择：**Anthropic SDK + LiteLLM**

#### 1. Anthropic SDK（主力）

```python
import anthropic

client = anthropic.AsyncAnthropic(
    api_key=settings.ANTHROPIC_API_KEY
)

async def generate_with_claude(
    prompt: str,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4096
) -> str:
    """使用Claude生成内容"""
    message = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return message.content[0].text
```

**优势**：
- 官方SDK，稳定可靠
- 类型完整
- 异步支持
- Streaming支持

#### 2. LiteLLM（多模型统一）

```python
from litellm import acompletion

async def generate_unified(
    prompt: str,
    model: str = "claude-sonnet-4"
) -> str:
    """统一的多模型接口"""
    response = await acompletion(
        model=model,  # 支持claude-sonnet-4, gpt-4, gemini-pro等
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
```

**优势**：
- 统一接口切换模型
- 成本追踪
- 回退机制
- 100+ 模型支持

### Prompt管理：**Jinja2模板**

```python
from jinja2 import Environment, FileSystemLoader

# 加载模板
env = Environment(loader=FileSystemLoader('prompts/'))

# 渲染Prompt
template = env.get_template('urban_chapter.j2')
prompt = template.render(
    genre=genre_config,
    outline=outline,
    chapter_number=5,
    previous_summary=prev_summary
)
```

**优势**：
- Prompt与代码分离
- 版本控制友好
- 易于A/B测试
- 支持继承和复用

---

## 🗄️ 数据库方案

### 混合存储策略

**核心思想**：结构化数据用SQL，非结构化用NoSQL

#### 1. PostgreSQL（主数据库）

**用途**：
- 用户账号
- 小说元数据
- 角色/世界观/大纲
- 关系数据

**选择理由**：
✅ ACID保证
✅ JSON/JSONB支持（兼顾灵活性）
✅ 全文搜索
✅ 成熟稳定
✅ 免费开源

**Schema示例**：
```sql
-- 角色表
CREATE TABLE characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id UUID NOT NULL REFERENCES novels(id),
    name VARCHAR(100) NOT NULL,
    genre_id VARCHAR(50) NOT NULL,
    
    -- 基础属性（通用）
    base_attributes JSONB NOT NULL,
    
    -- 题材专属属性
    genre_attributes JSONB NOT NULL,
    
    -- 元数据
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- 索引
    CONSTRAINT fk_novel FOREIGN KEY (novel_id) REFERENCES novels(id)
);

-- 索引
CREATE INDEX idx_characters_novel ON characters(novel_id);
CREATE INDEX idx_characters_genre ON characters(genre_id);
CREATE INDEX idx_characters_attrs ON characters USING GIN (genre_attributes);
```

#### 2. Redis（缓存+队列）

**用途**：
- LLM响应缓存
- 会话状态
- 任务队列
- 实时数据

**使用示例**：
```python
import redis.asyncio as redis

# 缓存LLM响应
async def cached_llm_call(prompt: str, ttl: int = 3600) -> str:
    cache_key = f"llm:cache:{hash(prompt)}"
    
    # 检查缓存
    cached = await redis_client.get(cache_key)
    if cached:
        return cached.decode()
    
    # 调用LLM
    result = await llm.generate(prompt)
    
    # 存缓存
    await redis_client.setex(cache_key, ttl, result)
    return result
```

#### 3. MongoDB（可选，用于日志）

**用途**：
- LLM调用日志
- 用户行为日志
- 实验数据

**是否必需**：❌ 可用PostgreSQL的JSONB替代

---

## 🔄 异步任务队列：Celery + Redis

### 选择理由

**为什么需要任务队列**：
- LLM生成耗时（10秒-2分钟）
- 避免HTTP超时
- 异步解耦
- 可重试

### 架构

```
用户请求 → FastAPI → 创建任务 → Celery Worker → LLM调用 → 结果存储
                          ↓
                      Redis队列
```

### 代码示例

```python
# tasks.py
from celery import Celery

celery_app = Celery(
    'anovel',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1'
)

@celery_app.task(bind=True, max_retries=3)
async def generate_chapter_task(self, chapter_id: str, prompt: str):
    """异步生成章节"""
    try:
        # 更新状态
        self.update_state(state='GENERATING', meta={'progress': 0})
        
        # 调用LLM
        content = await llm.generate(prompt, max_tokens=4096)
        
        # 保存结果
        await db.chapters.update(chapter_id, content=content, status='completed')
        
        return {"status": "success", "chapter_id": chapter_id}
    except Exception as exc:
        # 重试
        raise self.retry(exc=exc, countdown=60)


# api.py
@app.post("/generate/chapter")
async def generate_chapter(request: ChapterRequest):
    """创建章节生成任务"""
    # 创建异步任务
    task = generate_chapter_task.delay(
        chapter_id=request.chapter_id,
        prompt=request.prompt
    )
    
    return {
        "task_id": task.id,
        "status": "queued",
        "status_url": f"/api/v1/tasks/{task.id}"
    }

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """查询任务状态"""
    task = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "state": task.state,
        "progress": task.info.get('progress', 0) if task.info else 0
    }
```

---

## 📦 ORM：SQLAlchemy 2.0

### 选择理由

✅ **异步支持**（2.0版本）
✅ **类型安全**
✅ **成熟稳定**
✅ **灵活强大**

### 使用示例

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing import Optional
import uuid

# Base
class Base(DeclarativeBase):
    pass

# 模型定义
class Character(Base):
    __tablename__ = "characters"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    novel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("novels.id"))
    name: Mapped[str] = mapped_column(String(100))
    genre_id: Mapped[str] = mapped_column(String(50))
    
    # JSONB字段
    base_attributes: Mapped[dict] = mapped_column(JSON)
    genre_attributes: Mapped[dict] = mapped_column(JSON)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

# 异步查询
async def get_character(session: AsyncSession, character_id: uuid.UUID) -> Optional[Character]:
    stmt = select(Character).where(Character.id == character_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def create_character(session: AsyncSession, character_data: dict) -> Character:
    character = Character(**character_data)
    session.add(character)
    await session.commit()
    await session.refresh(character)
    return character
```

---

## 🧪 测试框架

### 1. Pytest（单元测试+集成测试）

```python
# tests/test_genre_detector.py
import pytest
from runtime.genre import GenreDetector

@pytest.fixture
def detector():
    return GenreDetector()

def test_detect_urban(detector):
    content = "陈阳在公司开会，讨论融资计划。"
    result = detector.detect(content)
    
    assert result.genre_id.value == "urban"
    assert result.confidence > 0.8

@pytest.mark.asyncio
async def test_llm_generation():
    """测试LLM生成"""
    prompt = "生成一个都市主角"
    result = await llm.generate(prompt)
    
    assert len(result) > 100
    assert "都市" in result or "城市" in result
```

### 2. Hypothesis（属性测试）

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=10, max_size=1000))
def test_genre_detector_never_crashes(content):
    """GenreDetector不应该崩溃"""
    detector = GenreDetector()
    result = detector.detect(content)
    
    assert 0.0 <= result.confidence <= 1.0
```

### 3. LLM输出测试（自定义）

```python
async def test_llm_output_quality():
    """测试LLM输出质量"""
    prompt = get_chapter_prompt(genre="urban", chapter_num=1)
    content = await llm.generate(prompt)
    
    # 基础检查
    assert len(content) >= 1800  # 至少1800字
    assert len(content) <= 2500  # 不超过2500字
    
    # 题材约束检查
    validator = GenreValidator()
    result = validator.validate("urban", content)
    
    assert result.is_valid
    assert not result.has_blocking_violations
```

---

## 🚀 部署方案

### 容器化：Docker + Docker Compose

#### 开发环境

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/anovel
      - REDIS_URL=redis://redis:6379/0
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - postgres
      - redis
    volumes:
      - ./app:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  worker:
    build: .
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/anovel
      - REDIS_URL=redis://redis:6379/0
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - postgres
      - redis
    command: celery -A tasks worker --loglevel=info

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=anovel
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

#### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 暴露端口
EXPOSE 8000

# 默认命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 生产部署：Kubernetes（可选）

**简化方案**：先用Docker Compose + VPS
**扩展方案**：流量增长后迁移K8s

---

## 📊 监控与日志

### 1. 日志：Loguru

```python
from loguru import logger

# 配置
logger.add(
    "logs/anovel_{time}.log",
    rotation="500 MB",
    retention="10 days",
    level="INFO"
)

# 使用
logger.info("开始生成章节", chapter_id=chapter_id)
logger.error("LLM调用失败", error=str(e))

# LLM专用日志
@logger.catch
async def generate_with_logging(prompt: str) -> str:
    logger.info("LLM调用开始", prompt_length=len(prompt))
    
    start_time = time.time()
    result = await llm.generate(prompt)
    duration = time.time() - start_time
    
    logger.info(
        "LLM调用完成",
        duration=duration,
        input_tokens=count_tokens(prompt),
        output_tokens=count_tokens(result)
    )
    
    return result
```

### 2. 监控：Prometheus + Grafana（可选）

**简化方案**：先用日志
**扩展方案**：流量增长后添加

---

## 🔒 安全方案

### 1. API认证：JWT

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        return payload["user_id"]
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# 使用
@app.post("/generate/chapter")
async def generate_chapter(
    request: ChapterRequest,
    user_id: str = Depends(get_current_user)
):
    # 用户已认证
    pass
```

### 2. Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/generate/chapter")
@limiter.limit("10/minute")  # 每分钟最多10次
async def generate_chapter(request: Request):
    pass
```

---

## 📦 依赖管理：Poetry

### 为什么选Poetry

✅ **确定性依赖** - poetry.lock
✅ **虚拟环境管理**
✅ **简化发布**
✅ **现代化工具**

### pyproject.toml

```toml
[tool.poetry]
name = "anovel-v2"
version = "2.0.0"
description = "AI小说生成平台"
authors = ["Your Name <email@example.com>"]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
sqlalchemy = {extras = ["asyncio"], version = "^2.0.0"}
asyncpg = "^0.29.0"  # PostgreSQL异步驱动
redis = {extras = ["hiredis"], version = "^5.0.0"}
celery = "^5.3.0"
anthropic = "^0.25.0"
litellm = "^1.0.0"
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"
jinja2 = "^3.1.0"
loguru = "^0.7.0"
httpx = "^0.25.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-cov = "^4.1.0"
hypothesis = "^6.92.0"
black = "^23.11.0"
ruff = "^0.1.0"
mypy = "^1.7.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

---

## 🎨 前端方案（简化）

### 技术栈：**React + TypeScript + Vite**

**原因**：
- 不是核心重点
- 选择主流稳定方案
- 快速开发

**具体选择**：
- **框架**：React 18
- **语言**：TypeScript
- **构建**：Vite
- **UI库**：Ant Design / shadcn/ui
- **状态管理**：Zustand（轻量）
- **HTTP**：axios

**关注点**：
- API对接简单
- 实时更新（WebSocket/SSE）
- 暂不考虑复杂交互

---

## 📋 技术栈总结

### 核心技术栈

| 层级 | 技术选择 | 原因 |
|------|---------|------|
| **语言** | Python 3.11 | 类型支持、异步、LLM生态 |
| **Web框架** | FastAPI | 异步、类型安全、自动文档 |
| **LLM SDK** | Anthropic + LiteLLM | 官方SDK + 多模型统一 |
| **数据库** | PostgreSQL 15 | ACID + JSONB灵活性 |
| **缓存** | Redis 7 | 快速、可靠、多功能 |
| **ORM** | SQLAlchemy 2.0 | 异步、类型安全、成熟 |
| **任务队列** | Celery + Redis | 成熟稳定、易用 |
| **Prompt管理** | Jinja2 | 模板化、版本控制友好 |
| **测试** | Pytest + Hypothesis | 标准方案 |
| **日志** | Loguru | 简单强大 |
| **部署** | Docker Compose | 简单高效 |
| **依赖管理** | Poetry | 现代化 |

### 可选/未来扩展

| 功能 | 技术 | 时机 |
|------|------|------|
| 监控 | Prometheus + Grafana | 流量增长后 |
| 日志聚合 | ELK/Loki | 多实例后 |
| 容器编排 | Kubernetes | 大规模部署 |
| 消息队列 | RabbitMQ/Kafka | 复杂事件流 |
| NoSQL | MongoDB | 特殊需求 |

---

## ✅ V1项目对比改进

### V1使用的技术（参考ainovel/）

```
✅ Python（保留）
✅ FastAPI（保留）
❌ 缺少类型标注（改进：完整类型）
❌ 同步调用为主（改进：全异步）
❌ 无任务队列（改进：Celery）
❌ Prompt硬编码（改进：Jinja2模板）
❌ 无缓存（改进：Redis）
❌ 测试覆盖低（改进：完整测试）
```

### 主要改进点

1. **完整类型标注** - AI更易理解
2. **全异步架构** - 性能提升
3. **任务队列** - 解耦长时任务
4. **Prompt管理** - 版本控制友好
5. **缓存策略** - 降低成本
6. **完整测试** - 质量保证

---

## 🎯 实施建议

### Phase 1（MVP）

**必需技术**：
- Python 3.11
- FastAPI
- PostgreSQL
- Redis
- Anthropic SDK
- SQLAlchemy 2.0
- Pytest

**可延后**：
- Celery（先同步，流量大后加）
- 监控（先日志）
- K8s（先Docker Compose）

### Phase 2（优化）

**添加**：
- Celery任务队列
- LiteLLM多模型
- 完整测试覆盖
- 基础监控

### Phase 3（扩展）

**添加**：
- Prometheus监控
- K8s部署
- 多区域部署
- 高级优化

---

## 📚 参考资源

### 官方文档

- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy 2.0: https://docs.sqlalchemy.org/
- Anthropic API: https://docs.anthropic.com/
- LiteLLM: https://docs.litellm.ai/

### 最佳实践

- FastAPI最佳实践: https://github.com/zhanymkanov/fastapi-best-practices
- Python异步编程: https://realpython.com/async-io-python/
- PostgreSQL性能: https://www.postgresql.org/docs/current/performance-tips.html

---

**技术栈选型文档完成！** ✅

下一步：**15_SYSTEM_ARCHITECTURE_DESIGN.md**（系统架构设计）
