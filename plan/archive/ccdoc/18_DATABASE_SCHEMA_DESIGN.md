# ANovel V2 数据库Schema设计

**版本**: v1.0  
**制定日期**: 2026-09-18  
**状态**: Draft  
**用途**: 定义PostgreSQL数据库完整Schema  

---

## 📋 文档目的

本文档基于 `13_DATA_MODEL_COMPLETE_DEFINITION.md` 中定义的领域模型，设计PostgreSQL数据库Schema，包括：
1. **表结构设计** - 所有核心表
2. **索引策略** - 查询优化
3. **约束规则** - 数据完整性
4. **关系设计** - 外键和关联
5. **迁移策略** - 版本管理

设计原则：
- 基于领域模型
- JSONB灵活存储Genre专属数据
- 合理的范式化（3NF为主）
- 性能优先的索引
- 支持未来扩展

---

## 🗄️ 数据库选型确认

**选择**: PostgreSQL 15+

**理由**：
- ✅ JSONB支持（存储Genre专属属性）
- ✅ 强大的索引（GIN索引支持JSONB查询）
- ✅ 全文搜索
- ✅ 事务支持（ACID）
- ✅ 免费开源
- ✅ 成熟稳定

---

## 📊 整体ER图

```
┌─────────┐         ┌──────────┐         ┌─────────┐
│  users  │────────▶│  novels  │◀────────│ genres  │
└─────────┘         └────┬─────┘         └─────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼──────┐   ┌────▼────┐   ┌──────▼──────┐
   │characters │   │worldview│   │   outline   │
   └───────────┘   └─────────┘   └──────┬──────┘
                                         │
                                    ┌────▼────┐
                                    │  arcs   │
                                    └────┬────┘
                                         │
                                ┌────────┼────────┐
                                │                 │
                        ┌───────▼──────┐   ┌─────▼──────┐
                        │chapter_outlines│   │  chapters  │
                        └──────────────┘   └────────────┘

   ┌──────────────┐
   │relationships │  (角色关系，独立表)
   └──────────────┘
```

---

## 📋 核心表设计

### 1. users（用户表）

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 基本信息
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    
    -- 个人信息
    display_name VARCHAR(100),
    avatar_url TEXT,
    bio TEXT,
    
    -- 状态
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active/suspended/deleted
    email_verified BOOLEAN DEFAULT FALSE,
    
    -- 权限
    role VARCHAR(20) NOT NULL DEFAULT 'user',  -- user/premium/admin
    
    -- 统计
    novels_count INTEGER DEFAULT 0,
    chapters_count INTEGER DEFAULT 0,
    
    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMP,
    
    -- 元数据
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- 索引
    CONSTRAINT users_username_length CHECK (char_length(username) >= 3),
    CONSTRAINT users_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- 索引
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_created_at ON users(created_at DESC);
CREATE INDEX idx_users_metadata ON users USING GIN (metadata);

-- 注释
COMMENT ON TABLE users IS '用户表';
COMMENT ON COLUMN users.role IS 'user=普通用户, premium=付费用户, admin=管理员';
```

### 2. novels（小说表）

```sql
CREATE TABLE novels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 所属用户
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 基本信息
    title VARCHAR(200) NOT NULL,
    genre_id VARCHAR(50) NOT NULL,  -- urban/xuanhuan/xianxia...
    description TEXT,
    cover_url TEXT,
    
    -- 状态
    status VARCHAR(20) NOT NULL DEFAULT 'draft',  -- draft/writing/completed/published
    
    -- 统计
    total_chapters INTEGER DEFAULT 0,
    total_words INTEGER DEFAULT 0,
    published_chapters INTEGER DEFAULT 0,
    
    -- 目标
    target_chapters INTEGER,
    target_words INTEGER,
    
    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    published_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- 元数据
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- 约束
    CONSTRAINT novels_title_not_empty CHECK (char_length(title) > 0)
);

