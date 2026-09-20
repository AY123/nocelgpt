# ANovel V2 API规格说明

**版本**: v1.0  
**制定日期**: 2026-09-18  
**状态**: Draft  
**用途**: 定义完整的RESTful API接口规范  

---

## 📋 文档目的

本文档定义ANovel V2的完整API规格，包括：
1. **API设计原则** - RESTful规范
2. **认证授权** - JWT机制
3. **核心接口** - Genesis/Production/管理
4. **数据格式** - 请求/响应规范
5. **错误处理** - 统一错误码
6. **API文档** - OpenAPI规范

设计原则：
- RESTful风格
- 统一响应格式
- 完整错误处理
- 版本控制
- 自动文档生成

---

## 🎯 API设计原则

### 1. RESTful约定

#### 资源命名

```
✅ 使用名词复数
GET    /api/v1/novels
POST   /api/v1/novels
GET    /api/v1/novels/{id}

❌ 不使用动词
GET    /api/v1/getNovels          # 错误
POST   /api/v1/createNovel        # 错误
```

#### HTTP方法语义

| 方法 | 语义 | 幂等性 | 安全性 |
|------|------|--------|--------|
| GET | 查询资源 | ✅ | ✅ |
| POST | 创建资源 | ❌ | ❌ |
| PUT | 完整更新 | ✅ | ❌ |
| PATCH | 部分更新 | ❌ | ❌ |
| DELETE | 删除资源 | ✅ | ❌ |

#### 嵌套资源

```
GET    /api/v1/novels/{novel_id}/chapters              # 获取小说的章节列表
POST   /api/v1/novels/{novel_id}/chapters              # 创建章节
GET    /api/v1/novels/{novel_id}/characters            # 获取小说的角色列表
GET    /api/v1/novels/{novel_id}/worldview             # 获取小说的世界观
```

### 2. 版本控制

**URL版本控制**

```
/api/v1/...  # 当前版本
/api/v2/...  # 未来版本
```

**版本升级策略**：
- 向后兼容的改动（添加字段）→ 不升级版本
- 破坏性改动（删除字段、修改行为）→ 升级版本
- 至少支持2个版本并行

### 3. 统一响应格式

#### 成功响应

```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "都市之巅",
    "genre_id": "urban"
  },
  "meta": {
    "timestamp": "2026-09-18T10:00:00Z",
    "request_id": "req_abc123"
  }
}
```

#### 列表响应（带分页）

```json
{
  "success": true,
  "data": [
    {"id": "1", "title": "小说1"},
    {"id": "2", "title": "小说2"}
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5,
    "has_next": true,
    "has_prev": false
  },
  "meta": {
    "timestamp": "2026-09-18T10:00:00Z",
    "request_id": "req_abc123"
  }
}
```

#### 错误响应

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid genre_id",
    "details": {
      "field": "genre_id",
      "value": "invalid_genre",
      "allowed_values": ["urban", "xuanhuan", "xianxia"]
    }
  },
  "meta": {
    "timestamp": "2026-09-18T10:00:00Z",
    "request_id": "req_abc123"
  }
}
```

---

## 🔐 认证授权

### JWT认证

#### 登录流程

```
POST /api/v1/auth/login

Request:
{
  "username": "user@example.com",
  "password": "password123"
}

Response:
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "user": {
      "id": "user_uuid",
      "username": "user",
      "email": "user@example.com",
      "role": "user"
    }
  }
}
```

#### Token使用

```
GET /api/v1/novels
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

#### Token刷新

```
POST /api/v1/auth/refresh

Request:
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}

Response:
{
  "success": true,
  "data": {
    "access_token": "new_access_token",
    "expires_in": 3600
  }
}
```

### 权限级别

| 角色 | 权限 |
|------|------|
| **user** | 创建自己的小说、章节 |
| **premium** | user权限 + 高级功能 |
| **admin** | 所有权限 + 管理功能 |

