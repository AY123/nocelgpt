# P0+P1验证 - 快速修复指南

## ❌ 遇到的问题

```
runtime serial run: error: the following arguments are required: --standard-root
```

## ✅ 修复方法

`--standard-root` 参数是必需的，指向标准库路径。

### 正确的命令

```bash
cd AI-Novel-Runtime

# 如果有standard-root目录
python3 -m runtime.cli serial run \
  --project ../novel-lingse \
  --standard-root <PATH_TO_STANDARD_ROOT> \
  --enable-final-quality-review \
  --enable-final-reader-simulation \
  --chapters 101-103

# 或者查找现有配置
cd ../novel-lingse
grep -r "standard" . --include="*.json" | head -5
```

---

## 🔍 查找standard-root

可能的位置：
1. `novel-lingse/standards/`
2. `../ANES-standards/`
3. 项目配置文件中指定

查找命令：
```bash
find . -name "standard-root" -o -name "standards"
cat novel-lingse/project.json 2>/dev/null | grep standard
```

---

## 📋 临时解决方案

如果找不到standard-root，可以：

1. **查看已有章节如何生成的**
2. **使用最小化参数生成**（可能不包含所有P0+P1功能）
3. **先完成P1-4任务**，等待明确standard-root路径

---

## 💡 建议

由于standard-root配置问题，建议：

**选项1**: 提供standard-root路径，我帮您生成正确命令

**选项2**: 先跳过验证，直接完成P1-4人物成长模型（不依赖运行时）

**选项3**: 查看项目文档找到正确的运行配置

---

需要我帮您：
- 查找standard-root路径？
- 完成P1-4人物成长模型？
- 或其他？
