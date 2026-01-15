# AICouncil v2.0.1 Release Notes

## 🐛 Bug Fixes

### 报告加载优化
**问题描述**：历史报告加载时偶尔出现 JS/配置丢失，导致交互功能失效

**解决方案**：
- 移除 `handleFinalReport` 函数内部的早期数据校验
- 在两个调用入口（WebSocket 事件流 + pollStatus API）进行前置校验
- 确保只有有效数据（`report_html.length > 100`）才会触发处理函数
- 避免因防御性代码导致的延迟加载时配置丢失

**影响范围**：所有历史报告加载场景

---

### 议事编排官议题字段错误
**问题描述**：使用"议事编排官"模式时，参考资料整理官收到的是问题分类（如"决策类"）而非实际议题内容，导致搜索结果相关性过滤失败

**解决方案**：
- 修复从 `orchestration_result.json` 加载报告数据时的字段映射错误
- 从错误的 `plan.analysis.problem_type` 改为正确的 `user_requirement`
- 确保整个议事流程中议题内容传递的一致性

**影响范围**：仅影响"议事编排官"模式（传统 `run_full_cycle` 模式不受影响）

---

### 用户数据库安全
- 将 `data/users.db` 从 Git 跟踪中移除，避免敏感数据泄露
- 确保用户认证信息本地化存储

---

## 📦 下载

### Windows 可执行文件
- **AICouncil-2.0.1-Windows.zip** (约 250MB)
  - 单目录模式，解压即用
  - 包含 Playwright Chromium 浏览器（用于 PDF 导出）
  - 运行 `AICouncil.exe` 启动

### 源码运行
```bash
git clone https://github.com/mzniu/AICouncil.git
cd AICouncil
git checkout v2.0.1
pip install -r requirements.txt
python src/web/app.py
```

---

## 🔧 配置要求

### API Keys
在 `src/config.py` 中配置至少一个模型后端：
- DeepSeek API
- OpenAI / OpenRouter
- Aliyun DashScope (Qwen)
- Ollama (本地模型)

详见：[docs/deployment.md](docs/deployment.md)

---

## 📝 完整更新日志

查看 [CHANGELOG.md](CHANGELOG.md) 了解 2.0.0 版本的完整功能列表（认证系统、议事编排官、Mermaid 图表等）。

---

## 🙏 反馈与支持

- 🐛 报告 Bug：[GitHub Issues](https://github.com/mzniu/AICouncil/issues)
- 💬 功能建议：[GitHub Discussions](https://github.com/mzniu/AICouncil/discussions)
- 📧 联系方式：通过 GitHub Issues 联系维护者

---

**感谢使用 AICouncil！**
