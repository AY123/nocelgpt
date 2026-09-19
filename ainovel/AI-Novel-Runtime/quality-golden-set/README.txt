quality-golden-set/

B2 人工盲评金样集的存放目录。

建议结构：
- metadata/: 金样集索引、版本、标注规范、评审规则
- samples/: 具体样本，每条样本一个独立目录或文件集

每个样本建议包含：
- body.txt: 正文片段
- meta.json: 题材、章节位置、来源类型、版权/敏感风险说明
- human_scores.json: 双编辑/多编辑评分
- labels.json: 问题标签与优点标签
- notes.md: 评分理由与边界说明
