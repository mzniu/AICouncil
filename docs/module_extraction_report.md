# 模块提取完成报告

## 📦 新增模块

### 1. history.js - 历史记录管理模块
**路径**: `src/web/static/js/modules/history.js`

**功能**:
- ✅ `toggleHistoryModal()` - 切换历史模态框显示/隐藏
- ✅ `renderHistoryList(workspaces)` - 渲染历史列表HTML
- ✅ `loadWorkspace(sessionId)` - 加载历史工作区
- ✅ `deleteHistory(event, sessionId)` - 删除历史记录
- ✅ `viewHistoryDetails(workspaceId)` - 查看历史详情（预留）

**依赖**:
```javascript
import { showAlert, showConfirm, formatDate } from '../core/utils.js';
import { getWorkspaces, deleteWorkspace, loadWorkspace } from '../core/api.js';
import { state } from '../core/state.js';

// 使用全局t()函数（定义在index.html中）
const t = window.t || ((key) => key);
```

**代码统计**:
- 总行数: ~160行
- 函数数: 5个
- JSDoc覆盖率: 100%

---

### 2. export.js - 报告导出模块
**路径**: `src/web/static/js/modules/export.js`

**功能**:
- ✅ `initExportModule(iframe)` - 初始化模块（设置reportIframe引用）
- ✅ `toggleDownloadDropdown()` - 切换下载下拉菜单
- ✅ `exportAsHTML()` - 导出HTML文件
- ✅ `exportAsMarkdown(e)` - 导出Markdown（服务器端转换）
- ✅ `exportAsPDF(e)` - 导出PDF（Playwright优先，降级到jsPDF）
- ✅ `exportAsScreenshot(e)` - 导出PNG长图
- ✅ `downloadFile(blob, filename)` - 通用下载辅助函数
- ✅ `expandCollapsedElements(doc)` - 展开折叠元素（私有）
- ✅ `restoreCollapsedElements(elements)` - 恢复折叠状态（私有）
- ✅ `exportAsPDFLegacy()` - 旧版PDF导出（私有）

**依赖**:
```javascript
import { exportMarkdown, exportPdf } from '../core/api.js';
import { showAlert } from '../core/utils.js';

// 使用全局t()函数（定义在index.html中）
const t = window.t || ((key) => key);
```

**外部库依赖**:
- `html2canvas` (全局) - 用于截图和旧版PDF
- `jspdf` (全局) - 用于旧版PDF生成

**代码统计**:
- 总行数: ~370行
- 函数数: 10个（含3个私有函数）
- JSDoc覆盖率: 100%

---

## 🔧 集成说明

### 在 index.html 中引入模块

需要在 `<script type="module">` 标签中引入：

```javascript
import * as historyModule from './static/js/modules/history.js';
import * as exportModule from './static/js/modules/export.js';

// 初始化导出模块
exportModule.initExportModule(document.getElementById('report-iframe'));

// 挂载到全局命名空间（供HTML内联事件调用）
window.aiCouncil = window.aiCouncil || {};
window.aiCouncil.history = historyModule;
window.aiCouncil.export = exportModule;
```

### 修改HTML事件绑定

#### 历史记录按钮
```html
<!-- 旧版 -->
<button onclick="toggleHistoryModal()">历史</button>

<!-- 新版 -->
<button onclick="window.aiCouncil.history.toggleHistoryModal()">历史</button>
```

#### 导出按钮
```html
<!-- 旧版 -->
<button onclick="downloadReport()">HTML</button>
<button onclick="downloadPDF(event)">PDF</button>
<button onclick="downloadMarkdown(event)">Markdown</button>
<button onclick="downloadImage(event)">图片</button>

<!-- 新版 -->
<button onclick="window.aiCouncil.export.exportAsHTML()">HTML</button>
<button onclick="window.aiCouncil.export.exportAsPDF(event)">PDF</button>
<button onclick="window.aiCouncil.export.exportAsMarkdown(event)">Markdown</button>
<button onclick="window.aiCouncil.export.exportAsScreenshot(event)">图片</button>
```

#### 删除历史记录（在动态生成的HTML中）
```javascript
// 在 renderHistoryList() 中已自动处理
`<button onclick="window.aiCouncil.history.deleteHistory(event, '${ws.id}')">`
```