-- 索引
CREATE INDEX idx_novels_user_id ON novels(user_id);
CREATE INDEX idx_novels_genre_id ON novels(genre_id);
CREATE INDEX idx_novels_status ON novels(status);
CREATE INDEX idx_novels_created_at ON novels(created_at DESC);
CREATE INDEX idx_novels_metadata ON novels USING GIN (metadata);

-- 注释
COMMENT ON TABLE novels IS '小说表';
COMMENT ON COLUMN novels.status IS 'draft=草稿, writing=创作中, completed=已完成, published=已发布';
```

### 3. characters（角色表）

```sql
CREATE TABLE characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 所属小说
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    
    -- 基本信息
    name VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    gender VARCHAR(20) NOT NULL,  -- male/female/other
    age INTEGER,
    
    -- 角色定位
    role VARCHAR(50) NOT NULL,  -- protagonist/antagonist/supporting...
    status VARCHAR(20) NOT NULL DEFAULT 'alive',  -- alive/dead/missing...
    
    -- 外貌
    appearance TEXT,
    appearance_details TEXT,
    
    -- 性格
    personality_traits JSONB DEFAULT '[]'::jsonb,  -- 数组
    personality_description TEXT,
    
    -- 背景与动机
    background TEXT,
    motivation TEXT,
    goal TEXT,
    
    -- 通用属性（所有题材共有）
    base_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- 题材专属属性（根据genre_id不同而不同）
    genre_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- 标签和元数据
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- 约束
    CONSTRAINT characters_name_not_empty CHECK (char_length(name) > 0),
    CONSTRAINT characters_age_positive CHECK (age IS NULL OR age > 0)
);

-- 索引
CREATE INDEX idx_characters_novel_id ON characters(novel_id);
CREATE INDEX idx_characters_role ON characters(role);
CREATE INDEX idx_characters_name ON characters(name);
CREATE INDEX idx_characters_genre_attrs ON characters USING GIN (genre_attributes);
CREATE INDEX idx_characters_tags ON characters USING GIN (tags);

-- 注释
COMMENT ON TABLE characters IS '角色表';
COMMENT ON COLUMN characters.base_attributes IS '通用属性（JSON）';
COMMENT ON COLUMN characters.genre_attributes IS '题材专属属性，如都市的wealth_tier、玄幻的cultivation_tier';
```

### 4. worldviews（世界观表）

```sql
CREATE TABLE worldviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 所属小说
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    
    -- 基本信息
    name VARCHAR(200) NOT NULL,
    genre_id VARCHAR(50) NOT NULL,
    description TEXT,
    version VARCHAR(20) DEFAULT '1.0',
    
    -- 时空设定
    time_period VARCHAR(200),
    geography TEXT,
    locations JSONB DEFAULT '[]'::jsonb,  -- [{name, description, type}, ...]
    
    -- 基础规则
    fundamental_rules JSONB DEFAULT '[]'::jsonb,
    constraints JSONB DEFAULT '[]'::jsonb,
    
    -- 题材专属设定
    genre_settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- 元数据
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 索引
CREATE INDEX idx_worldviews_novel_id ON worldviews(novel_id);
CREATE INDEX idx_worldviews_genre_id ON worldviews(genre_id);
CREATE INDEX idx_worldviews_genre_settings ON worldviews USING GIN (genre_settings);

-- 注释
COMMENT ON TABLE worldviews IS '世界观表';
COMMENT ON COLUMN worldviews.genre_settings IS '题材专属设定，如都市的经济体系、玄幻的修炼体系';
```

### 5. outlines（大纲表）

```sql
CREATE TABLE outlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 所属小说
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    
    -- 基本信息
    title VARCHAR(200),
    premise TEXT NOT NULL,  -- 故事前提
    
    -- 结构规划
    total_words_target INTEGER DEFAULT 1000000,
    total_chapters_target INTEGER DEFAULT 500,
    
    -- 核心元素
    protagonist_id UUID REFERENCES characters(id),
    main_characters UUID[] DEFAULT '{}',  -- 主要角色ID数组
    worldview_id UUID REFERENCES worldviews(id),
    
    -- 主题与风格
    themes JSONB DEFAULT '[]'::jsonb,
    tone VARCHAR(100),
    target_audience VARCHAR(100),
    
    -- 状态
    status VARCHAR(20) NOT NULL DEFAULT 'draft',  -- draft/approved/in_production/completed
    version VARCHAR(20) DEFAULT '1.0',
    
    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMP,
    
    -- 元数据
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 索引
CREATE INDEX idx_outlines_novel_id ON outlines(novel_id);
CREATE INDEX idx_outlines_status ON outlines(status);
CREATE INDEX idx_outlines_protagonist_id ON outlines(protagonist_id);