---

## 📚 API端点详细说明

### 1. 认证相关（/api/v1/auth）

#### 1.1 注册

```
POST /api/v1/auth/register

Request:
{
  "username": "newuser",
  "email": "user@example.com",
  "password": "password123",
  "password_confirm": "password123"
}

Response: 201 Created
{
  "success": true,
  "data": {
    "user_id": "uuid",
    "username": "newuser",
    "email": "user@example.com",
    "message": "注册成功，请查收验证邮件"
  }
}

Errors:
- 400: 用户名已存在
- 400: 邮箱已注册
- 400: 密码不匹配
```

#### 1.2 登录

```
POST /api/v1/auth/login

Request:
{
  "username": "user@example.com",  # 邮箱或用户名
  "password": "password123"
}

Response: 200 OK
{
  "success": true,
  "data": {
    "access_token": "...",
    "refresh_token": "...",
    "user": {...}
  }
}

Errors:
- 401: 用户名或密码错误
- 403: 账号已被封禁
```

#### 1.3 登出

```
POST /api/v1/auth/logout
Authorization: Bearer {token}

Response: 200 OK
{
  "success": true,
  "data": {
    "message": "登出成功"
  }
}
```

### 2. 用户相关（/api/v1/users）

#### 2.1 获取当前用户信息

```
GET /api/v1/users/me
Authorization: Bearer {token}

Response: 200 OK
{
  "success": true,
  "data": {
    "id": "uuid",
    "username": "user",
    "email": "user@example.com",
    "display_name": "用户昵称",
    "avatar_url": "https://...",
    "role": "user",
    "novels_count": 5,
    "chapters_count": 100,
    "created_at": "2026-09-01T10:00:00Z"
  }
}
```

#### 2.2 更新用户信息

```
PATCH /api/v1/users/me
Authorization: Bearer {token}

Request:
{
  "display_name": "新昵称",
  "bio": "个人简介"
}

Response: 200 OK
{
  "success": true,
  "data": {
    "id": "uuid",
    "display_name": "新昵称",
    "bio": "个人简介",
    "updated_at": "2026-09-18T10:00:00Z"
  }
}
```

### 3. 创世相关（/api/v1/genesis）

#### 3.1 创建创世任务

```
POST /api/v1/genesis
Authorization: Bearer {token}

Request:
{
  "genre_id": "urban",
  "user_input": "一个程序员通过创业逆袭成为商业大佬的故事",
  "title": "都市之巅"  # 可选
}

Response: 202 Accepted
{
  "success": true,
  "data": {
    "task_id": "task_uuid",
    "status": "queued",
    "status_url": "/api/v1/tasks/{task_id}"
  }
}

Errors:
- 400: 无效的genre_id
- 400: user_input太短（至少10字）
- 429: 请求过于频繁
```

#### 3.2 查询创世任务状态

```
GET /api/v1/tasks/{task_id}
Authorization: Bearer {token}

Response: 200 OK
{
  "success": true,
  "data": {
    "task_id": "task_uuid",
    "status": "completed",  # queued/generating/completed/failed
    "progress": 100,
    "result": {
      "novel_id": "novel_uuid",
      "outline": {...},
      "characters": [...],
      "worldview": {...}
    },
    "created_at": "2026-09-18T10:00:00Z",
    "completed_at": "2026-09-18T10:05:00Z"
  }
}

Status值:
- queued: 排队中
- generating: 生成中
- completed: 已完成
- failed: 失败
```

### 4. 小说管理（/api/v1/novels）

#### 4.1 获取小说列表

