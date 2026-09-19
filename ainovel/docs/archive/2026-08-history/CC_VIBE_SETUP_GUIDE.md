# CC_VIBE Anthropic 中继配置指南

## 当前配置状态

### ✅ 已配置的中继
1. **FLOW_CODEYU** (已配置)
   - Base URL: https://codeyu.shop
   - Model: claude-opus-5
   - Token: 已设置

2. **直连 Anthropic** (已配置)
   - Token: 已设置

### ⚠️ 待配置的中继
3. **CC_VIBE** (未配置)
   - 需要添加配置

---

## 配置步骤

### 1. 编辑 .env 文件

在 `.env` 文件末尾添加以下配置：

```bash
# CC_VIBE Anthropic 中继
CC_VIBE_ANTHROPIC_BASE_URL=https://your-cc-vibe-url.com
CC_VIBE_ANTHROPIC_AUTH_TOKEN=sk-your-cc-vibe-token-here
CC_VIBE_ANTHROPIC_MODEL=claude-opus-5
```

**注意**：
- 将 `https://your-cc-vibe-url.com` 替换为实际的 CC_VIBE 中继 URL
- 将 `sk-your-cc-vibe-token-here` 替换为实际的 API Token
- 根据需要修改模型名称

### 2. 测试连接

```bash
python3 test_cc_vibe_connection.py
```

---

## 在代码中使用

### 方法1: 通过 LLM Factory

```python
from llm.factory import build_llm_model

# 使用 CC_VIBE 中继
model = build_llm_model(
    provider='anthropic',
    model_id=os.environ.get('CC_VIBE_ANTHROPIC_MODEL', 'claude-opus-5'),
    auth_token=os.environ.get('CC_VIBE_ANTHROPIC_AUTH_TOKEN'),
    base_url=os.environ.get('CC_VIBE_ANTHROPIC_BASE_URL')
)
```

### 方法2: 直接使用 ClaudeAdapter

```python
from llm.adapters.claude import ClaudeAdapter

adapter = ClaudeAdapter(
    auth_token=os.environ.get('CC_VIBE_ANTHROPIC_AUTH_TOKEN'),
    base_url=os.environ.get('CC_VIBE_ANTHROPIC_BASE_URL'),
    model=os.environ.get('CC_VIBE_ANTHROPIC_MODEL', 'claude-opus-5')
)
```

### 方法3: 在 CLI 中使用

```bash
# 通过环境变量前缀指定中继
ANTHROPIC_AUTH_TOKEN=$CC_VIBE_ANTHROPIC_AUTH_TOKEN \
ANTHROPIC_BASE_URL=$CC_VIBE_ANTHROPIC_BASE_URL \
python3 -m runtime.cli serial run \
  --project ../novel-lingse \
  --model-provider anthropic \
  --model-id claude-opus-5 \
  ...
```

---

## 多中继切换

### 场景1: 手动切换

```bash
# 使用 FLOW_CODEYU
export ANTHROPIC_AUTH_TOKEN=$FLOW_CODEYU_ANTHROPIC_AUTH_TOKEN
export ANTHROPIC_BASE_URL=$FLOW_CODEYU_ANTHROPIC_BASE_URL

# 使用 CC_VIBE
export ANTHROPIC_AUTH_TOKEN=$CC_VIBE_ANTHROPIC_AUTH_TOKEN
export ANTHROPIC_BASE_URL=$CC_VIBE_ANTHROPIC_BASE_URL
```

### 场景2: 在代码中动态选择

```python
import os

def get_anthropic_config(relay='default'):
    configs = {
        'default': {
            'token': os.environ.get('ANTHROPIC_AUTH_TOKEN'),
            'base_url': None,
        },
        'flow_codeyu': {
            'token': os.environ.get('FLOW_CODEYU_ANTHROPIC_AUTH_TOKEN'),
            'base_url': os.environ.get('FLOW_CODEYU_ANTHROPIC_BASE_URL'),
        },
        'cc_vibe': {
            'token': os.environ.get('CC_VIBE_ANTHROPIC_AUTH_TOKEN'),
            'base_url': os.environ.get('CC_VIBE_ANTHROPIC_BASE_URL'),
        },
    }
    return configs.get(relay, configs['default'])

# 使用
config = get_anthropic_config('cc_vibe')
adapter = ClaudeAdapter(
    auth_token=config['token'],
    base_url=config['base_url']
)
```

---

## 故障排查

### 问题1: 连接失败

**症状**: `Failed to connect to api.anthropic.com`

**解决**:
1. 检查 `CC_VIBE_ANTHROPIC_BASE_URL` 是否正确
2. 确认中继服务可访问
3. 检查网络连接

### 问题2: 认证失败

**症状**: `401 Unauthorized` 或 `invalid_api_key`

**解决**:
1. 检查 `CC_VIBE_ANTHROPIC_AUTH_TOKEN` 是否正确
2. 确认 token 未过期
3. 验证 token 格式（应以 `sk-` 开头）

### 问题3: 模型不可用

**症状**: `model not found` 或 `model_not_available`

**解决**:
1. 检查 `CC_VIBE_ANTHROPIC_MODEL` 配置
2. 确认中继支持该模型
3. 尝试使用默认模型 `claude-opus-5`

---

## 配置检查清单

- [ ] CC_VIBE_ANTHROPIC_BASE_URL 已设置
- [ ] CC_VIBE_ANTHROPIC_AUTH_TOKEN 已设置
- [ ] CC_VIBE_ANTHROPIC_MODEL 已设置（可选）
- [ ] 运行 `test_cc_vibe_connection.py` 测试通过
- [ ] 在实际代码中测试通过

---

**文档版本**: 1.0
**最后更新**: 2026-08-10
