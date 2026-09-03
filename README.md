# Weekly AI Tech Update

每周自动研究最近 7 个完整自然日内值得学习的 AI 进展，经过独立核验和硬门槛筛选后，只保留最多 3 个主题；随后用 OpenAI TTS 生成中文旁白，由 Remotion 渲染为教学视频，并通过 GitHub Release 提供稳定链接。

## Pipeline

研究和视频是两段独立、可审计的流水线：

1. **Scout**：使用 Responses API 的 `web_search` 搜集 8–15 个候选，覆盖 engineering practice、valuable paper 和 practical trick。
2. **Evaluator**：重新打开来源并主动搜索反证，分别评分 factual accuracy、evidence strength、practical value、novelty、transferability 和 teachability。
3. **Editor**：只能从通过硬门槛的候选中选择最多 3 个主题，写成中文教学稿。
4. **Video director**：把通过筛选的 edition 转换为 10–14 个 source-grounded 场景，包括 evaluation funnel、问题、机制、demo、证据边界和 decision guide。
5. **OpenAI TTS**：每个场景单独生成 WAV 旁白；代码读取真实音频时长，而不是按字数猜测时间轴。
6. **Remotion**：按真实音频时长渲染 1080p 动画、流程图、实验步骤、证据卡片和分段字幕，最终输出 H.264 MP4。

研究部分继续执行 deterministic hard gates：发布时间必须在窗口内；至少两个经核验来源；至少一个候选 primary source 被 evaluator 重新确认；`factual_accuracy >= 4/5`、`evidence_strength >= 3/5`、总分 `>= 70/100`；任何未解决的 `red_flags` 都会淘汰候选。没有内容达标时任务会失败，不会硬凑视频。

## 每期产物

每期写入 `editions/YYYY-MM-DD/`：

- `weekly-update.md`：给人阅读的教学版周报，渲染完成后包含视频链接；
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

[GitHub Actions workflow](.github/workflows/weekly.yml) 在每周一 **08:00 Asia/Singapore**（UTC 周一 00:00）执行，也支持手动触发。首次运行前，在仓库 **Settings → Secrets and variables → Actions** 添加：

- Secret `OPENAI_API_KEY`（必需）；
- Variable `OPENAI_MODEL`（可选，默认 `gpt-5.4`）；
- Variable `OPENAI_VIDEO_MODEL`（可选，默认继承 `OPENAI_MODEL`）；
- Variable `OPENAI_TTS_MODEL`（可选，默认 `gpt-4o-mini-tts`）；
- Variable `OPENAI_TTS_VOICE`（可选，默认 `cedar`）。

Workflow 会安装 Python、Node.js、Remotion 和 Noto CJK font，依次测试、研究、生成 TTS、渲染、写回 edition，并发布视频 Release。默认分支若开启保护，需要允许 GitHub Actions 写入，或把 commit step 改为创建 PR。

## 本地运行

要求 Python 3.11+、Node.js 22+，以及能渲染中文的 CJK font。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
npm ci

export OPENAI_API_KEY='...'

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
- 每个 topic 必须至少包含 mechanism，以及 demo 或 evidence/limits 场景；未知 `topic_id` 会 fail closed。
- TTS 使用 OpenAI Audio API 的 `gpt-4o-mini-tts`；模型和 voice 都记录在 `video-manifest.json`。
- 字幕按旁白标点切片并映射到真实音频时长。它不是 word-level forced alignment，因此发布前仍应抽查字幕切换、专有名词读音和事实表达。
- Remotion 负责信息图与动画，不伪造产品 UI 或未经来源支持的 benchmark 图表。

OpenAI TTS 用法以 [official OpenAI Text-to-Speech documentation](https://developers.openai.com/api/docs/guides/text-to-speech) 为准；Remotion 的 [render](https://www.remotion.dev/docs/render)、[audio](https://www.remotion.dev/docs/audio/importing) 与 [GitHub Actions SSR](https://www.remotion.dev/docs/ssr) 文档是渲染实现依据。