```
GET /api/v1/novels?page=1&page_size=20&status=writing&sort=updated_at&order=desc
Authorization: Bearer {token}

Query Parameters:
- page: 页码（默认1）
- page_size: 每页数量（默认20，最大100）
- status: 状态筛选（draft/writing/completed/published）
- genre_id: 题材筛选
- sort: 排序字段（created_at/updated_at/title）
- order: 排序方向（asc/desc）

Response: 200 OK
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "title": "都市之巅",
      "genre_id": "urban",
      "status": "writing",
      "total_chapters": 50,
      "total_words": 100000,
      "created_at": "2026-09-01T10:00:00Z",
      "updated_at": "2026-09-18T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 5,
    "total_pages": 1
  }
}
```

#### 4.2 获取小说详情

```
GET /api/v1/novels/{novel_id}
Authorization: Bearer {token}

Response: 200 OK
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "都市之巅",
    "genre_id": "urban",
    "description": "一个程序员的逆袭之路",
    "status": "writing",
    "total_chapters": 50,
    "total_words": 100000,
    "published_chapters": 40,
    "target_chapters": 1000,
    "target_words": 2000000,
    "created_at": "2026-09-01T10:00:00Z",
    "updated_at": "2026-09-18T10:00:00Z",
    "statistics": {
      "avg_quality_score": 85.5,
      "character_count": 12,
      "reviewed_chapters": 10
    }
  }
}

Errors:
- 404: 小说不存在
- 403: 无权限访问
```

#### 4.3 更新小说信息

```
PATCH /api/v1/novels/{novel_id}
Authorization: Bearer {token}

Request:
{
  "title": "新标题",
  "description": "新描述",
  "status": "completed"
}

Response: 200 OK
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "新标题",
    "updated_at": "2026-09-18T10:00:00Z"
  }
}
```

#### 4.4 删除小说

```
DELETE /api/v1/novels/{novel_id}
Authorization: Bearer {token}

Response: 200 OK
{
  "success": true,
  "data": {
    "message": "小说已删除"
  }
}

Errors:
- 404: 小说不存在
- 403: 无权限删除
```

### 5. 章节管理（/api/v1/chapters）

#### 5.1 获取章节列表

```
GET /api/v1/novels/{novel_id}/chapters?page=1&page_size=20
Authorization: Bearer {token}

Response: 200 OK
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "chapter_number": 1,
      "title": "穷学生的梦想",
      "word_count": 2050,
      "status": "published",
      "quality_score": 88.5,
      "created_at": "2026-09-01T10:00:00Z"
    }
  ],
  "pagination": {...}
}
```

#### 5.2 获取章节详情

```
GET /api/v1/chapters/{chapter_id}
Authorization: Bearer {token}

Response: 200 OK
{
  "success": true,
  "data": {
    "id": "uuid",
    "novel_id": "novel_uuid",
    "chapter_number": 1,
    "title": "穷学生的梦想",
    "content": "章节正文内容...",
    "word_count": 2050,
    "status": "published",
    "quality_score": 88.5,
    "validation_results": {
      "genre_compliance": 95,
      "text_quality": 85,
      "overall": 88.5
    },
    "created_at": "2026-09-01T10:00:00Z",
    "published_at": "2026-09-01T11:00:00Z"
  }
}
```

#### 5.3 生成新章节

```
POST /api/v1/novels/{novel_id}/chapters
Authorization: Bearer {token}

Request:
{
  "chapter_number": 51,  # 可选，默认为当前最大章节号+1
  "auto_generate": true  # 是否自动生成，false则只创建大纲
}

Response: 202 Accepted
{
  "success": true,
  "data": {
    "task_id": "task_uuid",
    "chapter_id": "chapter_uuid",
    "status": "queued",
    "status_url": "/api/v1/tasks/{task_id}"
  }
}

Errors:
- 400: 章节号已存在
- 400: 缺少必要的上下文（大纲、角色等）
- 429: 生成请求过于频繁
```

#### 5.4 更新章节

```
PATCH /api/v1/chapters/{chapter_id}
Authorization: Bearer {token}

Request:
{
  "title": "新标题",
  "content": "更新后的内容",
  "status": "published"
}

Response: 200 OK
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "新标题",
    "word_count": 2100,
    "updated_at": "2026-09-18T10:00:00Z"
  }
}
```

