# 部署与运行（MVP）

本章节给出在本地或简单服务器上运行 demo 的步骤（Windows PowerShell）。

## 先决条件
- Python 3.10+ 已安装并在 PATH 中可用。
- 推荐使用虚拟环境。

## 可选：本地 Ollama 支持（推荐用于离线/私有模型部署）

本项目支持使用本地运行的 Ollama 模型作为模型适配层（优点：低延迟、数据留在本地、可选择多种本地模型）。下面给出快速安装与运行示例（以 Windows PowerShell 为例）：

1. 安装 Ollama：请参考官方安装包（Windows/MSI）或使用 Homebrew/macOS 安装器；安装完成后请确保 `ollama` CLI 可在终端中访问。

2. 拉取或安装模型（以 vicuna/ggml 示例）：

```powershell
# 拉取示例模型（视模型而定）
ollama pull ggml-vicuna-13b
```

3. 启动模型（本地服务或直接使用 CLI）：

```powershell
# 使用 ollama 直接运行（CLI）
ollama run ggml-vicuna-13b --prompt "你好"

# 或者在本地启动 Ollama HTTP 服务（若支持），默认监听 127.0.0.1:11434
# 然后项目会尝试通过 http://127.0.0.1:11434/api/generate 调用模型
```

4. 在本项目中使用 Ollama：
 - 将 `model_config` 设为 {"type": "ollama", "model": "ggml-vicuna-13b"}，模型适配器会优先尝试 HTTP API（127.0.0.1:11434），若失败回退到 `ollama run` CLI。示例见 `src/agents/model_adapter.py`。

注意：不同版本的 Ollama 其 HTTP API 路径或行为可能有差异，若遇到问题请参考 Ollama 官方文档并调整 `model_adapter` 的 HTTP 请求实现。

## 环境变量（开发/演示）
- MODEL_API_KEY （可选，若接入真实模型）
- MONGODB_URI （可选，若接入 MongoDB）

## 安装依赖（PowerShell）

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 运行本地 demo

```powershell
python src\agents\demo_runner.py
```

demo_runner 会：
- 使用本地模拟模型适配器（不会调用外部 API）
- 演示一轮议长→两名策论家并行盲评→两名监察官并行质疑→议长汇总的流程
- 在控制台输出每个 Agent 的 JSON 输出与最终汇总报告

## 可选：作为 FastAPI 服务运行（扩展）

若后续需要把服务化，建议:
- 新增 `src/api/app.py`（FastAPI），并创建相应路由（参见 `docs/api_spec.md`）
- 运行：

```powershell
uvicorn src.api.app:app --reload --port 8000
```

## 监控与运维建议（后期）
- 开启请求日志与异常告警（Sentry 等）。
- 对模型调用进行计费/速率限制与配额监控。  
- 数据清理策略由管理员配置，MVP 默认为最大保留，但生产环境建议设置合适的生命周期策略以控制存储成本。
