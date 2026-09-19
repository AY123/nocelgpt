# 切换到 CC_VIBE Anthropic 中继 - 2026-08-10

## 配置变更

### 从 DeepSeek 切换到 CC_VIBE

**原因**: 使用 Anthropic Claude 模型进行后续正文生产

**配置**:
```bash
CC_VIBE_ANTHROPIC_BASE_URL=https://codeyu.shop
CC_VIBE_ANTHROPIC_AUTH_TOKEN=sk-5d8220318e641c9f78acbe4492cde781783a2e538da9859629ee2c15a87e6298
CC_VIBE_ANTHROPIC_MODEL=claude-opus-5
```

---

## 使用方法

### 61-70 章生产（使用 CC_VIBE）

```bash
cd /Users/angyang/Documents/xiaoshuo/AINovel/AI-Novel-Runtime

python3 -m runtime.cli serial run \
  --project ../novel-lingse \
  --standard-root ../AI-Novel-Standard \
  --start-chapter 61 \
  --max-chapters 10 \
  --rolling-plan-continuation \
  --model-provider anthropic \
  --model-id claude-opus-5 \
  --prompt-version v12 \
  --speech \
  --mandate \
  --long-arc \
  --genre-contract \
  --env-file ../.env
```

**关键参数变更**:
- `--model-provider anthropic` (原: `deepseek`)
- `--model-id claude-opus-5` (原: `deepseek-chat`)
- `--env-file ../.env` (确保加载 CC_VIBE 配置)

---

## CLI 如何读取配置

### 方法1: 环境变量前缀（推荐）

CLI 会按以下顺序查找配置：
1. `CC_VIBE_ANTHROPIC_*` 环境变量
2. `ANTHROPIC_*` 环境变量
3. 默认配置

**实现方式**:
```python
# 在运行前设置环境变量
export ANTHROPIC_AUTH_TOKEN=$CC_VIBE_ANTHROPIC_AUTH_TOKEN
export ANTHROPIC_BASE_URL=$CC_VIBE_ANTHROPIC_BASE_URL
```

### 方法2: 直接在命令中指定

```bash
ANTHROPIC_AUTH_TOKEN=$CC_VIBE_ANTHROPIC_AUTH_TOKEN \
ANTHROPIC_BASE_URL=$CC_VIBE_ANTHROPIC_BASE_URL \
python3 -m runtime.cli serial run ...
```

### 方法3: 修改 .env 设置默认值

在 `.env` 中添加映射：
```bash
# 设置 Anthropic 默认为 CC_VIBE
ANTHROPIC_AUTH_TOKEN=${CC_VIBE_ANTHROPIC_AUTH_TOKEN}
ANTHROPIC_BASE_URL=${CC_VIBE_ANTHROPIC_BASE_URL}
```

---

## 测试连接

```bash
cd /Users/angyang/Documents/xiaoshuo/AINovel

python3 << 'EOF'
import os
import anthropic

# 加载 .env
if os.path.exists('.env'):
    with open('.env') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

# 测试连接
client = anthropic.Anthropic(
    auth_token=os.environ['CC_VIBE_ANTHROPIC_AUTH_TOKEN'],
    base_url=os.environ['CC_VIBE_ANTHROPIC_BASE_URL']
)

response = client.messages.create(
    model='claude-opus-5',
    max_tokens=100,
    messages=[{"role": "user", "content": "测试连接，请回复OK"}]
)

print(f"✅ CC_VIBE 连接成功！")
print(f"回复: {response.content[0].text}")
EOF
```

---

## 成本对比

### DeepSeek
- 单章成本: ¥0.027 CNY
- 10 章成本: ¥0.27 CNY

### Claude Opus-5 (CC_VIBE)
- 预估单章成本: 待测试
- 预估 10 章成本: 待测试

**建议**: 先运行 1-2 章测试，确认成本和质量后再批量生产

---

## 迁移计划

### 阶段1: 测试验证（1-2章）
```bash
# 生产 61-62 章测试
--start-chapter 61 --max-chapters 2
```

**验证点**:
- ✅ 连接成功
- ✅ 生成质量
- ✅ 成本可接受
- ✅ 速度可接受

### 阶段2: 小批量（10章）
```bash
# 61-70 章
--start-chapter 61 --max-chapters 10
```

### 阶段3: 完整批次（40章）
```bash
# 61-100 章（分4批）
```

---

## 质量对比监控

### 监控指标
1. **生成质量**: 对比 51-60 章（DeepSeek）vs 61-70 章（Claude）
2. **评分变化**: 18 维度质量分数
3. **成本效率**: CNY/章
4. **生产速度**: 分钟/章

### 对比脚本
```bash
# 生产完成后运行
python3 compare_quality.py \
  --chapters-a 51-60 \
  --chapters-b 61-70 \
  --output quality_comparison.md
```

---

## 回退方案

如果 CC_VIBE 效果不佳，可以随时切换回 DeepSeek：

```bash
--model-provider deepseek \
--model-id deepseek-chat
```

---

**文档版本**: 1.0
**最后更新**: 2026-08-10 22:10
**状态**: ✅ 配置完成，准备生产 61-70 章