-- 注释
COMMENT ON TABLE outlines IS '大纲表（总大纲）';
```

### 6. arcs（故事弧表）

```sql
CREATE TABLE arcs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 所属大纲
    outline_id UUID NOT NULL REFERENCES outlines(id) ON DELETE CASCADE,
    
    -- 基本信息
    arc_number INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    
    -- 结构
    chapter_start INTEGER NOT NULL,
    chapter_end INTEGER NOT NULL,
    chapter_count INTEGER NOT NULL,
    
    -- 情节核心
    main_conflict TEXT,
    main_goal TEXT,
    resolution TEXT,
    
    -- 角色
    featured_characters UUID[] DEFAULT '{}',
    new_characters UUID[] DEFAULT '{}',
    
    -- 进展
    character_growth TEXT,
    plot_progression TEXT,
    
    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- 元数据
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- 约束
    CONSTRAINT arcs_chapter_range CHECK (chapter_start <= chapter_end),
    CONSTRAINT arcs_chapter_count_match CHECK (chapter_count = chapter_end - chapter_start + 1),
    UNIQUE (outline_id, arc_number)
);

-- 索引
CREATE INDEX idx_arcs_outline_id ON arcs(outline_id);
CREATE INDEX idx_arcs_arc_number ON arcs(outline_id, arc_number);
CREATE INDEX idx_arcs_chapter_range ON arcs(chapter_start, chapter_end);

-- 注释
COMMENT ON TABLE arcs IS '故事弧表';
```

### 7. chapter_outlines（章节大纲表）

```sql
CREATE TABLE chapter_outlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 所属故事弧
    arc_id UUID NOT NULL REFERENCES arcs(id) ON DELETE CASCADE,
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    
    -- 章节信息
    chapter_number INTEGER NOT NULL,
    title VARCHAR(200),
    
    -- 内容规划
    summary TEXT,
    key_events JSONB DEFAULT '[]'::jsonb,
    pov_character_id UUID REFERENCES characters(id),
    
    -- 场景
    scenes JSONB DEFAULT '[]'::jsonb,  -- [{name, description, duration}, ...]
    location VARCHAR(200),
    time_of_day VARCHAR(50),
    
    -- 情节
    conflict TEXT,
    climax TEXT,
    cliffhanger TEXT,
    
    -- 角色
    characters_present UUID[] DEFAULT '{}',
    
    -- 目标
    target_words INTEGER DEFAULT 2000,
    
    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- 元数据
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- 约束
    UNIQUE (novel_id, chapter_number)
);

-- 索引
CREATE INDEX idx_chapter_outlines_arc_id ON chapter_outlines(arc_id);
CREATE INDEX idx_chapter_outlines_novel_id ON chapter_outlines(novel_id);
CREATE INDEX idx_chapter_outlines_chapter_number ON chapter_outlines(novel_id, chapter_number);
CREATE INDEX idx_chapter_outlines_pov_character ON chapter_outlines(pov_character_id);