#### 5.5 删除章节

```
DELETE /api/v1/chapters/{chapter_id}
Authorization: Bearer {token}

Response: 200 OK
{
  "success": true,
  "data": {
    "message": "章节已删除"
  }
}
```

### 6. 角色管理（/api/v1/characters）

#### 6.1 获取角色列表

```
GET /api/v1/novels/{novel_id}/characters
Authorization: Bearer {token}

Response: 200 OK
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "name": "陈阳",
      "role": "protagonist",
      "age": 25,
      "gender": "male",
      "genre_id": "urban",
      "genre_attributes": {
        "wealth_tier": "温饱",
        "occupation": "程序员"
      },
      "created_at": "2026-09-01T10:00:00Z"
    }
  ]
}
```

#### 6.2 获取角色详情

```
GET /api/v1/characters/{character_id}
Authorization: Bearer {token}

Response: 200 OK
{
  "success": true,
  "data": {
    "id": "uuid",
    "novel_id": "novel_uuid",
    "name": "陈阳",
    "name_en": "Chen Yang",
    "gender": "male",
    "age": 25,
    "role": "protagonist",
    "status": "alive",
    "appearance": "清秀俊朗",
    "personality_traits": ["果断", "聪明", "坚韧"],
    "personality_description": "性格坚韧...",
    "background": "贫困家庭出身...",
    "motivation": "改变家族命运",
    "goal": "成为行业领军人物",
    "genre_attributes": {
      "wealth_tier": "温饱",
      "wealth_details": {
        "annual_income": 80000,
        "savings": 50000
      },
      "occupation": "程序员",
      "skills": ["Python", "架构设计"]
    },
    "relationships": [
      {
        "character_id": "other_uuid",
        "character_name": "李明",
        "relationship_type": "friendship",
        "description": "大学室友"
      }
    ]
  }
}
```

#### 6.3 创建角色

```
POST /api/v1/novels/{novel_id}/characters
Authorization: Bearer {token}

Request:
{
  "name": "李明",
  "gender": "male",
  "age": 26,
  "role": "supporting",
  "personality_traits": ["热情", "忠诚"],
  "background": "富二代，陈阳的好友",
  "genre_attributes": {
    "wealth_tier": "富裕",
    "occupation": "企业继承人"
  }
}

Response: 201 Created
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "李明",
    "created_at": "2026-09-18T10:00:00Z"
  }
}
```

#### 6.4 更新角色

```
PATCH /api/v1/characters/{character_id}
Authorization: Bearer {token}

Request:
{
  "age": 26,
  "genre_attributes": {
    "wealth_tier": "小康",  # 财富进阶
    "occupation": "创业者"
  }
}

Response: 200 OK
{
  "success": true,
  "data": {
    "id": "uuid",
    "age": 26,
    "genre_attributes": {...},
    "updated_at": "2026-09-18T10:00:00Z"
  }
}
```

### 7. 世界观管理（/api/v1/worldviews）

#### 7.1 获取世界观

```
GET /api/v1/novels/{novel_id}/worldview
Authorization: Bearer {token}

Response: 200 OK
{
  "success": true,
  "data": {
    "id": "uuid",
    "novel_id": "novel_uuid",
    "name": "2025年中国科技圈",
    "genre_id": "urban",
    "description": "互联网与AI行业为主",
    "time_period": "2025年",
    "geography": "北京、深圳",
    "genre_settings": {
      "economic_system": "市场经济",
      "major_industries": ["互联网", "AI", "金融科技"],
      "technology_level": "现代科技（5G、AI）"
    },
    "created_at": "2026-09-01T10:00:00Z"
  }
}
```

#### 7.2 更新世界观

