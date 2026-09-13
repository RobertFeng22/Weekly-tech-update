# Weekly AI Intelligence Briefing

每周自动研究最近 7 个完整自然日内的 AI 进展，但不是做泛行业新闻摘要。项目使用一个由 Neural Alpha Obsidian 战略与架构记录提炼、经审阅的 private versioned context snapshot，把外部进展映射到当前 strategy、architecture、evaluation、risk、data 或 investment decision。目标读者是偏 business / investment 的 founder，不假设读者日常写模型或使用 PyTorch。

经过独立核验和受众适配硬门槛后，每期只保留最多 3 个主题；随后用 OpenAI TTS 生成中文旁白，由 Remotion 渲染为视频，并通过 GitHub Release 提供稳定链接。宁可只有 1 个重要主题，也不为了周更凑满 3 个。

## Pipeline

研究和视频是两段独立、可审计的流水线：

1. **Context snapshot**：本地使用被 Git 忽略的 `.local/neural-alpha-selection-context.json`，GitHub Actions 使用 encrypted secret `NEURAL_ALPHA_SELECTION_CONTEXT_JSON`。它保存从 Obsidian 定向提炼、经审阅的 fund identity、strategy wedge、active priorities、current constraints、high-value signals 和 false friends；超过 60 天未更新时 fail closed。公开的 `config/neural-alpha-selection-context.example.json` 只定义 schema 和示例，不含 Neural Alpha context。
2. **Scout**：使用 Responses API 的 `web_search` 搜集 8–15 个候选。每个候选必须选择一个 admission mode，并完成 `当前约束 → 外部变化 → 传导机制 → decision/test` 的结构化 relevance path。
3. **Evaluator**：重新打开来源并主动搜索反证；外部来源验证 AI 进展，context snapshot 独立验证 Neural Alpha 相关性，二者不能互相替代。
4. **Hard gates**：代码检查来源、日期、admission route、validated priority intersection、current-priority relevance、strategy/architecture impact、impact-chain quality、decision value 和总分。
5. **Editor**：只能从通过全部 gate 的候选中选择最多 3 个主题；两个主题若导向同一个 decision/test，原则上只保留证据更强的一个。
6. **Video director**：把 approved edition 转换为 8–14 个 source-grounded 场景，重点解释 Neural Alpha 当前 blocker、变化机制、内部 evaluation、二阶影响和 evidence boundary。
7. **OpenAI TTS + Remotion**：按场景生成中文 WAV，以真实音频时长渲染 1080p H.264 MP4。

三条 admission route：

- `frontier_shift`：AI capability、reliability、economics、control 或 deployability 边界显著移动，要求 `frontier_significance >= 4/5`；
- `direct_build_leverage`：新方法可直接降低一个 active strategy/architecture blocker 的验证成本，要求 `transfer_readiness >= 4/5`；
- `strategic_constraint_or_threat`：data rights、security、policy、platform 或 market structure 变化会迫使计划改变，要求 `strategic_magnitude >= 4/5`。

无论走哪条 route，都必须满足：至少两个经核验来源；primary source 被重新确认；`factual_accuracy >= 4/5`、`evidence_strength >= 3/5`、`current_priority_relevance >= 4/5`、`max(strategy_impact, architecture_impact) >= 4/5`、`relevance_path_quality >= 4/5`、`business_decision_value >= 3/5`、总分 `>= 70/100`；candidate 和 evaluator 的 priority IDs 必须与 context 中 `active + weight >= 4` 的 priority 相交。Evaluator 若判定 `engineering_only` 或 `generic_relevance_only`，直接 block。任何未解决的 `red_flags` 也会淘汰候选。没有内容达标时任务会失败，不会凑数。

普通 PyTorch / SDK / serving 更新、泛 productivity、generic sentiment、融资新闻和“AI 将改变金融”这类叙事，即使是大公司发布，也不会因为流行度或宽泛 finance use case 获得相关性分数。

## Neural Alpha context 的隐私与更新

GitHub Actions 无法读取 Robert 本地的 Obsidian，而且仓库是公开的。因此实际 snapshot 不进入 Git：本地文件被 `.gitignore` 排除，远程 workflow 通过 GitHub encrypted secret 注入，程序不会打印 secret。每次方向发生实质变化时，应从 Obsidian 定向更新 snapshot 的 `as_of`、priority status、current state 和 current need；超过 60 天未更新会 fail closed。每期 manifest 只记录 context 的 version、`as_of` 与 SHA-256，不保存正文，既能证明当时使用了哪个版本，也不会把 private context 写入公开 artifact。

Snapshot 本身也应遵守最小披露：不要包含 credentials、capital amounts、counterparties、private datasets 或不需要进入模型 prompt 的 proprietary implementation。由于 `weekly-update.md` 和视频目前会发布到公开 GitHub Release，prompt 要求使用 context 做内部筛选，但不得逐字复述 private current state/current need；发布前仍应抽查是否包含不应公开的内部信息。

## 每期产物

每期写入 `editions/YYYY-MM-DD/`：