-- 注释
COMMENT ON TABLE chapter_outlines IS '章节大纲表';
```

### 8. chapters（章节内容表）

```sql
CREATE TABLE chapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 所属小说
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    
    -- 章节信息
    chapter_number INTEGER NOT NULL,
    arc_id UUID REFERENCES arcs(id),
    outline_id UUID REFERENCES chapter_outlines(id),
    
    -- 内容
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER NOT NULL DEFAULT 0,
    
    -- 元数据
    genre_id VARCHAR(50) NOT NULL,
    
    -- 状态
    status VARCHAR(20) NOT NULL DEFAULT 'draft',  -- draft/generating/reviewing/approved/published
    version VARCHAR(20) DEFAULT '1.0',
    
    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    published_at TIMESTAMP,
    
    -- 质量相关
    quality_score FLOAT,
    validation_results JSONB DEFAULT '{}'::jsonb,
    
    -- 生成信息
    generation_metadata JSONB DEFAULT '{}'::jsonb,
    generation_attempts INTEGER DEFAULT 1,
    revision_count INTEGER DEFAULT 0,
    
    -- 人工审核
    human_reviewed BOOLEAN DEFAULT FALSE,
    reviewer_id UUID REFERENCES users(id),
    review_time TIMESTAMP,
    review_comments TEXT,
    
    -- 约束
    CONSTRAINT chapters_word_count_positive CHECK (word_count >= 0),
    CONSTRAINT chapters_quality_score_range CHECK (quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 100)),
    UNIQUE (novel_id, chapter_number)
);

-- 索引
CREATE INDEX idx_chapters_novel_id ON chapters(novel_id);
CREATE INDEX idx_chapters_chapter_number ON chapters(novel_id, chapter_number);
CREATE INDEX idx_chapters_status ON chapters(status);
CREATE INDEX idx_chapters_arc_id ON chapters(arc_id);
CREATE INDEX idx_chapters_created_at ON chapters(created_at DESC);
CREATE INDEX idx_chapters_quality_score ON chapters(quality_score);
CREATE INDEX idx_chapters_validation_results ON chapters USING GIN (validation_results);
CREATE INDEX idx_chapters_generation_metadata ON chapters USING GIN (generation_metadata);

-- 全文搜索索引
CREATE INDEX idx_chapters_content_fts ON chapters USING GIN (to_tsvector('chinese', content));
CREATE INDEX idx_chapters_title_fts ON chapters USING GIN (to_tsvector('chinese', title));

-- 注释
COMMENT ON TABLE chapters IS '章节内容表';
COMMENT ON COLUMN chapters.generation_metadata IS 'LLM生成相关信息：模型、tokens、成本等';
COMMENT ON COLUMN chapters.validation_results IS '质量检测结果：题材符合度、文本质量等';
```

### 9. relationships（角色关系表）

```sql
CREATE TABLE relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 关系双方
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    character_a_id UUID NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    character_b_id UUID NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    
    -- 关系类型
    relationship_type VARCHAR(50) NOT NULL,  -- family/romantic/friendship/rivalry...
    
    -- 关系描述
    description TEXT,
    intensity INTEGER DEFAULT 50,  -- 0-100
    is_mutual BOOLEAN DEFAULT TRUE,
    
    -- 关系动态
    established_at_chapter INTEGER DEFAULT 0,
    current_status VARCHAR(50) DEFAULT 'active',
    status_history JSONB DEFAULT '[]'::jsonb,
    
    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- 标签和元数据
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- 约束
    CONSTRAINT relationships_intensity_range CHECK (intensity >= 0 AND intensity <= 100),
    CONSTRAINT relationships_different_characters CHECK (character_a_id != character_b_id),
    UNIQUE (novel_id, character_a_id, character_b_id, relationship_type)
);

-- 索引
CREATE INDEX idx_relationships_novel_id ON relationships(novel_id);
CREATE INDEX idx_relationships_character_a ON relationships(character_a_id);
CREATE INDEX idx_relationships_character_b ON relationships(character_b_id);
CREATE INDEX idx_relationships_type ON relationships(relationship_type);
CREATE INDEX idx_relationships_tags ON relationships USING GIN (tags);

