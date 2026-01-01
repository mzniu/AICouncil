# Google 搜索功能说明

## 功能概述

提供**两种** Google 搜索方案：

1. **Google Custom Search API**（✅ 推荐）- 官方 API，稳定可靠，国内无需代理
2. **Playwright 爬虫**（⚠️ 备选）- 浏览器自动化，国内需要代理

## 实现位置

- **API 方案**: `src/utils/search_utils.py::google_search_api()`
- **Playwright 方案**: `src/utils/search_utils.py::google_search_playwright()`
- **API 测试**: `tests/test_google_api.py`
- **Playwright 测试**: `tests/test_google_search.py`

---

## 方案一：Google Custom Search API（推荐）

### ✅ 优势

- **官方 API**：无反爬虫问题
- **速度快**：响应时间 ~1 秒
- **稳定可靠**：99.9% 可用性
- **国内可访问**：无需代理
- **易于维护**：不受页面结构变化影响

### 📋 配置步骤

#### 1. 启用 Custom Search API

访问 [Google Cloud Console](https://console.cloud.google.com/)

1. 创建项目（如果没有）
2. 启用 API：https://console.cloud.google.com/apis/library/customsearch.googleapis.com
3. 点击「启用」

#### 2. 创建 API 凭据

访问 [API 凭据页面](https://console.cloud.google.com/apis/credentials)

1. 点击「创建凭据」→「API 密钥」
2. 复制生成的 API Key
3. （可选）限制 API Key 使用范围：
   - 应用限制：选择「HTTP 引荐来源网址」或「IP 地址」
   - API 限制：选择「Custom Search API」

#### 3. 创建自定义搜索引擎

访问 [Programmable Search Engine](https://programmablesearchengine.google.com/)

1. 点击「添加」创建新搜索引擎
2. 配置搜索引擎：
   - **名称**: AICouncil Search
   - **搜索范围**: 选择「搜索整个网络」
   - **语言**: 中文（简体）
3. 创建完成后，复制「搜索引擎 ID」（格式：`xxxxxxxxxxxxxxx:xxxxx`）

#### 4. 配置到项目

编辑 `src/config.py`，添加：

```python
# Google Custom Search API 配置
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', 'your_api_key_here')
GOOGLE_SEARCH_ENGINE_ID = os.getenv('GOOGLE_SEARCH_ENGINE_ID', 'your_search_engine_id_here')
```

或者设置环境变量：

```bash
# Windows PowerShell
$env:GOOGLE_API_KEY="your_api_key"
$env:GOOGLE_SEARCH_ENGINE_ID="your_search_engine_id"

# Linux/Mac
export GOOGLE_API_KEY="your_api_key"
export GOOGLE_SEARCH_ENGINE_ID="your_search_engine_id"
```

### 💰 费用说明

- **免费额度**: 100 次搜索/天
- **付费价格**: $5/1000 次查询（超出免费额度后）
- **计费方式**: 按实际调用次数计费

### 🔧 使用方法

```python
from src.utils.search_utils import google_search_api

# 基本调用
result = google_search_api("人工智能发展趋势", max_results=10)

# 在搜索流程中使用
result = search_if_needed(
    "[SEARCH: AI 技术应用]",
    providers=["google"]  # 会自动使用 API 方案
)
```

### ✅ 测试验证

```bash
# 运行 API 测试
python tests/test_google_api.py

# 预期输出：
# ✅ Google API 搜索成功！
# ✅ 推荐 | 速度: 0.xx秒 | 稳定性: 高
```

---

## 方案二：Playwright 爬虫（备选）

### ⚠️ 使用场景

- 海外服务器部署（无需代理）
- 已配置稳定代理的环境
- 不希望使用 API（避免配额限制）
- 需要爬取特定样式的搜索结果

### 🛠️ 配置要求

```bash
# 安装 Playwright
pip install playwright
playwright install chromium
```

### 🌐 代理配置

#### 方法1: 测试文件中配置

编辑 `tests/test_google_search.py`:

```python
# 取消注释并设置你的代理
PROXY = "http://127.0.0.1:7890"
```

#### 方法2: 代码中传入

```python
result = google_search_playwright(
    "查询内容",
    proxy="http://127.0.0.1:7890"
)
```

#### 方法3: 配置到 config.py

在 `src/config.py` 中添加：

```python
# Google 搜索代理配置（国内必需）
GOOGLE_SEARCH_PROXY = os.getenv('GOOGLE_SEARCH_PROXY', 'http://127.0.0.1:7890')
```

### 🚀 反检测增强

代码已包含以下反检测措施：

1. **浏览器指纹模拟**
   - 真实 User-Agent
   - 完整的浏览器环境参数
   - 窗口大小、设备类型等

2. **WebDriver 标志清除**
   - 删除 `navigator.webdriver` 标志
   - 修改 plugins、languages 等属性
   - 注入 Chrome runtime

3. **行为模拟**
   - 先访问 Google 首页建立 cookies
   - 随机延迟（1.5-3秒）
   - 模拟滚动行为

4. **网络优化**
   - 完整的 HTTP 头
   - Sec-Fetch-* 安全头
   - 正确的 Accept-Language

### 📊 测试结果

#### 无代理（国内）

```
状态: ❌ 失败
原因: Google 检测到异常流量，需要人机验证
建议: 配置代理或使用 API 方案
```

#### 有代理（国内）/ 海外服务器

```
状态: ✅ 成功（预期）
响应时间: 3-5 秒
结果质量: ⭐⭐⭐⭐⭐
```

---

## 两种方案对比

| 特性 | Google API ✅ | Playwright ⚠️ |
|-----|-------------|--------------|
| **访问性** | 国内可访问 | 国内需代理 |
| **速度** | ⭐⭐⭐⭐⭐ (1s) | ⭐⭐⭐ (3-5s) |
| **稳定性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **结果质量** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **维护成本** | 低 | 中（需应对反爬） |
| **费用** | $5/1000次 | 免费 |
| **免费额度** | 100次/天 | 无限制（受频率限制） |
| **配置难度** | 中 | 低（需代理） |
| **依赖** | 无 | Playwright + Chromium |

## 最佳实践

### 国内环境

**推荐方案**：Google Custom Search API

```python
# 1. 配置 API（一次性）
# 在 src/config.py 中添加 API Key 和 Search Engine ID

# 2. 使用统一搜索接口
result = search_if_needed(
    "[SEARCH: 查询内容]",
    providers=["google"]  # 自动使用 API 方案
)
```

**备选方案**：其他搜索引擎

```python
# 无需配置 API 的情况下
providers = ["yahoo", "mojeek", "bing"]
```

### 海外环境

**推荐方案**：直接使用 Playwright 或 API

```python
# 方案1: Playwright（无需代理）
result = google_search_playwright("query", max_results=10)

# 方案2: API（更快、更稳定）
result = google_search_api("query", max_results=10)
```

### 混合策略

在 `src/agents/langchain_agents.py` 中配置多引擎搜索：

```python
# 高质量需求（配置了 Google API）
providers = ["google", "yahoo", "bing"]

# 通用场景（国内无 API）
providers = ["yahoo", "mojeek", "bing"]

# 海外环境
providers = ["google_playwright", "bing", "yahoo"]
```

---

## 故障排除

### 问题1: "Playwright 未安装"

**解决**:
```bash
pip install playwright
playwright install chromium
```

### 问题2: "未配置 Google API"

**解决**:
1. 按照上述配置步骤获取 API Key 和 Search Engine ID
2. 在 `src/config.py` 中添加配置
3. 重启应用

### 问题3: "配额已用尽"

**原因**: 超过免费额度（100次/天）

**解决**:
1. 等待第二天重置（太平洋时间 00:00）
2. 升级到付费计划
3. 临时使用其他搜索引擎

### 问题4: "Google 检测到异常流量"（Playwright）

**原因**: 
- 国内 IP 直接访问 Google
- 未配置代理或代理失效

**解决**:
1. 配置代理：`proxy="http://127.0.0.1:7890"`
2. 切换到 API 方案（推荐）
3. 使用其他搜索引擎

### 问题5: "API 返回错误"

**常见错误码**:
- `403 Forbidden`: API Key 未正确配置或被限制
- `429 Too Many Requests`: 超过配额
- `400 Bad Request`: Search Engine ID 错误

**解决**:
1. 检查 API Key 和 Search Engine ID 是否正确
2. 确认 API 已启用
3. 检查 API Key 的限制设置

---

## 后续优化建议

### 已实现 ✅

- Google Custom Search API 集成
- Playwright 反检测增强
- 代理支持
- 多层次选择器
- 统一结果格式化
- 完整测试套件

### 可选增强 💡

1. **结果缓存**
   ```python
   # 缓存热门查询，减少 API 调用
   from functools import lru_cache
   
   @lru_cache(maxsize=100)
   def cached_google_search(query):
       return google_search_api(query)
   ```

2. **配额监控**
   ```python
   # 跟踪 API 使用量
   api_calls_today = 0
   MAX_DAILY_CALLS = 100
   
   if api_calls_today >= MAX_DAILY_CALLS:
       # 自动降级到 Playwright 或其他引擎
       return google_search_playwright(query)
   ```

3. **智能引擎选择**
   ```python
   # 根据查询类型选择最佳引擎
   def smart_search(query):
       if is_chinese(query):
           return baidu_search(query)  # 中文内容用百度
       elif has_api_quota():
           return google_search_api(query)  # 有配额用 Google API
       else:
           return yahoo_search(query)  # 默认 Yahoo
   ```

4. **并行多引擎**
   ```python
   # 同时查询多个引擎，取最佳结果
   with ThreadPoolExecutor() as executor:
       futures = [
           executor.submit(google_search_api, query),
           executor.submit(bing_search, query),
       ]
       results = [f.result() for f in futures]
   ```

---

## 总结

### ✅ 已完成

- ✅ Google Custom Search API 实现（推荐方案）
- ✅ Playwright 爬虫实现（备选方案）
- ✅ 反检测增强（WebDriver 标志清除、行为模拟）
- ✅ 代理支持
- ✅ 完整测试套件
- ✅ 详细配置文档

### 💡 推荐使用方式

| 场景 | 推荐方案 | 原因 |
|-----|---------|------|
| **国内生产环境** | Google API | 无需代理，稳定快速 |
| **海外服务器** | Google API 或 Playwright | 两者皆可，API 更快 |
| **开发测试** | 其他引擎（Yahoo/Mojeek） | 无需配置 |
| **高频调用** | API + 缓存 | 避免超过配额 |

### 📚 参考资源

- [Google Custom Search API 文档](https://developers.google.com/custom-search/v1/overview)
- [Playwright 文档](https://playwright.dev/python/)
- [配置示例](src/config_template.py)
- [测试文件](tests/test_google_api.py)

### 🔗 相关文件

- 核心实现: [src/utils/search_utils.py](../src/utils/search_utils.py)
- 配置模板: [src/config_template.py](../src/config_template.py)
- API 测试: [tests/test_google_api.py](../tests/test_google_api.py)
- Playwright 测试: [tests/test_google_search.py](../tests/test_google_search.py)


1. **不推荐使用 Google** （除非有稳定代理）
2. 推荐顺序：Yahoo → Mojeek → Bing → Baidu
3. Google 可作为高质量需求的备选（配置代理后）

### 海外环境

1. **首选 Google**（结果质量最高）
2. 备选：Bing → Yahoo → DuckDuckGo
3. 可配置 `SEARCH_PROVIDER="google"` 作为默认

### 混合策略

在 `src/agents/langchain_agents.py` 中配置：

```python
# 国内环境
providers = ["yahoo", "mojeek"]

# 海外环境
providers = ["google", "bing"]

# 高质量需求（配置代理）
providers = ["google", "yahoo", "bing"]
```

## 故障排除

### 问题1: "Playwright 未安装"

**解决**:
```bash
pip install playwright
playwright install chromium
```

### 问题2: "Google 检测到异常流量"

**原因**: 国内 IP 直接访问 Google

**解决**:
1. 配置代理（推荐）
2. 使用其他搜索引擎（Yahoo/Mojeek）

### 问题3: "搜索超时"

**原因**: 网络不稳定或代理失效

**解决**:
1. 检查代理连接
2. 增加重试次数：`max_retries=5`
3. 检查防火墙设置

### 问题4: "未找到结果"

**原因**: 
- 选择器失效（Google 更新 HTML 结构）
- 网络完全不可达

**解决**:
1. 更新选择器（查看最新 Google HTML）
2. 使用其他搜索引擎

## 后续优化

### 可选增强

1. **Cookie 复用**
   - 保存 Google Cookie 降低验证概率
   - 实现：使用 Playwright 的 `storageState`

2. **智能代理池**
   - 配置多个代理轮换
   - 检测代理可用性

3. **结果缓存**
   - 缓存热门查询结果
   - 减少重复请求

4. **Headful 模式**
   - 开发调试时显示浏览器窗口
   - 参数：`headless=False`

## 总结

✅ **已完成**:
- Playwright Google 搜索实现
- 多层次选择器和错误处理
- 代理支持
- 完整测试套件

⚠️ **使用限制**:
- 国内需要代理
- 性能开销较大
- 需要安装 Playwright

💡 **推荐场景**:
- 海外服务器部署
- 高质量搜索需求
- 配置了稳定代理的国内环境
