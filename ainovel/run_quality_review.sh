#!/bin/bash
# 批量运行 61-100 章质量评审

set -e

echo "=========================================="
echo "启动 61-100 章质量评审（40 章）"
echo "=========================================="

cd /Users/angyang/Documents/xiaoshuo/AINovel/AI-Novel-Runtime

# 使用 DeepSeek 进行质量评审（成本低）
export MODEL_PROVIDER=deepseek
export MODEL_ID=deepseek-chat

for chapter in {61..100}; do
    echo ""
    echo "Processing Chapter $chapter..."

    # 构建 package 路径
    package="../novel-lingse/registry/derived/drafts/TASK-$(printf "%05d" $chapter).json"

    if [ -f "$package" ]; then
        python3 -m runtime.cli refine \
            --package "$package" \
            --standard-root ../AI-Novel-Standard \
            --project ../novel-lingse \
            --model-provider deepseek \
            --model-id deepseek-chat \
            --prompt-version v12 \
            --max-rounds 1 \
            --reviewer llm-quality 2>&1 | tee -a quality_review_log.txt

        echo "✅ Chapter $chapter completed"
    else
        echo "⚠️ Chapter $chapter not found: $package"
    fi
done

echo ""
echo "=========================================="
echo "✅ 质量评审完成"
echo "=========================================="