-- 注释
COMMENT ON TABLE relationships IS '角色关系表';
COMMENT ON COLUMN relationships.intensity IS '关系强度，0=陌生，100=极度紧密';
```

### 10. llm_call_logs（LLM调用日志表）

```sql
CREATE TABLE llm_call_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 调用信息
    call_id VARCHAR(100) UNIQUE NOT NULL,
    user_id UUID REFERENCES users(id),
    novel_id UUID REFERENCES novels(id),
    chapter_id UUID REFERENCES chapters(id),
    
    -- 模型信息
    model VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,  -- anthropic/openai/...
    
    -- Prompt和响应
    prompt TEXT NOT NULL,
    response TEXT,
    
    -- Token和成本
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    cost_usd DECIMAL(10, 6),
    
    -- 性能
    latency_ms INTEGER,
    
    -- 状态
    success BOOLEAN NOT NULL,
    error_message TEXT,
    
    -- 用途
    purpose VARCHAR(50),  -- genesis/production/validation...
    
    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- 元数据
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 索引
CREATE INDEX idx_llm_logs_call_id ON llm_call_logs(call_id);
CREATE INDEX idx_llm_logs_user_id ON llm_call_logs(user_id);
CREATE INDEX idx_llm_logs_novel_id ON llm_call_logs(novel_id);
CREATE INDEX idx_llm_logs_chapter_id ON llm_call_logs(chapter_id);
CREATE INDEX idx_llm_logs_created_at ON llm_call_logs(created_at DESC);
CREATE INDEX idx_llm_logs_model ON llm_call_logs(model);
CREATE INDEX idx_llm_logs_purpose ON llm_call_logs(purpose);
CREATE INDEX idx_llm_logs_success ON llm_call_logs(success);

-- 分区（按月）
-- CREATE TABLE llm_call_logs_2026_09 PARTITION OF llm_call_logs
--     FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');

-- 注释
COMMENT ON TABLE llm_call_logs IS 'LLM调用日志表（用于成本追踪和问题排查）';
```

### 11. quality_reviews（质量审核表）

```sql
CREATE TABLE quality_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 审核对象
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    
    -- 审核员
    reviewer_id UUID REFERENCES users(id),
    
    -- 自动检测结果
    auto_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    trigger_reasons JSONB DEFAULT '[]'::jsonb,
    
    -- 人工评分
    manual_score FLOAT,
    manual_comments TEXT,
    
    -- 决策
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending/approved/rejected/needs_revision
    action VARCHAR(20),  -- publish/revise/regenerate
    revision_instructions TEXT,
    
    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMP,
    
    -- 元数据
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- 约束
    CONSTRAINT quality_reviews_manual_score_range CHECK (manual_score IS NULL OR (manual_score >= 0 AND manual_score <= 100))
);

-- 索引
CREATE INDEX idx_quality_reviews_chapter_id ON quality_reviews(chapter_id);
CREATE INDEX idx_quality_reviews_novel_id ON quality_reviews(novel_id);
CREATE INDEX idx_quality_reviews_reviewer_id ON quality_reviews(reviewer_id);
CREATE INDEX idx_quality_reviews_status ON quality_reviews(status);
CREATE INDEX idx_quality_reviews_created_at ON quality_reviews(created_at DESC);
CREATE INDEX idx_quality_reviews_auto_metrics ON quality_reviews USING GIN (auto_metrics);

-- 注释
COMMENT ON TABLE quality_reviews IS '质量审核记录表';
```

---

## 🔗 视图定义

### 1. novel_statistics（小说统计视图）

```sql
CREATE OR REPLACE VIEW novel_statistics AS
SELECT 
    n.id AS novel_id,
    n.title,
    n.genre_id,
    n.status,
    n.user_id,
    
    -- 章节统计
    COUNT(c.id) AS total_chapters,
    SUM(c.word_count) AS total_words,
    COUNT(c.id) FILTER (WHERE c.status = 'published') AS published_chapters,
    
    -- 质量统计
    AVG(c.quality_score) AS avg_quality_score,
    COUNT(c.id) FILTER (WHERE c.human_reviewed = TRUE) AS reviewed_chapters,
    
    -- 角色统计
    (SELECT COUNT(*) FROM characters WHERE novel_id = n.id) AS character_count,
    
    -- 时间
    n.created_at,
    n.updated_at,
    MAX(c.created_at) AS latest_chapter_at
    
