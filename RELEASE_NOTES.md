# Release Notes — 1.1.0 (2026-01-05)

Highlights:

- 👹 Devil's Advocate (closed-loop challenge)
  - New agent role that issues structured challenges and blind-spot lists during decomposition and after each round summary.
  - Severity labeling (Critical / Warning / Minor). Leaders must respond; final-round forced revision ensures quality.

- 🔄 User-driven report revision & versioning
  - Floating "💬 Revision Feedback" panel on reports for users to submit revision requests.
  - Original report automatically backed up as `report_v0.html`; subsequent revisions saved as `report_v1.html`, `report_v2.html`, etc.
  - Version selector in report header for easy comparison and rollback.
  - `Report Auditor` agent to analyze feedback and generate suggested revisions.

Bugfixes & Improvements:

- Fixed original report being overwritten during revisions (now saved as `report_v0.html`).
- Fixed report version selector visibility when loading historical workspaces.
- Optimized Reporter output to integrate internal feedback naturally without exposing internal role dialogues.

How to use the new features:

1. Generate a report as usual.
2. At the bottom of the report, click **💬 修订反馈** and submit your requested changes.
3. Review the suggested revision and click **Apply Revision** to update the report, or keep the original by switching to `report_v0.html` via the version selector.

See `CHANGELOG.md` and `README.md` for full details.

---

# 发布说明 — 1.1.0（2026-01-05）

亮点：

- 👹 质疑官（闭环质疑）
  - 新增智能体角色，在议题拆解阶段和每轮总结后输出结构化的质疑与盲点清单。
  - 按严重度分类（Critical / Warning / Minor），议长必须回应；若存在关键问题，最终轮将触发强制修订以保证质量。

- 🔄 用户参与式报告修订与版本管理
  - 报告页面新增“💬 修订反馈”浮动面板，用户可提交修订请求。
  - 系统会在首次修订前自动备份原始报告为 `report_v0.html`；后续修订保存为 `report_v1.html`、`report_v2.html` 等。
  - 报告标题栏提供版本选择器，便于比较和回退。
  - 引入 `Report Auditor` 智能体负责分析反馈并生成修订建议，支持一键应用与预览。

修复与改进：

- 修复修订时覆盖原始报告的问题（现在会保存 `report_v0.html`）。
- 修复历史工作区加载时版本选择器不可见的问题。
- 优化 Reporter 输出格式，将内部角色反馈自然整合到报告中，不再直接展示角色间的对话记录。

如何使用这些新功能：

1. 按常规流程生成报告。
2. 在报告页面底部点击 **💬 修订反馈** 并提交您的修改请求。
3. 查看系统生成的修订摘要与变更清单，点击“应用修订”更新报告，或通过版本选择器切回 `report_v0.html` 保留原稿。

更多细节请参阅 `CHANGELOG.md` 与 `README.md`。
