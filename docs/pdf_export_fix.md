# PDF导出功能修复说明

## 问题描述

原有的PDF导出使用 `html2canvas` + `jsPDF` 在客户端生成，存在以下问题：
1. **内容截断**：复杂布局在分页处可能被切断
2. **超链接失效**：PDF中的超链接被渲染为纯文本，无法点击
3. **质量有限**：基于Canvas截图，无法保留矢量图形

## 解决方案

采用 **Playwright** 浏览器自动化进行服务端PDF渲染：

### 优势
- ✅ 保留超链接和所有交互元素
- ✅ 智能分页，避免内容截断
- ✅ 高质量矢量渲染（类似浏览器"打印为PDF"）
- ✅ 支持复杂CSS样式和ECharts图表
- ✅ 自动回退到旧方案（Playwright未安装时）
- ✅ **自动展开所有折叠内容**（`.collapsed`、`details`、`.hidden`元素）并在导出后恢复原始状态

### 架构改动

#### 1. 新增模块：`src/utils/pdf_exporter.py`
```python
# 核心功能
generate_pdf_from_html(html_content, output_path)  # 从HTML字符串生成PDF
generate_pdf_from_file(html_file_path, output_path)  # 从HTML文件生成PDF
```

#### 2. 后端API：`src/web/app.py`
- `GET /api/pdf_available`: 检查Playwright是否可用
- `POST /api/export_pdf`: 接收HTML内容，返回PDF文件

#### 3. 前端逻辑：`src/web/templates/index.html`
```javascript
downloadPDF()  // 主入口，优先使用Playwright
  ├─ expandCollapsedContent() → 展开所有折叠元素
  ├─ /api/pdf_available → 检查后端能力
  ├─ 可用 → /api/export_pdf (高质量PDF)
  ├─ 不可用 → downloadPDFLegacy() (旧方案，显示警告)
  └─ restoreCollapsedContent() → 恢复折叠状态

downloadImage()  // 长图导出
  ├─ expandCollapsedContent() → 展开所有折叠元素
  ├─ html2canvas() → 渲染为图片
  └─ restoreCollapsedContent() → 恢复折叠状态
```

## 安装步骤

### 1. 安装Python依赖
```bash
pip install playwright
```

### 2. 安装浏览器内核
```bash
playwright install chromium
```
> Chromium浏览器约150MB，仅首次需要下载

### 3. 验证安装
访问 Web UI，点击"导出PDF"按钮：
- **成功**：显示 "✅ PDF已导出（高质量版本，保留超链接）"
- **回退**：显示警告提示安装Playwright

### 4. （可选）离线安装
如果服务器无外网，可在本地下载后手动安装：
```bash
# 本地机器下载
playwright install chromium --force

# 找到缓存目录（Windows: %USERPROFILE%\AppData\Local\ms-playwright\）
# 将浏览器文件复制到服务器同路径
```

## 使用说明

### Web界面
点击报告页面的"导出PDF"按钮，系统自动选择最佳方案。

### 命令行（用于批量处理）
```python
from src.utils.pdf_exporter import generate_pdf_from_file

# 从已生成的report.html创建PDF
success = generate_pdf_from_file(
    折叠内容自动展开

导出时自动处理三类折叠元素：

1. **CSS折叠** (`.collapsed`): 移除class，显示内容
2. **HTML Details**: 添加 `open` 属性展开
3. **隐藏元素** (`.hidden`): 移除class（排除脚本和样式）

```javascript
// 查找并展开所有折叠元素
const collapsedItems = doc.querySelectorAll('.collapsed');
const detailsElements = doc.querySelectorAll('details:not([open])');
const hiddenElements = doc.querySelectorAll('.hidden:not(script):not(style)');

// 导出完成后恢复原始状态
collapsedElements.forEach(item => {
    if (item.type === 'details') {
        item.elem.removeAttribute('open');
    } else if (item.type === 'hidden') {
        item.elem.classList.add('hidden');
    } else {
        item.classList.add('collapsed');
    }
});
```

### 'workspaces/20251230_123456/report.html',
    'output.pdf'
)
```

## 技术细节