```
PATCH /api/v1/novels/{novel_id}/worldview
Authorization: Bearer {token}

Request:
{
  "description": "更新后的描述",
  "genre_settings": {
    "major_industries": ["互联网", "AI", "生物科技"]
  }
}

Response: 200 OK
{
  "success": true,
  "data": {
    "id": "uuid",
    "updated_at": "2026-09-18T10:00:00Z"
  }
}
```

### 8. 大纲管理（/api/v1/outlines）

#### 8.1 获取大纲

```
GET /api/v1/novels/{novel_id}/outline
Authorization: Bearer {token}

Response: 200 OK
{
  "success": true,
  "data": {
    "id": "uuid",
    "novel_id": "novel_uuid",
    "title": "都市之巅",
    "premise": "程序员创业逆袭",
    "total_chapters_target": 1000,
    "total_words_target": 2000000,
    "themes": ["奋斗", "成长", "商战"],
    "tone": "励志",
    "arcs": [
      {
        "id": "arc_uuid",
        "arc_number": 1,
        "title": "创业起步篇",
        "chapter_start": 1,
        "chapter_end": 100,
        "main_conflict": "资金短缺与市场竞争",
        "main_goal": "获得天使投资"
      }
    ],
    "status": "approved"
  }
}
```

#### 8.2 更新大纲

```
PATCH /api/v1/novels/{novel_id}/outline
Authorization: Bearer {token}

Request:
{
  "total_chapters_target": 1200,
  "themes": ["奋斗", "成长", "商战", "情感"]
}

Response: 200 OK
{
  "success": true,
  "data": {
    "id": "uuid",
    "updated_at": "2026-09-18T10:00:00Z"
  }
}
```

### 9. 质量审核（/api/v1/reviews）

#### 9.1 获取待审核列表

```
GET /api/v1/reviews?status=pending
Authorization: Bearer {token}
Requires: admin role

Response: 200 OK
{
  "success": true,
  "data": [
    {
      "id": "review_uuid",
      "chapter_id": "chapter_uuid",
      "novel_id": "novel_uuid",
      "chapter_number": 5,
      "chapter_title": "初露锋芒",
      "auto_metrics": {
        "overall_score": 72,
        "genre_compliance": 95,
        "text_quality": 70
      },
      "trigger_reasons": ["文本质量需关注"],
      "status": "pending",
      "created_at": "2026-09-18T09:00:00Z"
    }
  ],
  "pagination": {...}
}
```

#### 9.2 提交审核结果

```
POST /api/v1/reviews/{review_id}/submit
Authorization: Bearer {token}
Requires: admin role

Request:
{
  "status": "approved",  # approved/rejected/needs_revision
  "action": "publish",   # publish/revise/regenerate
  "manual_score": 85,
  "manual_comments": "整体不错，个别用词可以优化",
  "revision_instructions": "第3段的对话需要更自然"  # 如果action=revise
}

Response: 200 OK
{
  "success": true,
  "data": {
    "review_id": "uuid",
    "status": "approved",
    "reviewed_at": "2026-09-18T10:00:00Z"
  }
}
```

### 10. 统计分析（/api/v1/stats）

#### 10.1 用户统计

```
GET /api/v1/stats/user
Authorization: Bearer {token}

Response: 200 OK
{
  "success": true,
  "data": {
    "novels_count": 5,
    "chapters_count": 250,
    "total_words": 500000,
    "avg_quality_score": 85.2,
    "this_month": {
      "chapters_created": 20,
      "words_written": 40000
    }
  }
}
```

#### 10.2 小说统计

```
GET /api/v1/novels/{novel_id}/stats
Authorization: Bearer {token}

Response: 200 OK
{
  "success": true,
  "data": {
    "total_chapters": 50,
    "total_words": 100000,
    "avg_quality_score": 85.5,
    "quality_distribution": {
      "A": 15,
      "B": 30,
      "C": 5,
      "D": 0
    },
    "generation_cost": 120.50,  # USD
    "timeline": [
      {
        "date": "2026-09-01",
        "chapters": 2,
        "words": 4000
      }
    ]
  }
}
```