- `weekly-update.md`：给人阅读的 AI frontier briefing，渲染完成后包含视频链接；
- `video-source.md`：只包含通过 evidence gate 的视频事实边界；
- `manifest.json`：候选、评分、门槛和模型配置的研究审计记录；
- `video-plan.json`：Video director 生成的结构化旁白与场景设计；
- `remotion-props.json`：带真实音频时长的 Remotion 时间轴；
- `video-manifest.json`：TTS 模型、voice、视频时长、SHA-256 和 Release URL。

WAV 与 MP4 不进入 Git 历史。Workflow 会把 MP4 上传到 `weekly-YYYY-MM-DD` GitHub Release，并把同一文件保留为 30 天 Actions artifact。公开视频链接格式为：

```text
https://github.com/RobertFeng22/Weekly-tech-update/releases/download/weekly-YYYY-MM-DD/ai-weekly-YYYY-MM-DD-zh.mp4
```

视频中会持续显示 AI voice disclosure；旁白不是人类录音。

## 每周执行

[GitHub Actions workflow](.github/workflows/weekly.yml) 在每周一 **08:00 Asia/Singapore**（UTC 周一 00:00）执行，也支持手动触发。手动触发时可设置 `as_of` 和 `max_topics`；若只想评审选题，可勾选 `research_only` 跳过 TTS、Remotion 和 Release。若同一日期已经存在，勾选 `regenerate_edition` 才会按当前筛选逻辑重做周报、video plan 和旁白。首次运行前，在仓库 **Settings → Secrets and variables → Actions** 添加：

- Secret `OPENAI_API_KEY`（必需）；
- Secret `NEURAL_ALPHA_SELECTION_CONTEXT_JSON`（必需；完整 JSON，不要放在 repo、Variable 或 workflow log 中）；
- Variable `OPENAI_MODEL`（可选，默认 `gpt-5.4`）；
- Variable `OPENAI_VIDEO_MODEL`（可选，默认继承 `OPENAI_MODEL`）；
- Variable `OPENAI_TTS_MODEL`（可选，默认 `gpt-4o-mini-tts`）；
- Variable `OPENAI_TTS_VOICE`（可选，默认 `cedar`）。

Workflow 会安装 Python、Node.js、Remotion 和 Noto CJK font，依次测试、研究、持久化已批准的 edition、生成 TTS、渲染、写回视频 metadata，并发布视频 Release。研究结果会在耗时的视频阶段之前提交，所以后续渲染失败不会丢失 selection audit。默认分支若开启保护，需要允许 GitHub Actions 写入，或把 commit step 改为创建 PR。

## 本地运行

要求 Python 3.11+、Node.js 22+，以及能渲染中文的 CJK font。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
npm ci

export OPENAI_API_KEY='...'

mkdir -p .local
cp config/neural-alpha-selection-context.example.json \
  .local/neural-alpha-selection-context.json
# Edit the ignored local file using the current, reviewed Obsidian context.

EDITION_DIR=$(weekly-tech-update --as-of 2026-08-26 --output-root editions)
weekly-tech-video prepare \
  --edition-dir "$EDITION_DIR" \
  --public-root public \
  --repository RobertFeng22/Weekly-tech-update

npm run render:video -- \
  "$EDITION_DIR/ai-weekly-2026-08-26-zh.mp4" \
  --props="$EDITION_DIR/remotion-props.json" \
  --codec=h264 --crf=18 --audio-bitrate=192k

weekly-tech-video finalize \
  --edition-dir "$EDITION_DIR" \
  --video-path "$EDITION_DIR/ai-weekly-2026-08-26-zh.mp4" \
  --repository RobertFeng22/Weekly-tech-update
```

`--as-of` 的研究窗口是它之前的 7 个完整自然日；例如 `2026-08-26` 会研究 `2026-08-19` 至 `2026-08-25`。

如果只想调整动效，可以运行 `npm run studio`，打开 `WeeklyAI` composition，并载入某期 `remotion-props.json`。如果希望复用已有 `video-plan.json`，再次执行 `prepare` 即可；只有显式添加 `--regenerate-plan` 才会重写场景与旁白。

## 质量边界

- Video director 无 web access，只能使用 approved edition，避免在视频阶段扩展事实。
- 每个 topic 必须保留 evaluator 验证过的 Neural Alpha priority IDs，并说明当前约束、已验证变化、传导机制、decision/test 和后续观察信号；editor 不得引入新的 priority mapping。视频至少包含 problem、mechanism，以及 decision scenario 或 evidence/limits 场景。未知 `topic_id` 会 fail closed。
- TTS 使用 OpenAI Audio API 的 `gpt-4o-mini-tts`；模型和 voice 都记录在 `video-manifest.json`。
- 字幕按旁白标点切片并映射到真实音频时长。它不是 word-level forced alignment，因此发布前仍应抽查字幕切换、专有名词读音和事实表达。
- Remotion 负责信息图与动画，不伪造产品 UI 或未经来源支持的 benchmark 图表。

OpenAI TTS 用法以 [official OpenAI Text-to-Speech documentation](https://developers.openai.com/api/docs/guides/text-to-speech) 为准；Remotion 的 [render](https://www.remotion.dev/docs/render)、[audio](https://www.remotion.dev/docs/audio/importing) 与 [GitHub Actions SSR](https://www.remotion.dev/docs/ssr) 文档是渲染实现依据。
