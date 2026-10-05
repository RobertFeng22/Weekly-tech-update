# Neural Alpha AI 决策 Brief · 2026-09-28 — 2026-10-04

> 本周评估 3 个候选，1 个通过 hard gates，最终选择 1 个主题。
> 主要淘汰原因：strategy / architecture impact 不足（2）；当前 priority 相关性不足（2）；总分未达门槛（2）；战略约束影响不足（2）。

本期仅保留 1 个主题，因为它通过了已验证的优先级映射，并且对 Neural Alpha 当前的研究代理评测与控制边界有直接决策价值；其价值不在“又一个 agent benchmark”，而在把验收标准从表面轨迹转到可执行的终态与重复稳定性。以下选择不代表穷尽本窗口全部相关进展。

## 1. ThinkingBox：用终态与重复试验评估 tool-using agents

**核心判断：** ThinkingBox 把 agent 验收从“看起来完成了任务”推进到“外部状态是否被正确且稳定地改变”，这应直接改变 Neural Alpha 对可写入型研究工作流的验收合同。

**Evaluation score：** 94.8/100

**命中的 Neural Alpha priorities：** `decision_replay_and_attribution`、`agentic_research_and_control`

### 发生了什么

此前常见边界是：agent 评估多看 transcript、单次成功或 tool-call 合理性；新近已验证的增量是：ThinkingBox 对 507 个有状态工作流按终端 backend state 与副作用做可执行检查，并从相同干净初始状态重复运行 20 次。

### 为什么影响 Neural Alpha

当前约束是：Neural Alpha 需要让研究代理在受控条件下更新研究对象、证据记录与任务状态，但“回答合理”或“调用过工具”不足以证明系统真的把状态改对了。外部已验证增量是：ThinkingBox 显示，许多表面顺利的运行仍会留下错误终态或额外副作用，而且单次成功不等于可重复可靠。传导机制是：这类评估把正确性锚定到可冻结初始状态、可执行 postconditions（事后条件）与重复稳定性，从而把错误分解为推理错误、工具使用错误或状态写入错误。对应决策是：对任何会写入持久状态的研究 capability pack（能力包），主验收门槛应改为“状态可验证 + 可重复”，而不是 transcript-only 通过。二阶影响是架构上更应优先选择那些能定义明确 postconditions 的工作流，再谈提高自治程度。

### 建议下一步

在内部做一个受限 eval slice：选 10–20 个冻结事件包，让研究代理只允许更新一个隔离的 research object store；对每个任务从相同初始状态重跑 20 次，记录终态正确率、非预期副作用率与 pass@20 一致性。若 transcript 通过但终态失败率显著，则把“可执行 postconditions”上升为写入型工作流的硬门槛。

### 观察信号

- 是否出现对金融或高审计场景的复现实验，而不只是企业支持工作流
- 社区是否开始报告单次成功率与 repeated-run consistency 的显著差距
- 是否有后续方法专门检测隐藏副作用、脏状态继承或回滚失败
- ThinkingBox 的开源实现是否足以支持自定义状态对象与确定性 replay

### Evidence boundary

- 现有任务主要是企业业务工作流，不是事件驱动投资研究任务
- 窗口内事件更接近公开发布与工程化包装，不是首次科学披露
- 外部结果证明评估设计有价值，但不自动证明其能提升真实投研 alpha
- 是否能迁移取决于内部是否能把研究对象与状态变化编码成可执行检查

### Sources

- https://huggingface.co/blog/microsoft/thinkingbox
- https://arxiv.org/abs/2608.19741
- https://github.com/microsoft/thinkingbox

## 本周组合判断

本期内容明显集中在同一决策簇：agentic_research_and_control 与 decision_replay_and_attribution。这种集中是合理的，因为本轮通过硬门槛的候选里，只有该主题同时改变了验收标准、控制边界与内部评测设计。覆盖缺口也需要直说：高权重且仍活跃的 event_intelligence、semantic_state_and_causal_mapping、expectation_and_priced_in、forecasting_and_calibration、portfolio_risk_and_execution 等优先级，在本窗口没有合格入选证据；这仅说明本次已发现并通过审核的候选不足，不代表这些方向没有外部进展。