### Playwright PDF选项
```python
{
    'format': 'A4',
    'print_background': True,  # 打印背景色
    'prefer_css_page_size': False,
    'margin': {'top': '20px', 'right': '20px', 'bottom': '20px', 'left': '20px'}
}
```

### ECharts图表等待
系统会等待ECharts实例渲染完成（最多15秒），确保图表完整导出：
```javascript
await page.wait_for_function(
    `() => {
        // 检查echarts库是否加载
        if (typeof echarts === 'undefined') return true;
        
        // 检查所有实例是否已渲染
        const instances = document.querySelectorAll('[_echarts_instance_]');
        for (let elem of instances) {
            const instance = echarts.getInstanceByDom(elem);
            if (!instance) continue;
            
            // 检查是否有canvas或svg内容
            const canvas = elem.querySelector('canvas');
            const svg = elem.querySelector('svg');
            if (!canvas && !svg) return false;
        }
        return true;
    }`
)
```

**ECharts内嵌优化**：为避免网络依赖，系统会自动：
1. 检测HTML中的ECharts CDN链接
2. 读取本地 `src/web/static/vendor/echarts.min.js`
3. 将脚本内容内嵌到HTML中（替换CDN链接）
4. 确保离线PDF中图表能正常渲染

**ECharts布局优化**：
- 注入CSS防止图表被分页截断（`page-break-inside: avoid`）
- 强制所有图表实例调用 `resize()` 确保尺寸正确
- 等待布局稳定（2秒）后再生成PDF
- 设置最小高度和边距避免重叠

```javascript
// 强制resize所有ECharts实例
instances.forEach(elem => {
    const instance = echarts.getInstanceByDom(elem);
    if (instance) {
        instance.resize();
        elem.style.pageBreakInside = 'avoid';
    }
});
```

### 超链接保留
Playwright原生支持超链接，生成的PDF中所有 `<a href="...">` 标签均可点击。

## 故障排查

### 问题1：Playwright安装失败
**症状**：`pip install playwright` 成功但 `playwright install` 超时

**解决**：
```bash
# 使用代理或国内镜像
set PLAYWRIGHT_DOWNLOAD_HOST=https://playwright.azureedge.net
playwright install chromium
```

### 问题2：Linux服务器缺少依赖
**症状**：`playwright install` 报错 "missing dependencies"

**解决**（Ubuntu/Debian）：
```bash
playwright install-deps chromium
```

### 问题3：PDF生成超时
**症状**：HTML内容复杂导致渲染超过60秒

**解决**：调整timeout参数
```python
generate_pdf_from_html(html, output, timeout=120000)  # 120秒
```

### 问题4：中文字体缺失
**症状**：PDF中中文显示为方块

**解决**：确保系统安装中文字体
```bash
# Linux
sudo apt-get install fonts-noto-cjk

# Windows（通常无需处理）
```

## 性能对比

| 指标 | jsPDF (旧) | Playwright (新) |
|------|-----------|----------------|
| 生成速度 | ~2-5秒 | ~5-10秒 |
| 文件大小 | 大（位图） | 小（矢量） |
| 超链接 | ❌ | ✅ |
| 内容截断 | 常见 | 罕见 |
| 安装复杂度 | 低 | 中 |

## 兼容性

- Python 3.9+
- Windows/Linux/macOS
- Playwright 1.40+
- 自动回退到jsPDF（无Playwright时）

## 未来优化方向

1. **并行导出**：支持多个报告同时生成PDF
2. **预设模板**：提供页眉页脚、水印等自定义选项
3. **PDF合并**：支持将多轮讨论报告合并为单个PDF
4. **书签导航**：为长报告自动生成章节书签

## 相关文件

- `src/utils/pdf_exporter.py`: PDF生成核心逻辑
- `src/web/app.py`: `/api/export_pdf` 和 `/api/pdf_available` 端点
- `src/web/templates/index.html`: `downloadPDF()` 和 `downloadPDFLegacy()` 函数
- `.github/copilot-instructions.md`: AI开发者文档更新
- `requirements.txt`: 添加 `playwright>=1.40.0` 依赖
