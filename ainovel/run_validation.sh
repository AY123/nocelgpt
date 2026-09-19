#!/bin/bash
# P0+P1修复效果验证 - 生成新章节脚本

set -e

echo "🚀 P0+P1修复效果验证 - 生成新章节"
echo "========================================="
echo ""

# 检查目录
if [ ! -d "AI-Novel-Runtime" ]; then
    echo "❌ 错误: 未找到AI-Novel-Runtime目录"
    echo "请在项目根目录运行此脚本"
    exit 1
fi

if [ ! -d "novel-lingse" ]; then
    echo "❌ 错误: 未找到novel-lingse目录"
    exit 1
fi

cd AI-Novel-Runtime

echo "📚 准备生成新章节（TASK-00101到TASK-00103）"
echo "这将使用P0+P1修复后的代码生成3个新章节"
echo ""
echo "预计时间: 10-30分钟（取决于LLM速度）"
echo ""
read -p "按Enter继续，或Ctrl+C取消..."

echo ""
echo "🔧 生成命令:"
echo "python3 -m runtime.cli serial run \\"
echo "  --project ../novel-lingse \\"
echo "  --enable-final-quality-review \\"
echo "  --enable-final-reader-simulation \\"
echo "  --chapters 101-103"
echo ""

# 执行生成
python3 -m runtime.cli serial run \
  --project ../novel-lingse \
  --enable-final-quality-review \
  --enable-final-reader-simulation \
  --chapters 101-103

echo ""
echo "✅ 章节生成完成！"
echo ""
echo "📊 现在运行验证脚本..."
cd ..

python3 validate_p0_p1.py

echo ""
echo "========================================="
echo "🎉 验证完成！"
echo ""
echo "查看详细数据:"
echo "  cat novel-lingse/registry/derived/chapter-run/run-TASK-00101.json | python3 -m json.tool | less"
echo ""
echo "查看Production Card:"
echo "  cat novel-lingse/registry/derived/chapter-run/run-TASK-00101.json | python3 -c \"import json, sys; print(json.dumps(json.load(sys.stdin).get('production_card', {}), indent=2))\" | less"