FROM novels n
LEFT JOIN chapters c ON c.novel_id = n.id
GROUP BY n.id;

-- 注释
COMMENT ON VIEW novel_statistics IS '小说统计视图';
```

### 2. chapter_with_context（章节完整上下文视图）

```sql
CREATE OR REPLACE VIEW chapter_with_context AS
SELECT 
    c.*,
    
    -- 小说信息
    n.title AS novel_title,
    n.genre_id,
    n.user_id,
    
    -- 大纲信息
    co.summary AS outline_summary,
    co.key_events,
    co.target_words AS target_words_outline,
    
    -- 故事弧信息
    a.title AS arc_title,
    a.arc_number,
    
    -- 上一章信息（用于生成上下文）
    LAG(c.id) OVER (PARTITION BY c.novel_id ORDER BY c.chapter_number) AS previous_chapter_id,
    LAG(c.content, 1, '') OVER (PARTITION BY c.novel_id ORDER BY c.chapter_number) AS previous_content
    
FROM chapters c
JOIN novels n ON n.id = c.novel_id
LEFT JOIN chapter_outlines co ON co.id = c.outline_id
LEFT JOIN arcs a ON a.id = c.arc_id;

-- 注释
COMMENT ON VIEW chapter_with_context IS '章节完整上下文视图（用于生成和展示）';
```

---

## 📈 索引策略总结

### 主键索引（自动创建）
- 所有表的 `id` 字段（UUID）

### 外键索引（必需）
- 所有外键字段都创建索引
- 例如：`novel_id`, `user_id`, `character_id` 等

### 查询优化索引
- **时间戳索引**：`created_at DESC`（用于排序）
- **状态索引**：`status`（用于筛选）
- **组合索引**：`(novel_id, chapter_number)`（用于精确查找）

### JSONB索引（GIN）
- `genre_attributes`：Genre专属属性查询
- `metadata`：元数据查询
- `validation_results`：质量指标查询

### 全文搜索索引
- `chapters.content`：章节内容全文搜索
- `chapters.title`：章节标题搜索

---

## 🔄 数据迁移策略

### 使用Alembic进行版本管理

```python
# alembic/versions/001_initial_schema.py
"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2026-09-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # 创建users表
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('username', sa.String(50), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        # ... 其他字段
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )
    
    # 创建索引
    op.create_index('idx_users_email', 'users', ['email'])
    # ... 其他表和索引

def downgrade():
    op.drop_table('users')
    # ... 其他回滚操作
```

### 迁移命令

```bash
# 创建新迁移
alembic revision --autogenerate -m "描述"

# 升级到最新版本
alembic upgrade head

# 回滚
alembic downgrade -1

# 查看当前版本
alembic current

# 查看历史
alembic history
```

---

## 🎯 性能优化建议

### 1. 分区策略

**llm_call_logs表按月分区**（日志数据量大）

```sql
-- 创建分区表
CREATE TABLE llm_call_logs (
    -- 字段定义...
) PARTITION BY RANGE (created_at);

-- 创建分区
CREATE TABLE llm_call_logs_2026_09 PARTITION OF llm_call_logs
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');

CREATE TABLE llm_call_logs_2026_10 PARTITION OF llm_call_logs
    FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');

-- 自动创建未来分区的函数
CREATE OR REPLACE FUNCTION create_llm_logs_partition()
RETURNS void AS $$
DECLARE
    start_date date;
    end_date date;
    partition_name text;
BEGIN
    -- 为下个月创建分区
    start_date := date_trunc('month', CURRENT_DATE + interval '1 month');
    end_date := start_date + interval '1 month';
    partition_name := 'llm_call_logs_' || to_char(start_date, 'YYYY_MM');
    
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF llm_call_logs FOR VALUES FROM (%L) TO (%L)',
        partition_name, start_date, end_date
    );