---

## 📊 通用参数

### 分页参数

```
?page=1              # 页码（从1开始）
?page_size=20        # 每页数量（默认20，最大100）
```

### 排序参数

```
?sort=created_at     # 排序字段
?order=desc          # 排序方向（asc/desc）
```

### 筛选参数

```
?status=published    # 状态筛选
?genre_id=urban      # 题材筛选
?search=关键词       # 搜索
```

---

## ⚠️ 错误码

### HTTP状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 202 | 已接受（异步任务） |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 422 | 验证失败 |
| 429 | 请求过于频繁 |
| 500 | 服务器错误 |

### 业务错误码

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "验证失败",
    "details": {...}
  }
}
```

| 错误码 | HTTP状态 | 说明 |
|--------|---------|------|
| VALIDATION_ERROR | 400 | 请求参数验证失败 |
| AUTHENTICATION_REQUIRED | 401 | 需要认证 |
| INVALID_TOKEN | 401 | Token无效或过期 |
| PERMISSION_DENIED | 403 | 权限不足 |
| RESOURCE_NOT_FOUND | 404 | 资源不存在 |
| RESOURCE_CONFLICT | 409 | 资源冲突（如重复创建） |
| RATE_LIMIT_EXCEEDED | 429 | 超过频率限制 |
| GENRE_VIOLATION | 422 | 违反题材约束 |
| QUALITY_TOO_LOW | 422 | 质量不达标 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |
| LLM_ERROR | 500 | LLM调用失败 |

---

## 📖 OpenAPI规范

### Swagger/OpenAPI 3.0

FastAPI自动生成，访问：
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`
- OpenAPI JSON: `http://localhost:8000/api/openapi.json`

### 示例Schema定义

```python
from pydantic import BaseModel, Field
from typing import Optional, List

class NovelCreate(BaseModel):
    """创建小说请求"""
    title: str = Field(..., min_length=1, max_length=200, description="小说标题")
    genre_id: str = Field(..., description="题材ID")
    description: Optional[str] = Field(None, description="小说描述")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "都市之巅",
                "genre_id": "urban",
                "description": "一个程序员的逆袭之路"
            }
        }

class NovelResponse(BaseModel):
    """小说响应"""
    id: str
    title: str
    genre_id: str
    status: str
    total_chapters: int
    total_words: int
    created_at: str
    updated_at: str
```

---

## 🚀 速率限制

### 限制策略

| 端点类型 | 限制 |
|---------|------|
| 登录/注册 | 5次/分钟 |
| 创世生成 | 3次/小时 |
| 章节生成 | 10次/小时 |
| 查询接口 | 60次/分钟 |
| 其他写操作 | 30次/分钟 |

### 响应头

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1632147600
```

### 超限响应

```
HTTP/1.1 429 Too Many Requests

{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "请求过于频繁，请稍后再试",
    "details": {
      "retry_after": 60
    }
  }
}
```

---

## 🎯 实施清单

### Phase 1（MVP）

**实现**：
- 认证授权（JWT）
- 小说CRUD
- 章节CRUD
- 角色CRUD
- 创世API（基础）
- 章节生成API

**不做**：
- 复杂统计
- 高级筛选
- WebSocket实时通信

### Phase 2（优化）

**添加**：
- 完整创世流程API
- 质量审核API
- 统计分析API
- 高级搜索

### Phase 3（扩展）

**添加**：
- WebSocket（实时进度）
- GraphQL（可选）
- Webhook
- 批量操作API

---

**API规格说明文档完成！** ✅

第二批（3个核心文档）全部完成：
1. ✅ 17_QUALITY_ASSURANCE_FRAMEWORK.md（1,063行）
2. ✅ 18_DATABASE_SCHEMA_DESIGN.md（1,045行）
3. ✅ 19_API_SPECIFICATION.md（当前文档）
