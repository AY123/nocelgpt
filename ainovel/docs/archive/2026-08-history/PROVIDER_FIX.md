# 修正：Provider 应该是 `claude` 而不是 `anthropic`

## 问题
```
RuntimeError: unsupported LLM provider 'anthropic'
```

## 原因
LLM Factory 支持的 provider 名称是 **`claude`**，不是 `anthropic`

## 支持的 Provider 列表
- `mock`
- `deepseek`
- `openai`
- `kimi`
- `92code`
- **`claude`** ✅ (正确)
- `gemini`
- `local`

## 正确命令

```bash
--model-provider claude  # 正确
--model-provider anthropic  # 错误
```

## 更新后的启动脚本

```bash
#!/bin/bash
export ANTHROPIC_AUTH_TOKEN=$CC_VIBE_ANTHROPIC_AUTH_TOKEN
export ANTHROPIC_BASE_URL=$CC_VIBE_ANTHROPIC_BASE_URL

python3 -m runtime.cli serial run \
  --project ../novel-lingse \
  --standard-root ../AI-Novel-Standard \
  --start-chapter 61 \
  --max-chapters 10 \
  --rolling-plan-continuation \
  --model-provider claude \
  --model-id claude-opus-5 \
  ...
```

---

**状态**: ✅ 已修正，重新启动中
