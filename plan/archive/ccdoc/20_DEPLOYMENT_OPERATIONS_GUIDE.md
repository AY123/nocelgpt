# ANovel V2 部署运维指南

**版本**: v1.0  
**制定日期**: 2026-09-18  
**状态**: Draft  
**用途**: 定义完整的部署和运维方案  

---

## 📋 文档目的

本文档定义ANovel V2的部署和运维方案，包括：
1. **环境配置** - 开发/测试/生产环境
2. **CI/CD流程** - 自动化部署
3. **容器化部署** - Docker/Docker Compose
4. **监控告警** - 日志、指标、告警
5. **备份恢复** - 数据安全
6. **故障处理** - 常见问题排查

目标：
- 一键部署
- 自动化运维
- 快速恢复
- 可观测性

---

## 🌍 环境规划

### 环境划分

| 环境 | 用途 | 配置 | 域名示例 |
|------|------|------|---------|
| **Development** | 本地开发 | Docker Compose | localhost:8000 |
| **Staging** | 测试环境 | 单机VPS | staging.anovel.com |
| **Production** | 生产环境 | 云服务器集群 | api.anovel.com |

### 硬件需求

#### 开发环境（本地）

```
CPU: 4核
内存: 8GB
磁盘: 50GB SSD
系统: macOS/Linux/Windows + Docker
```

#### 生产环境（MVP阶段）

```
服务器配置（单机）:
CPU: 8核
内存: 16GB
磁盘: 100GB SSD
带宽: 10Mbps
系统: Ubuntu 22.04 LTS

推荐云服务商:
- AWS: t3.xlarge
- 阿里云: ecs.c6.2xlarge
- 腾讯云: S5.2XLARGE16
```

#### 生产环境（扩展阶段）

```
API服务器 x3:
- CPU: 4核
- 内存: 8GB
- 作用: 处理HTTP请求

Worker服务器 x3:
- CPU: 8核
- 内存: 16GB
- 作用: LLM调用、章节生成

数据库服务器 x2:
- CPU: 8核
- 内存: 32GB
- 磁盘: 500GB SSD
- 作用: PostgreSQL主从

Redis服务器 x2:
- CPU: 2核
- 内存: 8GB
- 作用: 缓存、队列

负载均衡器 x1:
- CPU: 2核
- 内存: 4GB
```

---

## 🐳 Docker部署方案

### 1. Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim as base

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建非root用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1

# 启动命令（由docker-compose覆盖）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Docker Compose（开发环境）

```yaml
# docker-compose.yml
version: '3.8'

services:
  # API服务
  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://anovel:password@postgres:5432/anovel
      - REDIS_URL=redis://redis:6379/0
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - ENVIRONMENT=development
      - LOG_LEVEL=DEBUG
    volumes:
      - ./:/app
      - ./logs:/app/logs
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    restart: unless-stopped
    networks:
      - anovel-network

  # Celery Worker
  worker:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://anovel:password@postgres:5432/anovel
      - REDIS_URL=redis://redis:6379/0
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - ENVIRONMENT=development
    volumes:
      - ./:/app
      - ./logs:/app/logs
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: celery -A infrastructure.tasks.celery_app worker --loglevel=info --concurrency=2
    restart: unless-stopped
    networks:
      - anovel-network

  # Celery Beat（定时任务）
  beat:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://anovel:password@postgres:5432/anovel
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./:/app
    depends_on:
      - redis
    command: celery -A infrastructure.tasks.celery_app beat --loglevel=info
    restart: unless-stopped
    networks:
      - anovel-network

  # PostgreSQL数据库
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=anovel
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=anovel
      - PGDATA=/var/lib/postgresql/data/pgdata
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U anovel"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - anovel-network

  # Redis缓存
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    restart: unless-stopped
    networks:
      - anovel-network

  # Flower（Celery监控）
  flower:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - REDIS_URL=redis://redis:6379/0
    ports:
      - "5555:5555"
    depends_on:
      - redis
    command: celery -A infrastructure.tasks.celery_app flower --port=5555
    restart: unless-stopped
    networks:
      - anovel-network

volumes:
  postgres_data:
  redis_data:

networks:
  anovel-network:
    driver: bridge
```

### 3. Docker Compose（生产环境）

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  # Nginx反向代理
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - api
    restart: always
    networks:
      - anovel-network

  # API服务（多实例）
  api:
    image: anovel-api:latest
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
    environment:
      - DATABASE_URL=postgresql://anovel:${DB_PASSWORD}@postgres:5432/anovel
      - REDIS_URL=redis://redis:6379/0
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
    volumes:
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
    command: gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
    restart: always
    networks:
      - anovel-network

  # Worker服务（多实例）
  worker:
    image: anovel-api:latest
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '4'
          memory: 8G
    environment:
      - DATABASE_URL=postgresql://anovel:${DB_PASSWORD}@postgres:5432/anovel
      - REDIS_URL=redis://redis:6379/0
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - ENVIRONMENT=production
    volumes:
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
    command: celery -A infrastructure.tasks.celery_app worker --loglevel=info --concurrency=4
    restart: always
    networks:
      - anovel-network

  # PostgreSQL
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=anovel
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=anovel
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: always
    networks:
      - anovel-network

  # Redis
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: always
    networks:
      - anovel-network

