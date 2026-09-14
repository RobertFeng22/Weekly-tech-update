# Neural Alpha Weekly AI Decision Brief

每周自动研究最近 7 个完整自然日内的 AI 进展，并输出一份面向 Neural Alpha 的书面决策 brief。它不是泛行业新闻摘要，也不再生成视频。目标读者是偏 business / investment 的 founder；每期最多保留 2 个真正可能改变 strategy、architecture、evaluation、risk、data 或 investment decision 的主题。

宁可只有 1 个主题，甚至因没有内容通过门槛而失败，也不为周更凑数。

## Pipeline

1. **Context snapshot**：本地使用被 Git 忽略的 `.local/neural-alpha-selection-context.json`，GitHub Actions 使用 encrypted secret `NEURAL_ALPHA_SELECTION_CONTEXT_JSON`。它保存从 Neural Alpha 的 Obsidian/Notion strategy 与 architecture 记录中定向提炼、经审阅的 fund identity、strategy wedge、active priorities、current constraints、high-value signals 和 false friends；超过 60 天未更新时 fail closed。公开的 `config/neural-alpha-selection-context.example.json` 只定义 schema 与示例，不包含 Neural Alpha 私有 context。
2. **Scout**：使用 OpenAI Responses API 的 `web_search` 搜集候选。每个候选必须选择一个 admission route，并完成 `当前约束 → 外部变化 → 传导机制 → decision/test` 的 relevance path。
3. **Evaluator**：重新打开来源并主动搜索反证。外部来源验证 AI 进展；private context 独立验证 Neural Alpha 相关性，二者不能互相替代。
4. **Hard gates**：代码检查日期、来源、primary-source 复核、admission route、当前 priority 命中、strategy/architecture impact、relevance-path quality、decision value、red flags 与总分。
5. **Editor**：只能从通过全部 gates 的候选中选择最多 2 个主题。若两个主题导向相同 decision/test，除非证据冲突或需要不同 control，否则只保留更强的一项。
6. **Brief renderer**：生成结构稳定的 Markdown brief，并附上候选数、通过数、主要淘汰原因、每个主题的行动建议，以及对主题集中度和 coverage gap 的组合判断。

三条 admission route：

- `frontier_shift`：AI capability、reliability、economics、control 或 deployability 的边界显著移动，要求 `frontier_significance >= 4/5`；
- `direct_build_leverage`：新方法可直接降低一个 active strategy/architecture blocker 的验证成本，要求 `transfer_readiness >= 4/5`；
- `strategic_constraint_or_threat`：data rights、security、policy、platform 或 market structure 变化会迫使计划改变，要求 `strategic_magnitude >= 4/5`。

无论走哪条 route，通常都要有至少两个经核验来源，且 primary source 必须被重新确认；同时满足 `factual_accuracy >= 4/5`、`evidence_strength >= 3/5`、`current_priority_relevance >= 4/5`、`max(strategy_impact, architecture_impact) >= 4/5`、`relevance_path_quality >= 4/5`、`business_decision_value >= 3/5` 和总分 `>= 70/100`。Candidate 与 evaluator 的 priority IDs 还必须和 context 中 `active + weight >= 4` 的 priorities 相交。

若一个完整 authoritative primary artifact 足以直接证明被严格限定的发布事实，evaluator 可以设置 `authoritative_primary_sufficient=true`；该例外不能替代 performance、safety、generalization、transfer 或 independent-reproduction 的证据。`engineering_only`、`generic_relevance_only` 或任何未解决的 `red_flags` 都会直接淘汰候选。

普通 PyTorch / SDK / serving 更新、泛 productivity、generic sentiment、融资新闻和“AI 将改变金融”叙事，不会因为流行度或宽泛 finance use case 获得相关性分数。

## Brief 格式

每期的 `weekly-update.md` 固定包含：

