# P0+P1验证执行指南

## 🎯 目标

生成3个新章节（TASK-00101到103），验证P0+P1修复效果。

---

## 🚀 快速开始

### 方式1: 使用自动化脚本（推荐）

```bash
./run_validation.sh
```

这个脚本会：
1. 生成3个新章节（使用P0+P1修复后的代码）
2. 自动运行验证脚本
3. 显示验证结果

---

### 方式2: 手动执行

#### 步骤1: 生成新章节

```bash
cd AI-Novel-Runtime

python3 -m runtime.cli serial run \
  --project ../novel-lingse \
  --enable-final-quality-review \
  --enable-final-reader-simulation \
  --chapters 101-103
```

**参数说明**:
- `--enable-final-quality-review`: 启用P0-3质量闭环（初评→终评→delta）
- `--enable-final-reader-simulation`: 启用P1-3读者期待提取
- `--chapters 101-103`: 生成第101-103章

**预计时间**: 10-30分钟

---

#### 步骤2: 验证数据质量

```bash
cd ..
python3 validate_p0_p1.py
```

---

#### 步骤3: 查看详细数据

```bash
# 查看完整chapter run
cat novel-lingse/registry/derived/chapter-run/run-TASK-00101.json | python3 -m json.tool | less

# 只查看Production Card
cat novel-lingse/registry/derived/chapter-run/run-TASK-00101.json | \
  python3 -c "import json, sys; print(json.dumps(json.load(sys.stdin).get('production_card', {}), indent=2))" | less
```

---

## 📊 预期验证结果

### ✅ P0-1: Reader Simulation字段完整性
- `dropout_risk` 不为null
- personas使用`would_continue`字段

### ✅ P0-2: 质量阈值正确触发
- 低于阈值的维度触发hold
- hook/retention ≥ 75
- character/world_consistency ≥ 80

### ✅ P0-3: 质量闭环
- `initial_quality_scores` ≠ `final_quality_scores`（如有修订）
- `quality_delta` 正确计算

### ✅ P0-4: 决策一致性
- `publish_recommendation` 逻辑正确
- block有blocking_issues
- hold有warnings
- recommend无阻断问题

### ✅ P1-3: Reader期待提取
- personas包含expectations字段

---

## ⚠️ 注意事项

1. **LLM配置**: 确保LLM API key已配置
2. **生成时间**: 每章约3-10分钟，总计10-30分钟
3. **磁盘空间**: 确保有足够空间存储新章节
4. **项目状态**: 建议在干净的git状态下运行

---

## 🔍 验证失败处理

如果验证发现问题：

1. **查看具体错误**:
   ```bash
   python3 validate_p0_p1.py | tee validation_results.txt
   ```

2. **检查Production Card**:
   ```bash
   cat novel-lingse/registry/derived/chapter-run/run-TASK-00101.json | \
     python3 -m json.tool > pc_101.json
   less pc_101.json
   ```

3. **对比修复前后**:
   ```bash
   # 旧章节（修复前）
   cat novel-lingse/registry/derived/chapter-run/run-TASK-00001.json
   
   # 新章节（修复后）
   cat novel-lingse/registry/derived/chapter-run/run-TASK-00101.json
   ```

---

## 📈 下一步

根据验证结果：
- **全部通过**: 进入P2商业校准阶段
- **发现问题**: 分析问题，必要时调整代码
- **效果良好但想完善**: 完成P1-4人物成长模型

---

## 🆘 获取帮助

如遇问题，提供以下信息：
1. 验证脚本输出
2. 错误日志
3. Production Card片段
4. 具体失败的检查项

---

**准备好了吗？运行 `./run_validation.sh` 开始验证！** 🚀