END;
$$ LANGUAGE plpgsql;
```

### 2. 查询优化

**常用查询示例**

```sql
-- 1. 获取用户的所有小说（带统计）
SELECT 
    n.*,
    ns.total_chapters,
    ns.total_words,
    ns.avg_quality_score
FROM novels n
LEFT JOIN novel_statistics ns ON ns.novel_id = n.id
WHERE n.user_id = $1
ORDER BY n.updated_at DESC;

-- 使用索引：idx_novels_user_id, idx_novels_updated_at

-- 2. 获取小说的章节列表（分页）
SELECT 
    id, chapter_number, title, word_count, status, quality_score, created_at
FROM chapters
WHERE novel_id = $1
ORDER BY chapter_number
LIMIT $2 OFFSET $3;

-- 使用索引：idx_chapters_novel_id, idx_chapters_chapter_number

-- 3. 全文搜索章节
SELECT 
    id, chapter_number, title, 
    ts_headline('chinese', content, query) AS snippet
FROM chapters, plainto_tsquery('chinese', $1) AS query
WHERE novel_id = $2 AND to_tsvector('chinese', content) @@ query
ORDER BY ts_rank(to_tsvector('chinese', content), query) DESC
LIMIT 20;

-- 使用索引：idx_chapters_content_fts
```

### 3. 缓存策略

**Redis缓存层**

```python
# 缓存键设计
CACHE_KEYS = {
    "novel": "novel:{novel_id}",
    "novel_stats": "novel:stats:{novel_id}",
    "chapter": "chapter:{chapter_id}",
    "character": "character:{character_id}",
    "user_novels": "user:{user_id}:novels",
}

# TTL配置
CACHE_TTL = {
    "novel": 3600,  # 1小时
    "chapter": 1800,  # 30分钟
    "character": 3600,
    "user_novels": 600,  # 10分钟
}
```

---

## 🔒 数据完整性

### 外键约束

```sql
-- 级联删除
-- 删除用户时，自动删除其所有小说
ALTER TABLE novels ADD CONSTRAINT fk_novels_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- 删除小说时，自动删除所有章节
ALTER TABLE chapters ADD CONSTRAINT fk_chapters_novel
    FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE;

-- 保护性约束
-- 删除角色前必须先删除关联关系
ALTER TABLE relationships ADD CONSTRAINT fk_relationships_character_a
    FOREIGN KEY (character_a_id) REFERENCES characters(id) ON DELETE RESTRICT;
```

### 触发器

```sql
-- 自动更新updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_novels_updated_at
    BEFORE UPDATE ON novels
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- 自动更新小说统计
CREATE OR REPLACE FUNCTION update_novel_statistics()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE novels SET
        total_chapters = (SELECT COUNT(*) FROM chapters WHERE novel_id = NEW.novel_id),
        total_words = (SELECT COALESCE(SUM(word_count), 0) FROM chapters WHERE novel_id = NEW.novel_id)
    WHERE id = NEW.novel_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_novel_stats_on_chapter_insert
    AFTER INSERT ON chapters
    FOR EACH ROW
    EXECUTE FUNCTION update_novel_statistics();
```

---

## 🎯 初始化脚本

```sql
-- init.sql

-- 创建数据库
CREATE DATABASE anovel_v2;

-- 连接到数据库
\c anovel_v2;

-- 启用扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 用于模糊搜索

-- 创建所有表（按依赖顺序）
-- 1. users
-- 2. novels
-- 3. characters
-- ... 依次执行上面的CREATE TABLE语句

-- 创建视图
-- CREATE VIEW novel_statistics ...

-- 创建触发器
-- CREATE TRIGGER ...

-- 插入初始数据
INSERT INTO users (username, email, password_hash, role) VALUES
    ('admin', 'admin@anovel.com', '$2b$12$...', 'admin');

-- 完成
SELECT 'Database initialized successfully!' AS message;
```

---

**数据库Schema设计文档完成！** ✅

下一步：**19_API_SPECIFICATION.md**（API规格说明）
