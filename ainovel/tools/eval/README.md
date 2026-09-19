# tools/eval — 手动评审 Harness

这些脚本用真实 LLM（DeepSeek）跑质量流水线的各环节，用于人工观察真实产出。
**不是自动化测试**（CI 用的是 `AI-Novel-Runtime/tests/`，全部离线、无网络）。

全部带 replay 缓存：重复运行命中缓存、不重复计费，且把不可复现的 LLM 输出钉成
可复现工件。产物写入 `novel-pilot/registry/derived/`（该目录已被 `.gitignore`）。

从仓库根运行（脚本用 `Path(__file__).parents[2]` 定位仓库根）：

- `python3 tools/eval/eval_quality_deepseek.py` — Novel Quality Center 单 judge
  评审 pilot 的两份 draft（claude / gpt），并排对比 8 维评分与修改单。
- `python3 tools/eval/eval_revision_deepseek.py` — Revision Controller 完整闭环：
  评审 → 按修改单改稿 → 重新评审验证提升 / 拒绝净变差。
- `python3 tools/eval/eval_panel_deepseek.py` — 多模型评审团（DeepSeek 扮演 4 个
  角色），独立评审 + 加权融合 + 分歧 surfacing。

需要 `.env` 里的 `DEEPSEEK_API_KEY`。切换到真实 Claude/GPT/Gemini 只需在脚本里改
每个席位的 provider/model_id。

日常生产用 CLI，不用这些脚本：
```
cd AI-Novel-Runtime && python3 -m runtime.cli refine \
  --package ../novel-pilot/build/TASK-00001.package.json \
  --standard-root ../AI-Novel-Standard --project ../novel-pilot \
  --model-provider deepseek --model-id deepseek-chat \
  --reviewer panel --max-rounds 2 --env-file ../.env \
  --replay-dir ../novel-pilot/registry/derived/refine-replay
```
