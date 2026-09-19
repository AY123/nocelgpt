#!/bin/bash
# 使用 CC_VIBE Anthropic 中继生产 61-70 章

set -e

echo "=========================================="
echo "61-70 章生产 (CC_VIBE Anthropic)"
echo "=========================================="

# 加载 CC_VIBE 配置
export ANTHROPIC_AUTH_TOKEN=$(grep CC_VIBE_ANTHROPIC_AUTH_TOKEN .env | cut -d= -f2)
export ANTHROPIC_BASE_URL=$(grep CC_VIBE_ANTHROPIC_BASE_URL .env | cut -d= -f2)

echo "配置检查:"
echo "  Base URL: $ANTHROPIC_BASE_URL"
echo "  Token: ${ANTHROPIC_AUTH_TOKEN:0:20}..."
echo ""

cd AI-Novel-Runtime

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
  --genre-contract

echo ""
echo "=========================================="
echo "✅ 61-70 章生产完成"
echo "=========================================="

