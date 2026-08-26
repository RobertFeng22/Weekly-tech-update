# Weekly AI Tech Update

每周自动研究最近 7 个完整自然日内值得学习的 AI 进展，经过独立核验和硬门槛筛选后，只保留最多 3 个主题，并生成可直接导入 NotebookLM 的教学 source pack。

## 它做什么

Pipeline 分三次独立调用，避免“搜到什么就总结什么”：

1. **Scout**：使用 Responses API 的 `web_search` 搜集 8–15 个候选，覆盖 engineering practice、valuable paper 和 practical trick。
2. **Evaluator**：重新打开来源并主动搜索反证，分别评分 factual accuracy、evidence strength、practical value、novelty、transferability 和 teachability。
3. **Editor**：只能从通过硬门槛的候选中选择最多 3 个主题，写成中文教学稿和 NotebookLM steering prompt。

代码还会执行确定性的 hard gates：发布时间必须在窗口内；至少两个经核验来源；至少一个候选 primary source 被 evaluator 重新确认；`factual_accuracy >= 4/5`、`evidence_strength >= 3/5`、总分 `>= 70/100`；任何未解决的 `red_flags` 都会淘汰该候选。若没有内容达标，本周任务会失败而不是硬凑内容。

每期写入 `editions/YYYY-MM-DD/`：

- `weekly-update.md`：给人阅读的教学版周报；
- `notebooklm-source.md`：可上传 NotebookLM 的单文件 source pack，包含每个主题的教学脚本、demo、限制、来源和 Video Overview prompt；
- `manifest.json`：候选、评分、门槛和模型配置的审计记录。

## 每周执行

[GitHub Actions workflow](.github/workflows/weekly.yml) 在每周一 **08:00 Asia/Singapore**（UTC 周一 00:00）执行，也支持手动触发。首次运行前，在仓库 **Settings → Secrets and variables → Actions** 添加：

- Secret `OPENAI_API_KEY`（必需）；
- Variable `OPENAI_MODEL`（可选，默认 `gpt-5.4`）。

Workflow 会测试代码、生成本期内容、把 `editions/` commit 回默认分支，并保留 30 天 artifact。若默认分支开启保护，请允许 GitHub Actions 写入，或把 `Commit edition` step 改成创建 PR。

## 本地运行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
export OPENAI_API_KEY='...'
pytest -q
weekly-tech-update --as-of 2026-08-24 --output-root editions
```

`--as-of` 的研究窗口是它之前的 7 个完整自然日；例如 `2026-08-24` 会研究 `2026-08-17` 至 `2026-08-23`。

## NotebookLM 视频

NotebookLM 个人版目前没有公开 API，不能在无登录态的 GitHub runner 上可靠地全自动生成 Video Overview。稳定流程是：

1. 下载或打开本期 `notebooklm-source.md`；
2. 在 NotebookLM 新建 notebook 并上传该文件；
3. 在 Studio 选择 **Video Overview → Explainer**；
4. 语言选择 **简体中文**，逐个使用文件内的 `Video steering prompt` 生成视频。

本地已登录的浏览器可以由 Codex 操作完成这些 UI 步骤，但创建 notebook、上传资料和触发视频会向 Google 账户写入数据，因此每期应在执行时明确授权。Video Overview 可能需要 30 分钟以上，生成后仍应人工抽查事实、字幕和演示步骤。

## 配置

除 CLI 参数外，还支持：

- `OPENAI_DISCOVERY_MODEL`
- `OPENAI_EVALUATION_MODEL`
- `OPENAI_EDITOR_MODEL`

三者默认继承 `OPENAI_MODEL`。为减少 shared blind spot，可以给 evaluator 配置不同于 scout 的强模型；无论模型是否相同，evaluator 都是单独请求，并会重新 web search 和验证 primary source。
