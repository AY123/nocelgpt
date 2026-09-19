#!/bin/bash
# 建 v12-vs-v13 双臂 A/B 的 4 个实验臂。
#
# 每臂是一个干净项目:同一 registry/facts + 同一 outline + 同一 sources,
# 但 registry/derived 里不带任何旧 draft(否则 task_id 会撞旧产物)。
#
# 池化设计:单项目章数硬顶 33(一事件一章,plan_chapters),
# 所以取两本不同的书各跑双臂 → 66 配对 > 设计要求的 n=60。
set -euo pipefail

ROOT="/Users/angyang/Documents/xiaoshuo/AINovel"
cd "$ROOT"

# story 代号 -> 源项目
declare -a STORIES=("lingse:novel-lingse" "guhai:genesis-pilot")

for entry in "${STORIES[@]}"; do
  story="${entry%%:*}"
  src="${entry##*:}"
  for arm in v12 v13; do
    dst="v13ab-${story}-${arm}"
    rm -rf "$dst"
    mkdir -p "$dst/registry/derived"
    # facts / _meta / sources 原样复制(两臂输入完全同一)
    cp -R "$src/registry/_meta" "$dst/registry/_meta"
    cp -R "$src/registry/facts" "$dst/registry/facts"
    cp -R "$src/sources" "$dst/sources"
    # outline 是 derived,但生成链要读它(load_project_outline)
    if [ -d "$src/registry/derived/outline" ]; then
      cp -R "$src/registry/derived/outline" "$dst/registry/derived/outline"
    fi
    echo "built $dst  (facts=$(ls "$dst/registry/facts/events" | wc -l | tr -d ' ') events)"
  done
done

echo "--- 校验两臂输入同一 ---"
# 注意:不能用 `xargs shasum | shasum` —— shasum 的输出里带文件路径,
# 而两臂路径必然不同(v12 vs v13),那样算出的摘要永远不等,是个假警报。
# 只对文件内容做摘要(cut 掉路径列),才是真正比较输入是否同一。
for story in lingse guhai; do
  a=$(find "v13ab-${story}-v12/registry/facts" -type f | sort | xargs shasum | awk '{print $1}' | shasum | cut -d' ' -f1)
  b=$(find "v13ab-${story}-v13/registry/facts" -type f | sort | xargs shasum | awk '{print $1}' | shasum | cut -d' ' -f1)
  if [ "$a" = "$b" ]; then echo "  $story: facts 一致 ✓"; else echo "  $story: facts 不一致 ✗"; exit 1; fi
  diff -r "v13ab-${story}-v12/registry/facts" "v13ab-${story}-v13/registry/facts" >/dev/null \
    || { echo "  $story: diff -r 不一致 ✗"; exit 1; }
done
