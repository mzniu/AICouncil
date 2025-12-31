# AICouncil 打包版用户手册

欢迎使用 AICouncil（AI 元老院）打包版！本手册将帮助您快速上手使用。

---

## 📋 目录

- [快速开始](#快速开始)
- [首次运行](#首次运行)
- [配置 API 密钥](#配置-api-密钥)
- [使用指南](#使用指南)
- [常见问题](#常见问题)
- [故障排除](#故障排除)

---

## 快速开始

### 系统要求
- **操作系统**: Windows 10/11 (64位)
- **内存**: 建议 4GB 以上
- **磁盘空间**: 200MB 可用空间（用于存储讨论数据）
- **网络**: 需要访问 LLM API（DeepSeek、OpenAI 等）

### 安装步骤
1. **下载**: 从 [GitHub Releases](https://github.com/mzniu/AICouncil/releases) 下载最新版本
2. **解压**: 解压到任意目录（如 `C:\AICouncil\`）
3. **运行**: 双击 `AICouncil.exe`

**无需安装 Python 或任何依赖！**

---

## 首次运行

### 启动程序
双击 `AICouncil.exe`，会看到：

```
============================================================
  🏛️ 欢迎使用 AICouncil（AI 元老院）
============================================================

检测到首次运行，正在初始化配置...

✅ 配置初始化成功！

配置文件位置: C:\Users\YourName\AppData\Roaming\AICouncil\config.py

💡 提示：
   1. 请编辑配置文件填入您的 API 密钥
   2. 或在 Web 界面右上角「设置」中配置

按回车键继续启动...
```

### 首次配置
1. **按回车键** 继续
2. 程序会自动：
   - 启动 Flask 服务器（端口 5000）
   - 在浏览器打开 `http://127.0.0.1:5000`
3. 进入 Web 界面

---

## 配置 API 密钥

### 方式 1: Web 界面配置（推荐）

1. 点击右上角 **⚙️ 设置** 按钮
2. 在弹出窗口填入您的 API 密钥：
   - **DeepSeek API Key** (推荐)
   - **OpenAI API Key**
   - **Aliyun API Key** (Qwen)
   - 或其他支持的后端
3. 点击 **保存配置**

### 方式 2: 编辑配置文件

1. 打开配置文件：
   - 路径：`%APPDATA%\AICouncil\config.py`
   - 或：`C:\Users\你的用户名\AppData\Roaming\AICouncil\config.py`

2. 编辑文件，填入 API 密钥：
   ```python
   # DeepSeek API (推荐)
   DEEPSEEK_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxx"
   DEEPSEEK_BASE_URL = "https://api.deepseek.com"
   
   # OpenAI API
   OPENAI_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxx"
   OPENAI_BASE_URL = "https://api.openai.com/v1"
   
   # Aliyun DashScope (Qwen)
   ALIYUN_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxx"
   ```

3. 保存文件并重启程序

### 获取 API 密钥

- **DeepSeek**: https://platform.deepseek.com/api_keys
- **OpenAI**: https://platform.openai.com/api-keys
- **Aliyun**: https://dashscope.console.aliyun.com/apiKey

---

## 使用指南

### 发起讨论

1. **填写议题**
   - 在「输入您的议题」框中输入问题
   - 例如：「如何提高团队协作效率」

2. **配置参数**（可选）
   - **模型后端**: 选择 LLM 服务商（deepseek/openai/aliyun/ollama）
   - **讨论轮数**: 建议 2-3 轮
   - **策论家数量**: 建议 2-3 个
   - **监察官数量**: 建议 1-2 个

3. **开始讨论**
   - 点击「开始议事」按钮
   - 实时查看智能体思考过程

### 查看结果

讨论完成后：
- **讨论面板**: 实时显示各智能体发言
- **最终报告**: 结构化 HTML 报告
- **导出选项**:
  - 📄 **复制为 HTML**: 完整报告代码
  - 🖼️ **下载长图**: PNG 格式截图
  - 📑 **导出 PDF**: 高质量 PDF（需 Playwright）

### 管理历史记录

- **查看历史**: 点击右上角「历史」按钮
- **加载会话**: 选择历史记录重新查看
- **删除记录**: 点击「删除」按钮清理旧数据

### 使用预设配置

1. **保存预设**: 讨论配置满意后点击「保存当前配置为预设」
2. **加载预设**: 下次使用时从下拉菜单选择预设
3. **删除预设**: 点击预设旁的删除按钮

---

## 常见问题

### Q1: 如何停止正在运行的讨论？
**答**: 点击「停止讨论」按钮即可终止当前会话。

### Q2: 讨论数据存储在哪里？
**答**: 
- **配置文件**: `%APPDATA%\AICouncil\config.py`
- **讨论数据**: `%APPDATA%\AICouncil\workspaces\`

### Q3: 可以离线使用吗？
**答**: 
- ✅ Web 界面可离线运行
- ❌ 讨论需要联网访问 LLM API
- 💡 可使用本地 Ollama 模型实现完全离线

### Q4: 支持哪些搜索引擎？
**答**: 
- ✅ **Yahoo** (默认，无需浏览器)
- ✅ **Mojeek** (无需浏览器)
- ✅ **DuckDuckGo** (无需浏览器)
- ⚠️ **Baidu/Bing** (需 DrissionPage，完整版包含)

### Q5: PDF 导出失败怎么办？
**答**: 
- **原因**: 打包版默认不包含 Playwright
- **解决**: 使用「下载长图」或「复制 HTML」代替
- **完整版**: 下载包含 Playwright 的完整版（体积更大）

### Q6: 如何使用本地模型（Ollama）？
**答**:
1. 安装 Ollama: https://ollama.com/
2. 拉取模型: `ollama pull qwen2.5:7b`
3. 在 Web 界面选择「ollama」后端
4. 填入模型名称: `qwen2.5:7b`

### Q7: 程序闪退怎么办？
**答**:
1. 以管理员身份运行
2. 检查端口 5000 是否被占用
3. 查看日志文件: `%APPDATA%\AICouncil\aicouncil.log`
4. 关闭杀毒软件试试

---

## 故障排除

### 问题 1: 无法启动服务器
**错误**: "端口 5000 被占用"

**解决**:
```powershell
# 查找占用端口的进程
netstat -ano | findstr :5000

# 结束进程（替换 PID）
taskkill /PID <进程ID> /F
```

或程序会自动尝试 5001-5009 端口。

### 问题 2: API 密钥无效
**错误**: "API authentication failed"

**检查**:
1. API 密钥是否正确（无多余空格）
2. API 密钥是否过期
3. 账户余额是否充足
4. BASE_URL 是否正确

### 问题 3: 讨论进度卡住
**现象**: 长时间无响应

**解决**:
1. 检查网络连接
2. 查看是否触发搜索（搜索较慢）
3. 点击「停止讨论」并重试
4. 减少策论家/监察官数量

### 问题 4: 中文显示乱码
**原因**: 系统编码问题

**解决**:
1. 在 `config.py` 中添加：
   ```python
   import sys
   sys.stdout.reconfigure(encoding='utf-8')
   ```
2. 或在浏览器中手动设置编码为 UTF-8

### 问题 5: 找不到配置文件
**解决**:
```powershell
# 打开配置目录
explorer %APPDATA%\AICouncil
```

如果目录不存在，重新运行 `AICouncil.exe` 会自动创建。

---

## 数据管理

### 备份配置
```powershell
# 备份配置文件
copy %APPDATA%\AICouncil\config.py D:\backup\config_backup.py
```

### 清理旧数据
```powershell
# 清理所有讨论数据（谨慎操作！）
rmdir /s /q %APPDATA%\AICouncil\workspaces
```

### 迁移到新电脑
1. 复制整个 `%APPDATA%\AICouncil\` 目录
2. 在新电脑相同位置粘贴
3. 运行 `AICouncil.exe`

---

## 高级功能

### 用户介入
在讨论过程中：
1. 点击「用户介入」按钮
2. 输入指导意见（如「重点关注成本效益」）
3. 智能体会根据您的指令调整讨论方向

### 自定义代理数量
- **策论家**: 负责提出解决方案（建议 2-3 个）
- **监察官**: 负责批判审查（建议 1-2 个）
- **轮数**: 每轮包含 提案 → 审查 → 综合（建议 2-3 轮）

**注意**: 代理数量和轮数越多，讨论时间越长，API 调用费用越高。

### 模型选择建议
| 模型 | 速度 | 质量 | 成本 | 推荐场景 |
|------|------|------|------|---------|
| DeepSeek Chat | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 日常使用（性价比最高）|
| DeepSeek Reasoner | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 复杂推理、深度分析 |
| GPT-4 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | 高质量要求 |
| Qwen 2.5 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | 中文场景、快速响应 |
| Ollama (本地) | ⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | 离线使用、数据隐私 |

---

## 卸载

### 完全卸载
1. 删除程序目录（如 `C:\AICouncil\`）
2. 删除配置和数据：
   ```powershell
   rmdir /s /q %APPDATA%\AICouncil
   ```

### 保留数据卸载
只删除程序目录，保留 `%APPDATA%\AICouncil\` 以便重装后恢复。

---

## 更新

### 检查更新
访问 [GitHub Releases](https://github.com/mzniu/AICouncil/releases) 查看最新版本。

### 更新步骤
1. 下载新版本
2. 关闭旧版本程序
3. 解压到新目录
4. 配置和数据会自动保留（存储在 `%APPDATA%`）

---

## 获取帮助

- **项目主页**: https://github.com/mzniu/AICouncil
- **提交 Issue**: https://github.com/mzniu/AICouncil/issues
- **查看文档**: [docs/](../docs/)
- **构建指南**: [build_guide.md](build_guide.md)

---

## 许可证

AICouncil 采用 MIT 许可证开源。详见 [LICENSE](../LICENSE) 文件。

---

*感谢使用 AICouncil！祝您议事愉快！*

*最后更新: 2025-12-30*