- 本周候选数、hard-gate 通过数和主要淘汰原因；
- 每个主题的核心判断、evaluation score 与命中的 Neural Alpha priorities；
- `发生了什么`：此前边界与本周新证据；
- `为什么影响 Neural Alpha`：具体 transmission mechanism 和二阶影响；
- `建议下一步`：一个 bounded internal evaluation、decision、control change 或 watch trigger；
- 观察信号、evidence boundary 和 sources；
- `本周组合判断`：明确主题是否过度集中，以及哪些当前高权重 priorities 没有找到达标证据。

Editor 的可发布字段使用中文，但保留必要的 English technical terms。Private context 只参与 selection 与 relevance validation，不得被逐字复述到公开 brief。

## Neural Alpha context 的隐私与更新

GitHub Actions 无法读取本地 Obsidian，而且仓库是公开的，因此实际 snapshot 不进入 Git：本地文件由 `.gitignore` 排除，远程 workflow 通过 GitHub encrypted secret 注入，程序不会打印 secret。每次 strategy 或 architecture 方向发生实质变化时，应更新 snapshot 的 `as_of`、priority status、current state 与 current need；超过 60 天未更新会 fail closed。

每期 `manifest.json` 只记录 context 的 version、`as_of` 与 SHA-256，不保存正文。Snapshot 不应包含 credentials、capital amounts、counterparties、private datasets 或不需要进入模型 prompt 的 proprietary implementation。仓库公开，因此仍应在发布前抽查 brief 是否包含不应公开的内部信息。

## 每期产物

每期写入 `editions/YYYY-MM-DD/`：

- `weekly-update.md`：给 Robert 阅读的双主题 AI decision brief；
- `manifest.json`：候选、evaluation、hard-gate 结果、模型配置与 selection-context fingerprint，便于审计和重放；
- `failed-run-manifest.json`：没有候选通过时的失败审计记录。

历史 edition 中的 NotebookLM、Remotion、TTS 与 MP4 文件会保留为旧记录，但新的 workflow 不会再创建或发布视频资产。

## 每周执行

[GitHub Actions workflow](.github/workflows/weekly.yml) 在每周一 **08:00 Asia/Singapore**（UTC 周一 00:00）执行，也支持手动触发。手动触发可以设置 `as_of`、`max_topics`（1–2）与 `regenerate_edition`。首次运行前，在仓库 **Settings → Secrets and variables → Actions** 添加：

- Secret `OPENAI_API_KEY`（必需）；
- Secret `NEURAL_ALPHA_SELECTION_CONTEXT_JSON`（必需；完整 JSON，不要放进 repo、Variable 或 workflow log）；
- Variable `OPENAI_MODEL`（可选，默认 `gpt-5.4`）。

Workflow 只安装 Python dependencies，执行测试与完整研究流程，将通过筛选的 edition commit 到默认分支，并保留 30 天 Actions artifact。默认分支若开启保护，需要允许 GitHub Actions 写入，或把 commit step 改为创建 PR。

## 本地运行

要求 Python 3.11+：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

export OPENAI_API_KEY='...'

mkdir -p .local
cp config/neural-alpha-selection-context.example.json \
  .local/neural-alpha-selection-context.json
# 用当前、经审阅的 Neural Alpha context 修改这个被 Git 忽略的本地文件。

weekly-tech-update \
  --as-of 2026-09-14 \
  --output-root editions \
  --max-topics 2
```

`--as-of` 的研究窗口是它之前的 7 个完整自然日；例如 `2026-09-14` 会研究 `2026-09-07` 至 `2026-09-13`。

## 质量边界

- Scout 与 evaluator 可以使用 web search；editor 无 web access，只能使用 approved candidates、evaluations 与 versioned context。
- Brief 不能引入新的 source URL、candidate 或 priority mapping；runtime 会用 allowlist 复核。
- `portfolio_judgment` 必须披露主题集中度和未覆盖的 active priority，不能把“本周没有达标证据”写成“该方向没有进展”。
- 没有候选通过时，workflow 会保留 failure audit 并失败，不生成空 brief。
- Responses API 使用 structured output 约束每个阶段的 schema，并设置 `store=False`。

OpenAI API 的实现以 [official Responses API documentation](https://developers.openai.com/api/reference/cli/resources/responses/methods/create) 为准。
