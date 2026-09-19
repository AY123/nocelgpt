#!/bin/bash
# Phase 1: 准备30章重跑环境

set -e

PROJECT_ROOT="/Users/angyang/Documents/xiaoshuo/AINovel"
RUNTIME_DIR="$PROJECT_ROOT/AI-Novel-Runtime"
NOVEL_DIR="$PROJECT_ROOT/novel-lingse"

echo "========================================="
echo "Phase 1: 30章重跑环境准备"
echo "========================================="

# 1. 检查.env文件
echo ""
echo "[1/7] 检查.env配置..."
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "❌ 错误: .env文件不存在"
    exit 1
fi
echo "   ✅ .env文件存在"

# 2. 检查Python依赖
echo ""
echo "[2/7] 检查Python依赖..."
cd "$RUNTIME_DIR"
python3 -c "import yaml" 2>/dev/null || echo "   ⚠️  警告: pyyaml未安装"
echo "   ✅ 基础依赖检查完成"

# 3. 运行Phase 1测试
echo ""
echo "[3/7] 运行Phase 1测试..."
python3 -m pytest tests/test_text_integrity*.py tests/test_length*.py tests/test_template*.py -q || {
    echo "   ❌ 错误: Phase 1测试未全部通过"
    exit 1
}
echo "   ✅ Phase 1测试通过"

# 4. 检查novel-lingse项目结构
echo ""
echo "[4/7] 检查novel-lingse项目..."
if [ ! -d "$NOVEL_DIR/registry" ]; then
    echo "   ❌ 错误: novel-lingse/registry不存在"
    exit 1
fi
echo "   ✅ 项目结构正常"

# 5. 备份现有30章（如果存在）
echo ""
echo "[5/7] 备份现有章节..."
BACKUP_DIR="$NOVEL_DIR/backup-$(date +%Y%m%d-%H%M%S)"
if [ -d "$NOVEL_DIR/registry/chapters" ]; then
    echo "   创建备份: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
    cp -r "$NOVEL_DIR/registry/chapters" "$BACKUP_DIR/" 2>/dev/null || true
    echo "   ✅ 备份完成"
else
    echo "   ℹ️  无现有章节，跳过备份"
fi

# 6. 清理draft缓存（可选）
echo ""
echo "[6/7] 清理draft缓存..."
echo "   ⏭️  跳过清理（保留现有draft）"

# 7. 生成运行配置
echo ""
echo "[7/7] 生成运行配置..."
cat > "$RUNTIME_DIR/30chapter_rerun_config.yaml" << 'INNEREOF'
# 30章重跑配置
project: novel-lingse
chapters: 1-30

# Phase 1增强功能
text_integrity:
  enabled: true
  cross_chapter_check: true
  
ai_taste:
  enabled: true
  quantified_instructions: true
  template_detection: true
  
length_control:
  enabled: true
  progressive_strategy: true
  max_attempts: 3
  tolerance: 0.2

# 模型配置（从.env读取）
# 优先级：1号模型 > 2号模型 > 3号模型

# 成本控制
budget_limit: 5.0  # CNY
stop_on_budget: true

# 监控
verbose: true
log_level: INFO
INNEREOF

echo "   ✅ 配置已生成: 30chapter_rerun_config.yaml"

# 完成
echo ""
echo "========================================="
echo "✅ 30章重跑环境准备完成！"
echo "========================================="
echo ""
echo "下一步："
echo "1. 检查 .env 文件中的模型配置"
echo "2. 运行: cd AI-Novel-Runtime && python3 scripts/run_30chapter_rerun.py"
echo "3. 或手动运行serial loop"
echo ""
echo "预计耗时: 2-3天"
echo "预计成本: ¥3-5"
echo ""
