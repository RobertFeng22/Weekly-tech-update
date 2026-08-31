# NotebookLM Source Pack: AI Weekly 2026-08-24 — 2026-08-30

本文件只包含通过证据门槛的主题。生成 Video Overview 时，要求所有事实仅来自本文件及所列 primary sources。

## Topic 1: Gemini Omni 1.1 Flash GA：把视频生成/编辑从 preview 迁移到稳定 API

Evaluation score: 83.2/100

`gemini-omni-1.1-flash` 进入 GA，意味着团队可以把视频 extension、首尾帧插值式 `image_to_video`、以及 `resolution` 控制纳入更稳定的自动化生产流程。

该能力在 2026-08-27 进入 GA，且已验证 `gemini-omni-flash-preview` 将于 2026-09-30 deprecate；如果你的流程仍绑定 preview 端点，现在就是整理迁移、参数封装和回归测试的窗口期。

核心机制不是“模型突然更强”，而是 API surface 成熟了：你不再只依赖模糊的 prompt-only 调用，而是围绕更明确的任务接口来搭建流水线，例如 `extend` 用于视频续写、`image_to_video` 用于从首尾帧做插值/过渡，并把 `resolution` 暴露成产品层参数。这样做的工程价值在于：1）调用语义更稳定，便于封装 SDK 与作业编排；2）迁移时可以对不同任务建立独立回归集，而不是把所有视频需求混成一个 prompt；3）前台产品可以显式提供 360p/720p/1080p/4K 的质量档位，让用户在速度、成本和清晰度之间做选择。要注意，GA 只说明接口和生命周期更稳定，不等于源文档已经证明了各分辨率的质量/延迟/成本最优点。

### Demo script
1. 建立一个最小迁移清单：把代码中所有 `gemini-omni-flash-preview` 搜索出来，统一替换为 `gemini-omni-1.1-flash`，并记录涉及的任务类型是 `extend` 还是 `image_to_video`。
2. 做一个最小参数化包装：为内部函数增加 `resolution` 参数，只允许传入 `360p`、`720p`、`1080p`、`4K` 这类受支持档位；先不要在业务层默认 4K。
3. 准备一个 3 样本回归集：样本 A 做 clip extension，样本 B 做首尾帧过渡，样本 C 做同一提示词下的多分辨率输出。检查迁移前后是否都能成功完成任务。
4. 可复现伪代码示意：`generate_video(task="extend", model="gemini-omni-1.1-flash", resolution="720p", input_video="clip.mp4")`；再运行 `generate_video(task="image_to_video", model="gemini-omni-1.1-flash", resolution="1080p", first_frame="start.png", last_frame="end.png")`。重点不是具体 SDK 细节，而是验证你的作业系统已经按任务类型和分辨率正确路由。
5. 在产品层加入一个简单实验开关：同样请求先默认 `720p`，仅对少量流量开放 `1080p` 或 `4K`，观察完成率与用户主观反馈。由于来源未给出成本/时延证据，这一步应由你自己测。

### Limitations
- 这是 release note / model 文档层面的已验证信息，不是独立的工程基准研究。
- 已验证能力包括 video extension、基于首尾帧的 `image_to_video`、以及 360p/720p/1080p/4K 分辨率控制；但没有经验证的成本、延迟、质量 tradeoff 数据。
- 评估中特别提醒：不要把 GA 状态过度解读为实践效果已被充分证明。
- 已验证资料还指出输出视频支持 3s-10s、最高 4K/24 FPS，但具体场景效果仍需自测。

### Source URLs
- https://ai.google.dev/gemini-api/docs/changelog
- https://ai.google.dev/gemini-api/docs/changelog?authuser=6
- https://ai.google.dev/gemini-api/docs/models/gemini-omni-flash?hl=en

### Video steering prompt
请基于提供来源，制作一个简洁的中文 Explainer 视频脚本（简体中文）。只讲来源中可证实的内容，重点包括：1）`gemini-omni-1.1-flash` GA 的工程意义；2）`extend`、`image_to_video`、`resolution` 控制分别解决什么问题；3）一个最小可复现迁移 demo；4）它的局限：没有被来源证明的成本/延迟/质量 tradeoff，不能把 GA 误解为全面性能背书。请明确引用并锚定 source URLs，不要加入来源外断言。