---

## ⚠️ 注意事项

### 1. 模块初始化顺序
必须先加载 `core/` 模块，再加载 `modules/`：
```javascript
// 1. 先加载核心模块
import { state } from './static/js/core/state.js';
import { showAlert } from './static/js/core/utils.js';
import * as api from './static/js/core/api.js';

// 2. 再加载功能模块
import * as historyModule from './static/js/modules/history.js';
import * as exportModule from './static/js/modules/export.js';
```

### 2. export.js 需要初始化
```javascript
// 必须调用一次，传入reportIframe元素
exportModule.initExportModule(document.getElementById('report-iframe'));
```和函数依赖
确保在模块加载前已引入和定义：
```html
<!-- 外部库 -->
<script src="/static/vendor/html2canvas.min.js"></script>
<script src="/static/vendor/jspdf.umd.min.js"></script>

<!-- 全局函数（在index.html中定义） -->
<script>
    // translations对象和currentLang变量
    const translations = { zh: {...}, en: {...} };
    let currentLang = 'zh';
    
    // t()函数
    function t(key) {
        return translations[currentLang][key] || key;
    }
    
    // 确保全局可访问
    window.t = t;

<script src="/static/vendor/html2canvas.min.js"></script>
<script src="/static/vendor/jspdf.umd.min.js"></script>
```

### 4. fetchUpdates 函数引用
history.js 中调用了 `window.aiCouncil.core.fetchUpdates()`，需要确保该函数已挂载到全局。

---

## 🎯 后续TODO

### 短期（必需）
- [ ] 在 index.html 中引入这两个模块
- [ ] 修改所有HTML内联事件调用路径
- [ ] 测试所有导出功能（HTML/PDF/PNG/Markdown）
- [ ] 测试历史记录加载/删除

### 中期（优化）
- [ ] 移除 index.html 中的重复代码
- [ ] 为 `viewHistoryDetails()` 实现完整逻辑
- [ ] 添加导出进度条（大文件导出时）
- [ ] 支持批量删除历史记录

### 长期（增强）
- [ ] 添加历史记录搜索功能
- [ ] 支持导出为Word (.docx)
- [ ] 添加云端备份功能

---

## 📊 代码质量

### JSDoc覆盖率
- ✅ history.js: 100% (5/5 函数)
- ✅ export.js: 100% (10/10 函数)

### ES6模块化
- ✅ 使用 `import/export` 语法
- ✅ 避免全局变量污染
- ✅ 支持按需引入

### 错误处理
- ✅ 所有异步函数使用 try-catch
- ✅ 用户友好的错误提示
- ✅ 控制台错误日志

### 兼容性
- ✅ 兼容旧版函数名（`downloadReport` → `exportAsHTML`）
- ✅ 降级策略（Playwright → jsPDF → html2canvas）
- ✅ 折叠状态保护（导出时展开，完成后恢复）

---

## 📝 使用示例

### 导出HTML
```javascript
import { exportAsHTML } from './modules/export.js';

// 直接调用
exportAsHTML();
```

### 加载历史
```javascript
import { loadWorkspace } from './modules/history.js';

// 传入workspace ID
await loadWorkspace('20240114_abc123');
```

### 批量导出
```javascript
import * as exportModule from './modules/export.js';

async function exportAll() {
    await exportModule.exportAsHTML();
    await exportModule.exportAsMarkdown();
    await exportModule.exportAsPDF();
}
```

---

## ✅ 测试清单

### 历史记录模块
- [ ] 打开历史模态框
- [ ] 显示工作区列表
- [ ] 点击加载历史工作区
- [ ] 删除历史记录
- [ ] 空列表提示
- [ ] 加载失败提示

### 导出模块
- [ ] HTML导出
- [ ] Markdown导出（服务器端）
- [ ] PDF导出（Playwright）
- [ ] PDF导出（jsPDF降级）
- [ ] PNG截图导出
- [ ] 折叠元素展开/恢复
- [ ] ECharts图表渲染
- [ ] 下载下拉菜单切换

---

**生成时间**: 2026-01-14  
**模块版本**: v1.0.0  
**提取自**: src/web/templates/index.html (6230行)
