# 模块集成快速指南

## 🚀 集成步骤

### 步骤1：在 index.html 中添加模块引入

在 `<script>` 部分的最后（DOMContentLoaded 之前），添加：

```javascript
// ==================== 导入ES6模块 ====================
import * as historyModule from './static/js/modules/history.js';
import * as exportModule from './static/js/modules/export.js';

// ==================== 初始化模块 ====================
// 初始化导出模块（传入reportIframe引用）
const reportIframe = document.getElementById('report-iframe');
exportModule.initExportModule(reportIframe);

// ==================== 挂载到全局命名空间 ====================
window.aiCouncil = window.aiCouncil || {};
window.aiCouncil.history = historyModule;
window.aiCouncil.export = exportModule;

// ==================== 兼容旧版全局函数 ====================
// 为HTML内联事件提供兼容
window.toggleHistoryModal = historyModule.toggleHistoryModal;
window.loadWorkspace = historyModule.loadWorkspace;
window.deleteWorkspace = historyModule.deleteHistory;

window.downloadReport = exportModule.exportAsHTML;
window.downloadMarkdown = exportModule.exportAsMarkdown;
window.downloadPDF = exportModule.exportAsPDF;
window.downloadImage = exportModule.exportAsScreenshot;
window.toggleDownloadDropdown = exportModule.toggleDownloadDropdown;
```

### 步骤2：确保 t() 函数全局可访问

在 translations 定义之后，添加：

```javascript
// 确保t()函数全局可访问（供ES6模块使用）
window.t = t;
```

### 步骤3：修改HTML按钮事件（可选）

如果想使用命名空间调用，可以修改：

```html
<!-- 历史按钮 -->
<button onclick="window.aiCouncil.history.toggleHistoryModal()">
    历史
</button>

<!-- 导出按钮 -->
<button onclick="window.aiCouncil.export.exportAsHTML()">
    下载HTML
</button>
<button onclick="window.aiCouncil.export.exportAsPDF(event)">
    下载PDF
</button>
```

**注意**：如果不修改HTML，旧的函数名（如 `toggleHistoryModal()`）仍然可用（通过兼容层）。

---

## ✅ 完整示例代码

在 index.html 的 `<script>` 标签内：

```javascript
<script type="module">
    // ==================== 翻译配置 ====================
    const translations = {
        zh: { /* ... */ },
        en: { /* ... */ }
    };
    let currentLang = 'zh';
    
    function t(key) {
        return translations[currentLang][key] || key;
    }
    
    // 全局暴露t()函数
    window.t = t;
    
    // ==================== 导入ES6模块 ====================
    import * as historyModule from './static/js/modules/history.js';
    import * as exportModule from './static/js/modules/export.js';
    
    // ==================== 初始化 ====================
    document.addEventListener('DOMContentLoaded', () => {
        // 初始化导出模块
        const reportIframe = document.getElementById('report-iframe');
        exportModule.initExportModule(reportIframe);
        
        // 挂载到全局
        window.aiCouncil = {
            history: historyModule,
            export: exportModule
        };
        
        // 兼容旧版（如果HTML未修改）
        window.toggleHistoryModal = historyModule.toggleHistoryModal;
        window.downloadReport = exportModule.exportAsHTML;
        window.downloadPDF = exportModule.exportAsPDF;
        window.downloadMarkdown = exportModule.exportAsMarkdown;
        window.downloadImage = exportModule.exportAsScreenshot;
        window.toggleDownloadDropdown = exportModule.toggleDownloadDropdown;
        
        // ... 其他初始化代码 ...
    });
</script>
```

---

## 🧪 测试清单

### 历史记录测试
```bash
# 1. 打开浏览器控制台
window.aiCouncil.history.toggleHistoryModal()

# 2. 检查是否显示模态框
# 3. 点击历史记录，检查是否加载成功
# 4. 点击删除按钮，检查是否删除成功
```

### 导出功能测试
```bash
# 1. 确保报告已生成
# 2. 测试HTML导出
window.aiCouncil.export.exportAsHTML()

# 3. 测试PDF导出
window.aiCouncil.export.exportAsPDF({ currentTarget: null })

# 4. 测试Markdown导出
window.aiCouncil.export.exportAsMarkdown({ target: null })

# 5. 测试截图导出
window.aiCouncil.export.exportAsScreenshot({ currentTarget: null })
```

---

## ⚠️ 常见问题

### Q1: 报错 "Cannot find module './core/i18n.js'"
**解决方案**: 确保已移除 `import { t } from '../core/i18n.js'`，改为使用 `const t = window.t`。

### Q2: 报错 "t is not a function"
**解决方案**: 确保在模块加载前已定义 `window.t = t`。

### Q3: 报错 "reportIframe is null"
**解决方案**: 确保调用了 `exportModule.initExportModule(iframe)`。

### Q4: 历史记录加载后讨论流不更新
**解决方案**: 确保 `window.aiCouncil.core.fetchUpdates` 已定义并可调用。

### Q5: 导出PDF时图表消失
**解决方案**: 检查 ECharts 库路径是否正确（应使用本地路径 `/static/vendor/echarts.min.js`）。

---

## 📦 文件结构

```
src/web/static/js/
├── core/                      # 核心模块（已存在）
│   ├── state.js              # 全局状态管理
│   ├── api.js                # API调用封装（已更新，新增loadWorkspace）
│   └── utils.js              # 工具函数
└── modules/                   # 功能模块（新增）
    ├── history.js            # 历史记录管理
    └── export.js             # 报告导出
```

---

## 🎯 下一步

1. **在 index.html 中集成模块** - 按照步骤1-3操作
2. **测试所有功能** - 使用测试清单验证
3. **移除重复代码** - 删除 index.html 中已提取的函数
4. **提交代码** - 使用有意义的commit信息

**建议commit信息**:
```bash
git commit -m "refactor: 提取history和export模块

- history.js: 历史记录管理（加载/删除/查看）
- export.js: 报告导出（HTML/PDF/PNG/Markdown）
- 更新api.js: 新增loadWorkspace函数
- 完整JSDoc注释和错误处理
- 支持降级策略（Playwright → jsPDF）"
```

---

**最后更新**: 2026-01-14  
**文档版本**: v1.1