volumes:
  postgres_data:
  redis_data:

networks:
  anovel-network:
    driver: bridge
```

### 4. Nginx配置

```nginx
# nginx.conf
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript 
               application/json application/javascript application/xml+rss;

    # 上游API服务器
    upstream api_backend {
        least_conn;
        server api:8000 max_fails=3 fail_timeout=30s;
    }

    # HTTP重定向到HTTPS
    server {
        listen 80;
        server_name api.anovel.com;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS服务器
    server {
        listen 443 ssl http2;
        server_name api.anovel.com;

        # SSL证书
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # 安全头
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;

        # 客户端最大请求体（支持大文件上传）
        client_max_body_size 10M;

        # API代理
        location /api/ {
            proxy_pass http://api_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # 超时设置（LLM调用可能耗时）
            proxy_connect_timeout 60s;
            proxy_send_timeout 300s;
            proxy_read_timeout 300s;
        }

        # WebSocket支持（未来）
        location /ws/ {
            proxy_pass http://api_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
        }

        # 健康检查
        location /health {
            proxy_pass http://api_backend/api/v1/health;
            access_log off;
        }

        # 静态文件（如果有）
        location /static/ {
            alias /var/www/static/;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

---

## 🚀 CI/CD流程

### GitHub Actions工作流

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches:
      - main
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: anovel-api

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run tests
        run: |
          pytest tests/ --cov=. --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v3
      
      - name: Log in to Container Registry
        uses: docker/login-action@v2
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: ${{ env.REGISTRY }}/${{ github.repository }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha
            type=raw,value=latest
      
      - name: Build and push Docker image
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.PROD_HOST }}
          username: ${{ secrets.PROD_USER }}
          key: ${{ secrets.PROD_SSH_KEY }}
          script: |
            cd /opt/anovel
            docker-compose -f docker-compose.prod.yml pull
            docker-compose -f docker-compose.prod.yml up -d --no-deps --build api worker
            docker-compose -f docker-compose.prod.yml exec -T api alembic upgrade head
            
      - name: Health check
        run: |
          sleep 10
          curl -f https://api.anovel.com/api/v1/health || exit 1
      
      - name: Notify deployment
        if: always()
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'Deployment to production ${{ job.status }}'
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

### 部署脚本

```bash
#!/bin/bash
# deploy.sh - 手动部署脚本

set -e

echo "🚀 Starting deployment..."

# 1. 拉取最新代码
echo "📥 Pulling latest code..."
git pull origin main

# 2. 构建Docker镜像
echo "🏗️  Building Docker image..."
docker build -t anovel-api:latest .

# 3. 停止旧容器
echo "🛑 Stopping old containers..."
docker-compose -f docker-compose.prod.yml down

# 4. 启动新容器
echo "✨ Starting new containers..."
docker-compose -f docker-compose.prod.yml up -d

# 5. 运行数据库迁移
echo "🗄️  Running database migrations..."
docker-compose -f docker-compose.prod.yml exec -T api alembic upgrade head

# 6. 健康检查
echo "🏥 Health check..."
sleep 10
curl -f http://localhost:8000/api/v1/health || exit 1

echo "✅ Deployment completed successfully!"
```

---

## 📊 监控与日志

### 1. 日志管理

#### 日志配置

```python
# shared/logging_config.py
import logging
from loguru import logger
import sys

def setup_logging(environment: str = "development"):
    """配置日志"""
    
    # 移除默认handler
    logger.remove()
    
    # 控制台输出
    logger.add(
        sys.stdout,
        level="DEBUG" if environment == "development" else "INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # 文件输出
    logger.add(
        "logs/anovel_{time:YYYY-MM-DD}.log",
        rotation="00:00",  # 每天午夜轮转
        retention="30 days",  # 保留30天
        compression="zip",  # 压缩旧日志
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    
    # 错误日志单独文件
    logger.add(
        "logs/error_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="90 days",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}\n{exception}"
    )
    
    # LLM调用日志
    logger.add(
        "logs/llm_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        filter=lambda record: "llm" in record["extra"],
        format="{time:YYYY-MM-DD HH:mm:ss} | {extra[llm_model]} | {extra[tokens]} tokens | ${extra[cost]} | {message}"
    )
    
    return logger
```

#### 日志使用示例

```python
from shared.logging_config import setup_logging

logger = setup_logging()

# 普通日志
logger.info("Starting chapter generation", chapter_id="ch_123")
logger.error("LLM call failed", error=str(e), chapter_id="ch_123")

# LLM专用日志
logger.bind(
    llm=True,
    llm_model="claude-sonnet-4",
    tokens=4500,
    cost=0.84
).info("Chapter generated successfully")
```

### 2. 应用指标

#### Prometheus指标

```python
# infrastructure/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# 请求计数
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# 请求延迟
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

# LLM调用
llm_calls_total = Counter(
    'llm_calls_total',
    'Total LLM API calls',
    ['model', 'success']
)

llm_call_duration_seconds = Histogram(
    'llm_call_duration_seconds',
    'LLM call latency',
    ['model']
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total tokens used',
    ['model', 'type']  # type: input/output
)

llm_cost_usd_total = Counter(
    'llm_cost_usd_total',
    'Total LLM cost in USD',
    ['model']
)

# 章节生成
chapters_generated_total = Counter(
    'chapters_generated_total',
    'Total chapters generated',
    ['genre', 'status']  # status: success/failed
)

chapters_quality_score = Histogram(
    'chapters_quality_score',
    'Chapter quality scores',
    ['genre']
)

# 系统资源
active_workers = Gauge(
    'active_workers',
    'Number of active Celery workers'
)

queue_length = Gauge(
    'queue_length',
    'Number of tasks in queue',
    ['queue_name']
)
```

#### 指标收集示例

```python
# 在API中间件
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    
    # 记录指标
    http_requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    http_request_duration_seconds.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response

# 在LLM客户端
async def generate_with_metrics(prompt: str, model: str):
    start_time = time.time()
    
    try:
        result = await llm.generate(prompt, model=model)
        
        # 成功指标
        llm_calls_total.labels(model=model, success="true").inc()
        
        # Token统计
        input_tokens = count_tokens(prompt)
        output_tokens = count_tokens(result)
        llm_tokens_total.labels(model=model, type="input").inc(input_tokens)
        llm_tokens_total.labels(model=model, type="output").inc(output_tokens)
        
        # 成本
        cost = calculate_cost(model, input_tokens, output_tokens)
        llm_cost_usd_total.labels(model=model).inc(cost)
        
        return result
    
    except Exception as e:
        llm_calls_total.labels(model=model, success="false").inc()
        raise
    
    finally:
        duration = time.time() - start_time
        llm_call_duration_seconds.labels(model=model).observe(duration)
```

### 3. 健康检查端点

```python
# api/routes/health.py
from fastapi import APIRouter, status
from pydantic import BaseModel
import asyncpg
import redis.asyncio as redis

router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    version: str
    components: dict

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    components = {}
    overall_status = "healthy"
    
    # 检查数据库
    try:
        conn = await asyncpg.connect(settings.DATABASE_URL)
        await conn.fetchval("SELECT 1")
        await conn.close()
        components["database"] = "healthy"
    except Exception as e:
        components["database"] = f"unhealthy: {str(e)}"
        overall_status = "unhealthy"
    
    # 检查Redis
    try:
        r = await redis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.close()
        components["redis"] = "healthy"
    except Exception as e:
        components["redis"] = f"unhealthy: {str(e)}"
        overall_status = "unhealthy"
    
    # 检查Celery Workers
    try:
        from infrastructure.tasks.celery_app import celery_app
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        
        if active_workers:
            components["workers"] = f"healthy ({len(active_workers)} workers)"
        else:
            components["workers"] = "no workers"
            overall_status = "degraded"
    except Exception as e:
        components["workers"] = f"unhealthy: {str(e)}"
        overall_status = "unhealthy"
    
    return {
        "status": overall_status,
        "version": settings.VERSION,
        "components": components
    }

@router.get("/ready")
async def readiness_check():
    """就绪检查（Kubernetes用）"""
    # 简单检查，确保应用可以接受流量
    return {"ready": True}

@router.get("/live")
async def liveness_check():
    """存活检查（Kubernetes用）"""
    # 最简单的检查，只要进程活着就返回200
    return {"alive": True}
```

---

## 💾 备份与恢复

### 1. 数据库备份

#### 自动备份脚本

```bash
#!/bin/bash
# backup.sh - PostgreSQL自动备份

set -e

# 配置
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="anovel"
DB_USER="anovel"
BACKUP_DIR="/backups"
RETENTION_DAYS=30

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份文件名（包含时间戳）
BACKUP_FILE="$BACKUP_DIR/anovel_$(date +%Y%m%d_%H%M%S).sql.gz"

# 执行备份
echo "Starting backup to $BACKUP_FILE..."
PGPASSWORD=$DB_PASSWORD pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER $DB_NAME | gzip > $BACKUP_FILE

# 验证备份
if [ -f "$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "Backup completed successfully. Size: $SIZE"
else
    echo "Backup failed!"
    exit 1
fi

# 删除旧备份
echo "Cleaning up old backups..."
find $BACKUP_DIR -name "anovel_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup process completed!"
```

#### Cron定时任务

```bash
# 添加到crontab
# 每天凌晨2点备份
0 2 * * * /opt/anovel/scripts/backup.sh >> /var/log/anovel-backup.log 2>&1
```

#### Docker Compose备份

```yaml
# docker-compose中添加备份服务
  backup:
    image: postgres:15-alpine
    environment:
      - PGHOST=postgres
      - PGUSER=anovel
      - PGPASSWORD=${DB_PASSWORD}
      - PGDATABASE=anovel
    volumes:
      - ./backups:/backups
      - ./scripts/backup.sh:/backup.sh
    entrypoint: /bin/sh
    command: -c "while true; do /backup.sh; sleep 86400; done"
    depends_on:
      - postgres
    networks:
      - anovel-network
```

### 2. 数据恢复

```bash
#!/bin/bash
# restore.sh - 数据库恢复

set -e

if [ -z "$1" ]; then
    echo "Usage: ./restore.sh <backup_file>"
    exit 1
fi

BACKUP_FILE=$1

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "⚠️  WARNING: This will overwrite the current database!"
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

# 停止应用
echo "Stopping application..."
docker-compose down api worker

# 恢复数据库
echo "Restoring database from $BACKUP_FILE..."
gunzip < $BACKUP_FILE | PGPASSWORD=$DB_PASSWORD psql -h localhost -U anovel anovel

# 启动应用
echo "Starting application..."
docker-compose up -d

echo "✅ Restore completed successfully!"
```

---

## 🔧 常见问题排查

### 1. 应用无法启动

**症状**: 容器启动后立即退出

**排查步骤**:
```bash
# 查看容器日志
docker-compose logs api

# 检查容器状态
docker-compose ps

# 进入容器调试
docker-compose exec api /bin/bash

# 检查配置
docker-compose config
```

**常见原因**:
- 环境变量缺失
- 数据库连接失败
- 端口冲突
- 权限问题

### 2. LLM调用失败

**症状**: 章节生成失败，日志显示LLM错误

**排查步骤**:
```bash
# 查看Worker日志
docker-compose logs worker

# 检查API Key
docker-compose exec api env | grep ANTHROPIC

# 手动测试API
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-sonnet-4-20250514","max_tokens":100,"messages":[{"role":"user","content":"test"}]}'
```

**常见原因**:
- API Key无效或过期
- 账户余额不足
- 速率限制
- 网络问题

### 3. 数据库连接池耗尽

**症状**: 503错误，日志显示"too many connections"

**排查步骤**:
```sql
-- 查看当前连接数
SELECT count(*) FROM pg_stat_activity;

-- 查看最大连接数
SHOW max_connections;

-- 查看活跃查询
SELECT pid, usename, application_name, state, query 
FROM pg_stat_activity 
WHERE state != 'idle';

-- 终止空闲连接
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'idle' AND state_change < NOW() - INTERVAL '10 minutes';
```

**解决方案**:
- 增加数据库max_connections
- 优化连接池配置
- 检查连接泄漏

### 4. Redis内存不足

**症状**: 缓存失效，Redis报OOM错误

**排查步骤**:
```bash
# 连接Redis
docker-compose exec redis redis-cli

# 查看内存使用
INFO memory

# 查看键数量
DBSIZE

# 查看大键
redis-cli --bigkeys

# 手动清理（谨慎）
FLUSHDB
```

**解决方案**:
- 增加Redis内存限制
- 设置合理的TTL
- 启用LRU淘汰策略

---

## 📱 运维命令速查

### Docker常用命令

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 查看日志
docker-compose logs -f api

# 重启服务
docker-compose restart api

# 进入容器
docker-compose exec api /bin/bash

# 查看资源使用
docker stats

# 清理未使用的资源
docker system prune -a
```

### 数据库操作

```bash
# 连接数据库
docker-compose exec postgres psql -U anovel anovel

# 运行迁移
docker-compose exec api alembic upgrade head

# 回滚迁移
docker-compose exec api alembic downgrade -1

# 查看迁移历史
docker-compose exec api alembic history

# 数据库备份
docker-compose exec postgres pg_dump -U anovel anovel > backup.sql
```

### Celery操作

```bash
# 查看Worker状态
docker-compose exec worker celery -A infrastructure.tasks.celery_app inspect active

# 查看队列长度
docker-compose exec worker celery -A infrastructure.tasks.celery_app inspect stats

# 清空队列
docker-compose exec worker celery -A infrastructure.tasks.celery_app purge

# 重启Worker
docker-compose restart worker
```

---

**部署运维指南文档完成！** ✅

下一步：**21_TESTING_STRATEGY.md**（测试策略）
