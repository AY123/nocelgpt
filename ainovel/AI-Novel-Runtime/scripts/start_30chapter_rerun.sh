#!/bin/bash
# 30章重跑验证 - 启动脚本 (Phase 1)

set -e

cd /Users/angyang/Documents/xiaoshuo/AINovel/AI-Novel-Runtime

echo "========================================="
echo "Phase 1: 30章重跑验证"
echo "========================================="
echo ""
echo "⚠️  重要提示："
echo "   - 这将生成30章内容"
echo "   - 预计耗时: 2-3天"
echo "   - 预计成本: ¥3-5"
echo "   - 使用.env中配置的模型"
echo ""
echo "Phase 1功能（全部启用）："
echo "   ✅ 文本完整性检查（跨章/标点/换行）"
echo "   ✅ AI味修复（span定位+量化指令+模板检测）"
echo "   ✅ 篇幅控制（多轮收紧+硬截断）"
echo ""

read -p "确认启动 30章重跑? (输入 yes 继续): " confirm

if [ "$confirm" != "yes" ]; then
    echo ""
    echo "❌ 已取消"
    exit 0
fi

echo ""
echo "🚀 启动30章生成..."
echo ""
echo "命令: runtime serial run --project novel-lingse --max-chapters 30 ..."
echo ""

# 正确的命令格式
python3 -m runtime.cli serial run \
  --project /Users/angyang/Documents/xiaoshuo/AINovel/novel-lingse \
  --standard-root /Users/angyang/Documents/xiaoshuo/AINovel/AI-Novel-Runtime \
  --max-chapters 30 \
  --hygiene \
  --hygiene-rounds 2 \
  --budget-limit 5.0 \
  --model-provider deepseek \
  --model-id deepseek-chat

echo ""
echo "========================================="
echo "✅ 30章重跑完成！"
echo "========================================="
echo ""
echo "下一步："
echo "1. 查看质量报告"
echo "2. 分析Phase 1修复效果"
echo "3. 准备真人评审"
