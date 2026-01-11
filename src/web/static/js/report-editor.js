/**
 * AICouncil 报告编辑器 - 交互式编辑功能
 * 版本: MVP v1.0
 * 功能: 文本编辑、保存/加载、版本历史
 */

class ReportEditor {
    constructor(workspaceId) {
        this.workspaceId = workspaceId;
        this.isEditMode = false;
        this.originalContent = null;
        this.autoSaveInterval = null;
        this.hasUnsavedChanges = false;
        
        // **新增检测**: 检测是否在iframe中（只有独立窗口才显示编辑器）
        const isInIframe = window.self !== window.top;
        console.log('[Editor] iframe检测:', {
            isInIframe: isInIframe,
            pathname: window.location.pathname,
            href: window.location.href
        });
        
        if (isInIframe) {
            console.log('[Editor] 报告在iframe中显示，编辑器功能已隐藏（请通过新窗口打开以使用编辑功能）');
            return;
        }
        
        // **方案C修复**: 检测全局禁用标志（由协议检测脚本设置）
        if (window.EDITOR_DISABLED) {
            console.warn('[Editor] 编辑器已被禁用（可能是通过 file:// 协议打开）');
            return;
        }
        
        // **核心修复**: 检测workspace_id是否有效
        if (!this.workspaceId || this.workspaceId === 'unknown') {
            console.error('[Editor] ❌ workspace_id 未识别 (当前值:', this.workspaceId, ')');
            this.showCriticalError();
            return;
        }
        
        console.log('[Editor] ✅ 初始化编辑器，workspace_id:', this.workspaceId);
        this.init();
    }
    
    showCriticalError() {
        // 禁用编辑按钮，并在 tooltip 中说明原因
        console.warn('[Editor] 编辑器不可用 - workspace_id 无效或通过本地文件打开');
        
        // 等待 DOM 加载完成后禁用按钮
        const disableEditButton = () => {
            const editBtn = document.getElementById('toggleEditMode');
            if (editBtn) {
                editBtn.disabled = true;
                editBtn.title = '⚠️ 无法使用编辑器\n报告必须通过 Flask 服务器访问才能编辑\n\n请访问: http://127.0.0.1:5000/report/' + this.extractSessionIdFromPath();
                editBtn.style.cursor = 'not-allowed';
                editBtn.style.opacity = '0.5';
            }
        };
        
        // 立即尝试禁用，并在 DOM 加载完成后再次尝试
        disableEditButton();
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', disableEditButton);
        } else {
            setTimeout(disableEditButton, 100);
        }
    }
    
    extractSessionIdFromPath() {
        // 尝试从文件路径中提取 session_id (例如: 20251229_210718_b206e1a2)
        const pathMatch = window.location.pathname.match(/(\d{8}_\d{6}_[a-f0-9]+)/);
        if (pathMatch) {
            return pathMatch[1];
        }
        
        // 尝试从 meta 标签提取
        const metaTag = document.querySelector('meta[name="workspace-id"]');
        if (metaTag) {
            return metaTag.getAttribute('content');
        }
        
        return 'YOUR_SESSION_ID';
    }
    
    init() {
        this.createToolbar();
        this.bindEvents();
        this.loadEditHistory();
        
        // 监听页面离开事件，防止未保存内容丢失
        window.addEventListener('beforeunload', (e) => {
            if (this.hasUnsavedChanges) {
                e.preventDefault();
                e.returnValue = '您有未保存的修改，确定要离开吗？';
                return e.returnValue;
            }
        });
    }
    
    createToolbar() {
        console.log('[Editor] 开始创建工具栏...');
        const toolbar = document.createElement('div');
        toolbar.id = 'editorToolbar';
        toolbar.className = 'editor-toolbar';
        toolbar.innerHTML = `
            <div class="toolbar-content">
                <button id="toggleEditMode" class="btn btn-primary" title="进入编辑模式">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                    </svg>
                    <span>编辑报告</span>
                </button>
                
                <button id="saveReport" class="btn btn-success" style="display:none;" title="保存修改">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                        <polyline points="17 21 17 13 7 13 7 21"></polyline>
                        <polyline points="7 3 7 8 15 8"></polyline>
                    </svg>
                    <span>保存</span>
                </button>
                
                <button id="cancelEdit" class="btn btn-secondary" style="display:none;" title="取消编辑">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                    <span>取消</span>
                </button>
                
                <button id="versionHistory" class="btn btn-info" title="查看版本历史">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <polyline points="12 6 12 12 16 14"></polyline>
                    </svg>
                    <span>版本历史</span>
                </button>
                
                <div class="download-dropdown-wrapper">
                    <button id="downloadReport" class="btn btn-success" title="下载报告">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                        <span>下载报告</span>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-left: 4px;">
                            <polyline points="6 9 12 15 18 9"></polyline>
                        </svg>
                    </button>
                    <div id="downloadDropdown" class="download-dropdown-menu">
                        <button class="download-option" data-format="html">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                <polyline points="14 2 14 8 20 8"></polyline>
                                <line x1="16" y1="13" x2="8" y2="13"></line>
                                <line x1="16" y1="17" x2="8" y2="17"></line>
                            </svg>
                            <span>HTML 格式</span>
                        </button>
                        <button class="download-option" data-format="pdf">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                <polyline points="14 2 14 8 20 8"></polyline>
                            </svg>
                            <span>PDF 格式</span>
                        </button>
                        <button class="download-option" data-format="image">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                                <circle cx="8.5" cy="8.5" r="1.5"></circle>
                                <polyline points="21 15 16 10 5 21"></polyline>
                            </svg>
                            <span>图片格式</span>
                        </button>
                        <button class="download-option" data-format="markdown">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                <polyline points="14 2 14 8 20 8"></polyline>
                            </svg>
                            <span>Markdown 格式</span>
                        </button>
                    </div>
                </div>
                
                <div class="toolbar-status" id="editorStatus">
                    <span class="status-indicator"></span>
                    <span class="status-text">查看模式</span>
                </div>
            </div>
        `;
        
        document.body.insertBefore(toolbar, document.body.firstChild);
        console.log('[Editor] ✅ 工具栏创建完成，已添加到DOM');
    }
    
    bindEvents() {
        console.log('[Editor] 开始绑定事件...');
        const toggleBtn = document.getElementById('toggleEditMode');
        const saveBtn = document.getElementById('saveReport');
        const cancelBtn = document.getElementById('cancelEdit');
        const historyBtn = document.getElementById('versionHistory');
        const downloadBtn = document.getElementById('downloadReport');
        
        console.log('[Editor] 找到的按钮:', {
            toggleBtn: !!toggleBtn,
            saveBtn: !!saveBtn,
            cancelBtn: !!cancelBtn,
            historyBtn: !!historyBtn,
            downloadBtn: !!downloadBtn
        });
        
        if (toggleBtn) toggleBtn.addEventListener('click', () => this.toggleEditMode());
        if (saveBtn) saveBtn.addEventListener('click', () => this.saveReport());
        if (cancelBtn) cancelBtn.addEventListener('click', () => this.cancelEdit());
        if (historyBtn) historyBtn.addEventListener('click', () => this.showVersionHistory());
        
        // 下载按钮和下拉菜单
        if (downloadBtn) {
            downloadBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleDownloadDropdown();
            });
        }
        
        // 下载选项点击事件
        const downloadOptions = document.querySelectorAll('.download-option');
        downloadOptions.forEach(option => {
            option.addEventListener('click', (e) => {
                e.stopPropagation();
                const format = option.dataset.format;
                this.downloadReport(format);
                this.toggleDownloadDropdown();
            });
        });
        
        // 点击外部关闭下拉菜单
        document.addEventListener('click', (e) => {
            const dropdown = document.getElementById('downloadDropdown');
            const downloadBtn = document.getElementById('downloadReport');
            if (dropdown && !dropdown.contains(e.target) && !downloadBtn.contains(e.target)) {
                dropdown.classList.remove('show');
            }
        });
        
        console.log('[Editor] ✅ 事件绑定完成');
        
        // 监听内容变化
        document.addEventListener('input', (e) => {
            if (this.isEditMode && e.target.hasAttribute('contenteditable')) {
                this.hasUnsavedChanges = true;
                this.updateStatus('未保存的修改', 'warning');
            }
        });
    }
    
    makeElementEditable(el) {
        // 跳过工具栏、脚本、样式等元素
        if (!el || el.id === 'editorToolbar' || 
            el.tagName === 'SCRIPT' || 
            el.tagName === 'STYLE') {
            return;
        }
        
        // 递归遍历所有子元素
        const makeTextEditable = (element) => {
            // 跳过已经处理过的元素
            if (element.hasAttribute('contenteditable')) {
                return;
            }
            
            // 跳过图表容器
            if (element.classList.contains('chart-container') || 
                element.classList.contains('references')) {
                return;
            }
            
            // 特殊处理 Mermaid SVG 容器（稍后特殊处理）
            if (element.classList.contains('mermaid') && element.querySelector('svg')) {
                this.makeMermaidEditable(element);
                return;
            }
            
            // 可编辑的文本元素
            const editableTagNames = ['P', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'LI', 'TD', 'TH', 'SPAN', 'DIV', 'BLOCKQUOTE'];
            
            if (editableTagNames.includes(element.tagName)) {
                // 检查是否有文本内容（排除只有子元素的容器）
                const hasDirectText = Array.from(element.childNodes).some(
                    node => node.nodeType === Node.TEXT_NODE && node.textContent.trim().length > 0
                );
                
                // 或者是叶子节点（没有子元素）
                const isLeafNode = element.children.length === 0;
                
                if ((hasDirectText || isLeafNode) && element.textContent.trim().length > 0) {
                    element.setAttribute('contenteditable', 'true');
                    element.classList.add('editable-active');
                    return; // 不继续递归子元素
                }
            }
            
            // 递归处理子元素
            Array.from(element.children).forEach(child => {
                makeTextEditable(child);
            });
        };
        
        makeTextEditable(el);
    }
    
    makeMermaidEditable(mermaidContainer) {
        // 保存原始 Mermaid 代码
        const svg = mermaidContainer.querySelector('svg');
        if (!svg) return;
        
        // 尝试从 data 属性或其他地方恢复源代码
        let sourceCode = mermaidContainer.getAttribute('data-mermaid-source');
        
        if (!sourceCode) {
            // 如果没有保存源代码，显示警告
            sourceCode = '// Mermaid 源代码不可用\n// 原图表已渲染，无法编辑';
        }
        
        // 添加双击编辑功能
        mermaidContainer.style.cursor = 'pointer';
        mermaidContainer.title = '双击编辑 Mermaid 源代码';
        
        mermaidContainer.addEventListener('dblclick', (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            // 创建编辑界面
            const editor = document.createElement('div');
            editor.className = 'mermaid-editor-popup';
            editor.innerHTML = `
                <div class="mermaid-editor-overlay" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 9999;">
                    <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 80%; max-width: 800px;">
                        <h3 style="margin: 0 0 15px 0; color: #1e293b;">编辑 Mermaid 图表源代码</h3>
                        <textarea class="mermaid-source" style="width: 100%; height: 300px; font-family: 'Courier New', monospace; font-size: 13px; padding: 10px; border: 1px solid #cbd5e1; border-radius: 4px; resize: vertical;">${sourceCode}</textarea>
                        <div style="margin-top: 15px; text-align: right;">
                            <button class="btn-cancel" style="padding: 8px 16px; margin-right: 10px; background: #e2e8f0; border: none; border-radius: 4px; cursor: pointer;">取消</button>
                            <button class="btn-save" style="padding: 8px 16px; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer;">保存</button>
                        </div>
                        <p style="margin: 10px 0 0 0; font-size: 12px; color: #64748b;">注意：保存后需要刷新页面才能看到新图表</p>
                    </div>
                </div>
            `;
            
            document.body.appendChild(editor);
            
            // 绑定事件
            editor.querySelector('.btn-cancel').addEventListener('click', () => {
                editor.remove();
            });
            
            editor.querySelector('.btn-save').addEventListener('click', () => {
                const newSource = editor.querySelector('.mermaid-source').value;
                mermaidContainer.setAttribute('data-mermaid-source', newSource);
                mermaidContainer.textContent = newSource; // 保存为文本
                mermaidContainer.classList.add('mermaid-source-edited');
                this.hasUnsavedChanges = true;
                this.showNotification('Mermaid 源代码已更新，保存后刷新页面查看效果', 'success');
                editor.remove();
            });
            
            editor.querySelector('.mermaid-editor-overlay').addEventListener('click', (e) => {
                if (e.target.classList.contains('mermaid-editor-overlay')) {
                    editor.remove();
                }
            });
        });
    }
    
    toggleEditMode() {
        console.log('[Editor] toggleEditMode 被调用，当前模式:', this.isEditMode ? '编辑' : '查看');
        if (this.isEditMode) {
            this.exitEditMode();
        } else {
            this.enterEditMode();
        }
    }
    
    enterEditMode() {
        console.log('[Editor] 进入编辑模式...');
        this.isEditMode = true;
        
        // **改进方案**: 处理body下所有非工具栏的顶级元素
        // 这样无论报告结构如何（.header + .container，还是单一.container），都能全部处理
        const bodyChildren = Array.from(document.body.children).filter(el =>
            el.id !== 'editorToolbar' &&
            !el.classList.contains('editor-toolbar') &&
            el.tagName !== 'SCRIPT' &&
            el.tagName !== 'STYLE'
        );
        
        console.log(`[Editor] 找到 ${bodyChildren.length} 个顶级内容元素`);
        
        // 保存原始内容（保存body副本用于取消）
        this.originalContent = document.body.cloneNode(true);
        
        // 处理所有顶级内容元素
        let processedCount = 0;
        let totalEditableCount = 0;
        
        bodyChildren.forEach((el, index) => {
            console.log(`[Editor] [${index}] 处理元素:`, el.tagName, el.className || '(无class)', `子元素: ${el.children.length}`);
            
            // 递归处理每个顶级元素的子元素
            Array.from(el.querySelectorAll('*')).forEach(child => {
                this.makeElementEditable(child);
            });
            // 也处理顶级元素自身
            this.makeElementEditable(el);
            
            processedCount++;
        });
        
        console.log(`[Editor] 共处理 ${processedCount} 个顶级元素`);
        
        // 统计实际被标记为可编辑的元素数量
        const editableElements = document.querySelectorAll('[contenteditable="true"]');
        console.log(`[Editor] 实际可编辑元素数量: ${editableElements.length}`);
        
        // 更新UI
        const toggleBtn = document.getElementById('toggleEditMode');
        const saveBtn = document.getElementById('saveReport');
        const cancelBtn = document.getElementById('cancelEdit');
        
        console.log('[Editor] 更新按钮显示状态...');
        if (toggleBtn) toggleBtn.style.display = 'none';
        if (saveBtn) saveBtn.style.display = 'inline-flex';
        if (cancelBtn) cancelBtn.style.display = 'inline-flex';
        
        document.body.classList.add('edit-mode-active');
        
        this.updateStatus('编辑模式', 'editing');
        this.showNotification('已进入编辑模式，可以直接点击文本进行编辑', 'info', 3000);
        console.log('[Editor] ✅ UI更新完成，已显示提示消息');
        
        // 启动自动保存（每60秒）
        this.autoSaveInterval = setInterval(() => this.autoSave(), 60000);
    }
    
    exitEditMode() {
        this.isEditMode = false;
        
        // 移除contenteditable属性
        const editableElements = document.querySelectorAll('[contenteditable="true"]');
        editableElements.forEach(el => {
            el.removeAttribute('contenteditable');
            el.classList.remove('editable-active');
        });
        
        // 更新UI
        document.getElementById('toggleEditMode').style.display = 'inline-flex';
        document.getElementById('saveReport').style.display = 'none';
        document.getElementById('cancelEdit').style.display = 'none';
        document.body.classList.remove('edit-mode-active');
        
        this.updateStatus('查看模式', 'view');
        this.hasUnsavedChanges = false;
        
        // 停止自动保存
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
            this.autoSaveInterval = null;
        }
    }
    
    cancelEdit() {
        if (this.hasUnsavedChanges) {
            if (!confirm('您有未保存的修改，确定要放弃吗？')) {
                return;
            }
        }
        
        // 恢复原始内容
        if (this.originalContent) {
            const container = document.querySelector('.container') || 
                             document.querySelector('main') || 
                             document.querySelector('body > div') ||
                             document.body;
            
            if (container && container.parentNode) {
                container.parentNode.replaceChild(this.originalContent, container);
            }
        }
        
        this.exitEditMode();
        this.showNotification('已取消编辑', 'info');
    }
    
    async saveReport() {
        const summary = prompt('请简要描述本次修改内容（可选）：');
        
        // 用户点击取消时，summary为null，直接返回不保存
        if (summary === null) {
            console.log('[Editor] 用户取消保存');
            return;
        }
        
        this.updateStatus('保存中...', 'saving');
        
        try {
            const reportData = this.extractReportData();
            reportData.metadata = {
                last_edited: new Date().toISOString(),
                edit_summary: summary || '用户手动编辑'
            };
            
            const response = await fetch(`/api/report/edit/${this.workspaceId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(reportData)
            });
            
            if (!response.ok) {
                throw new Error(`保存失败: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            this.hasUnsavedChanges = false;
            this.updateStatus('已保存', 'saved');
            this.showNotification(`保存成功！版本: ${result.version}`, 'success');
            
            // 3秒后退出编辑模式
            setTimeout(() => this.exitEditMode(), 3000);
            
        } catch (error) {
            console.error('保存报告失败:', error);
            this.updateStatus('保存失败', 'error');
            this.showNotification(`保存失败: ${error.message}`, 'error');
        }
    }
    
    async autoSave() {
        if (!this.hasUnsavedChanges) return;
        
        try {
            const reportData = this.extractReportData();
            reportData.metadata = {
                last_edited: new Date().toISOString(),
                edit_summary: '自动保存草稿',
                is_draft: true
            };
            
            const response = await fetch(`/api/report/draft/${this.workspaceId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(reportData)
            });
            
            if (response.ok) {
                console.log('自动保存成功');
                this.showNotification('已自动保存草稿', 'info', 2000);
            }
        } catch (error) {
            console.error('自动保存失败:', error);
        }
    }
    
    extractReportData() {
        // **关键修复**: 保存完整的HTML文档，但要移除编辑器工具栏
        
        // 1. 临时移除contenteditable属性，避免保存编辑状态
        const editableElements = document.querySelectorAll('[contenteditable="true"]');
        editableElements.forEach(el => {
            el.setAttribute('data-was-editable', 'true');
            el.removeAttribute('contenteditable');
            el.classList.remove('editable-active');
        });
        
        // 2. 临时移除编辑器工具栏（保存时不应包含）
        const toolbar = document.getElementById('editorToolbar');
        const toolbarParent = toolbar?.parentNode;
        const toolbarNextSibling = toolbar?.nextSibling;
        if (toolbar) {
            toolbar.remove();
        }
        
        // 3. 移除edit-mode-active类
        document.body.classList.remove('edit-mode-active');
        
        // 4. 获取完整的HTML文档
        const fullHtml = document.documentElement.outerHTML;
        
        // 5. 恢复工具栏
        if (toolbar && toolbarParent) {
            toolbarParent.insertBefore(toolbar, toolbarNextSibling);
        }
        
        // 6. 恢复edit-mode-active类
        document.body.classList.add('edit-mode-active');
        
        // 7. 恢复contenteditable属性
        document.querySelectorAll('[data-was-editable="true"]').forEach(el => {
            el.setAttribute('contenteditable', 'true');
            el.classList.add('editable-active');
            el.removeAttribute('data-was-editable');
        });
        
        // 提取章节和引用信息（用于元数据）
        const container = document.querySelector('.container') || 
                         document.querySelector('main') || 
                         document.body;
        
        const sections = [];
        const sectionCards = container.querySelectorAll('.card, [data-section-id], section, article');
        sectionCards.forEach((card, index) => {
            const title = card.querySelector('.section-title, h2, h1')?.textContent.trim() || '';
            sections.push({
                id: card.getAttribute('data-section-id') || `section-${index}`,
                title: title,
                order: index
            });
        });
        
        const citations = [];
        const citationItems = container.querySelectorAll('.ref-item, .citation-item');
        citationItems.forEach(item => {
            const num = item.querySelector('.ref-num')?.textContent.trim() || '';
            const title = item.querySelector('.ref-title')?.textContent.trim() || '';
            citations.push({ num, title });
        });
        
        return {
            html_content: fullHtml,
            sections: sections,
            citations: citations
        };
    }
    
    async loadEditHistory() {
        try {
            const response = await fetch(`/api/report/history/${this.workspaceId}`);
            if (response.ok) {
                this.editHistory = await response.json();
            }
        } catch (error) {
            console.error('加载编辑历史失败:', error);
        }
    }
    
    async showVersionHistory() {
        try {
            const response = await fetch(`/api/report/versions/${this.workspaceId}`);
            if (!response.ok) {
                throw new Error('获取版本历史失败');
            }
            
            const versions = await response.json();
            this.renderVersionHistoryModal(versions);
            
        } catch (error) {
            console.error('获取版本历史失败:', error);
            this.showNotification(`获取版本历史失败: ${error.message}`, 'error');
        }
    }
    
    renderVersionHistoryModal(versions) {
        // 移除旧的模态框
        const oldModal = document.getElementById('versionHistoryModal');
        if (oldModal) oldModal.remove();
        
        const modal = document.createElement('div');
        modal.id = 'versionHistoryModal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-overlay" onclick="document.getElementById('versionHistoryModal').remove()"></div>
            <div class="modal-content">
                <div class="modal-header">
                    <h3>版本历史</h3>
                    <button class="modal-close" onclick="document.getElementById('versionHistoryModal').remove()">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
                <div class="modal-body">
                    <div class="version-timeline">
                        ${this.renderVersionList(versions)}
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        modal.style.display = 'flex';
    }
    
    renderVersionList(versions) {
        if (!versions || versions.length === 0) {
            return '<p class="no-versions">暂无版本历史</p>';
        }
        
        return versions.map((version) => {
            const isCurrent = version.is_current === true;
            const isV0 = version.id === 'v0';
            
            return `
                <div class="version-item ${isCurrent ? 'current' : ''}">
                    <div class="version-header">
                        <span class="version-tag">
                            ${version.id}
                            ${isCurrent ? ' <span class="current-badge">当前版本</span>' : ''}
                            ${isV0 ? ' <span class="original-badge">原始</span>' : ''}
                        </span>
                        <span class="version-time">${this.formatDate(version.timestamp)}</span>
                    </div>
                    <div class="version-changes">
                        ${version.changes_summary || '无修改说明'}
                    </div>
                    ${!isCurrent ? `
                        <div class="version-actions">
                            <button onclick="reportEditor.previewVersion('${version.id}')" class="btn-small btn-secondary">
                                预览
                            </button>
                            <button onclick="reportEditor.restoreVersion('${version.id}')" class="btn-small btn-primary">
                                恢复此版本
                            </button>
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');
    }
    
    async previewVersion(versionId) {
        try {
            const response = await fetch(`/api/report/version/${this.workspaceId}/${versionId}`);
            if (!response.ok) {
                throw new Error('获取版本内容失败');
            }
            
            const versionHtml = await response.text();
            
            // 在新窗口打开预览
            const previewWindow = window.open('', '_blank');
            previewWindow.document.write(versionHtml);
            previewWindow.document.close();
            
        } catch (error) {
            console.error('预览版本失败:', error);
            this.showNotification(`预览失败: ${error.message}`, 'error');
        }
    }
    
    async restoreVersion(versionId) {
        if (!confirm(`确定要恢复到版本 ${versionId} 吗？当前未保存的修改将丢失。`)) {
            return;
        }
        
        try {
            const response = await fetch(`/api/report/restore/${this.workspaceId}/${versionId}`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                throw new Error('恢复版本失败');
            }
            
            this.showNotification('版本恢复成功，即将刷新页面...', 'success');
            
            // 关闭模态框并刷新页面
            document.getElementById('versionHistoryModal').remove();
            setTimeout(() => window.location.reload(), 2000);
            
        } catch (error) {
            console.error('恢复版本失败:', error);
            this.showNotification(`恢复失败: ${error.message}`, 'error');
        }
    }
    
    updateStatus(text, type) {
        const statusText = document.querySelector('.status-text');
        const statusIndicator = document.querySelector('.status-indicator');
        
        if (statusText) statusText.textContent = text;
        if (statusIndicator) {
            statusIndicator.className = 'status-indicator';
            statusIndicator.classList.add(`status-${type}`);
        }
    }
    
    showNotification(message, type = 'info', duration = 5000) {
        // 移除已存在的通知（包括正在淡出的）
        const existingNotifications = document.querySelectorAll('.notification');
        existingNotifications.forEach(n => {
            n.classList.remove('show');
            n.remove();
        });
        
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // 触发动画（确保DOM更新后再添加class）
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                notification.classList.add('show');
            });
        });
        
        // 自动关闭
        const closeTimeout = setTimeout(() => {
            notification.classList.remove('show');
            const removeTimeout = setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300);
            // 保存timeout ID以便可能的清理
            notification._removeTimeout = removeTimeout;
        }, duration);
        
        // 保存timeout ID以便可能的清理
        notification._closeTimeout = closeTimeout;
    }
    
    
    toggleDownloadDropdown() {
        const dropdown = document.getElementById('downloadDropdown');
        if (dropdown) {
            dropdown.classList.toggle('show');
        }
    }
    
    async downloadReport(format = 'html') {
        try {
            if (format === 'html') {
                this.downloadHTML();
            } else if (format === 'pdf') {
                await this.downloadPDF();
            } else if (format === 'image') {
                await this.downloadImage();
            } else if (format === 'markdown') {
                await this.downloadMarkdown();
            }
        } catch (error) {
            console.error('下载报告失败:', error);
            this.showNotification(`下载失败: ${error.message}`, 'error');
        }
    }
    
    downloadHTML() {
        try {
            // 临时移除编辑器工具栏
            const toolbar = document.getElementById('editorToolbar');
            const toolbarParent = toolbar ? toolbar.parentNode : null;
            const toolbarNextSibling = toolbar ? toolbar.nextSibling : null;
            
            if (toolbar) {
                toolbar.remove();
            }
            
            // 移除编辑模式类
            document.body.classList.remove('edit-mode-active');
            
            // 移除所有 contenteditable 属性
            const editableElements = document.querySelectorAll('[contenteditable="true"]');
            editableElements.forEach(el => {
                el.removeAttribute('contenteditable');
                el.classList.remove('editable');
            });
            
            // 获取完整的 HTML
            const fullHtml = document.documentElement.outerHTML;
            
            // 恢复工具栏
            if (toolbar && toolbarParent) {
                toolbarParent.insertBefore(toolbar, toolbarNextSibling);
            }
            
            // 恢复编辑状态
            if (this.isEditMode) {
                document.body.classList.add('edit-mode-active');
                editableElements.forEach(el => {
                    el.setAttribute('contenteditable', 'true');
                    el.classList.add('editable');
                });
            }
            
            // 创建 Blob 并下载
            const blob = new Blob([fullHtml], { type: 'text/html;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            // 生成文件名: report_工作区ID_时间戳.html
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
            a.download = `report_${this.workspaceId}_${timestamp}.html`;
            
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            this.showNotification('HTML报告下载成功', 'success', 3000);
            
        } catch (error) {
            console.error('下载HTML失败:', error);
            throw error;
        }
    }
    
    async downloadPDF() {
        const collapsedElements = [];
        let originalButtonText = '';
        
        try {
            // 展开所有折叠内容
            const collapsedItems = document.querySelectorAll('.collapsed');
            collapsedItems.forEach(elem => {
                collapsedElements.push(elem);
                elem.classList.remove('collapsed');
            });
            
            const detailsElements = document.querySelectorAll('details:not([open])');
            detailsElements.forEach(elem => {
                collapsedElements.push({ elem, type: 'details' });
                elem.setAttribute('open', '');
            });
            
            const hiddenElements = document.querySelectorAll('.hidden:not(script):not(style)');
            hiddenElements.forEach(elem => {
                if (elem.textContent.trim() || elem.querySelector('img, svg, canvas')) {
                    collapsedElements.push({ elem, type: 'hidden' });
                    elem.classList.remove('hidden');
                }
            });
            
            // 临时移除工具栏
            const toolbar = document.getElementById('editorToolbar');
            if (toolbar) toolbar.remove();
            
            // 移除编辑模式
            document.body.classList.remove('edit-mode-active');
            const editableElements = document.querySelectorAll('[contenteditable="true"]');
            editableElements.forEach(el => {
                el.removeAttribute('contenteditable');
                el.classList.remove('editable');
            });
            
            // 获取HTML内容
            let htmlContent = document.documentElement.outerHTML;
            
            // 替换相对路径为绝对URL
            htmlContent = htmlContent.replace(/src="\/static\//g, 'src="http://127.0.0.1:5000/static/');
            htmlContent = htmlContent.replace(/href="\/static\//g, 'href="http://127.0.0.1:5000/static/');
            
            this.showNotification('正在生成PDF，请稍候...', 'info', 2000);
            
            // 调用后端API生成PDF
            const response = await fetch('/api/export_pdf', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    html: htmlContent,
                    filename: `report_${this.workspaceId}_${new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)}.pdf`
                })
            });
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `report_${this.workspaceId}_${new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)}.pdf`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                this.showNotification('✅ PDF已导出（高质量版本）', 'success', 3000);
            } else {
                const errorData = await response.json();
                throw new Error(errorData.message || 'PDF生成失败');
            }
            
        } catch (error) {
            console.error('PDF导出失败:', error);
            this.showNotification(`PDF导出失败: ${error.message}`, 'error');
            throw error;
        } finally {
            // 恢复折叠状态
            collapsedElements.forEach(item => {
                if (item.type === 'details') {
                    item.elem.removeAttribute('open');
                } else if (item.type === 'hidden') {
                    item.elem.classList.add('hidden');
                } else if (item.classList) {
                    item.classList.add('collapsed');
                }
            });
            
            // 恢复工具栏和编辑状态
            if (!document.getElementById('editorToolbar')) {
                this.createToolbar();
                this.bindEvents();
            }
        }
    }
    
    async downloadImage() {
        if (!window.html2canvas) {
            this.showNotification('图片导出功能需要加载 html2canvas 库', 'error');
            return;
        }
        
        const collapsedElements = [];
        
        try {
            this.showNotification('正在生成图片，请稍候...', 'info', 2000);
            
            // 展开所有折叠内容
            const collapsedItems = document.querySelectorAll('.collapsed');
            collapsedItems.forEach(elem => {
                collapsedElements.push(elem);
                elem.classList.remove('collapsed');
            });
            
            const detailsElements = document.querySelectorAll('details:not([open])');
            detailsElements.forEach(elem => {
                collapsedElements.push({ elem, type: 'details' });
                elem.setAttribute('open', '');
            });
            
            const hiddenElements = document.querySelectorAll('.hidden:not(script):not(style)');
            hiddenElements.forEach(elem => {
                if (elem.textContent.trim() || elem.querySelector('img, svg, canvas')) {
                    collapsedElements.push({ elem, type: 'hidden' });
                    elem.classList.remove('hidden');
                }
            });
            
            // 临时移除工具栏
            const toolbar = document.getElementById('editorToolbar');
            if (toolbar) toolbar.style.display = 'none';
            
            await new Promise(resolve => setTimeout(resolve, 300));
            
            const canvas = await html2canvas(document.body, {
                useCORS: true,
                allowTaint: true,
                backgroundColor: '#ffffff',
                scale: 2
            });
            
            if (toolbar) toolbar.style.display = '';
            
            const url = canvas.toDataURL('image/png');
            const a = document.createElement('a');
            a.download = `report_${this.workspaceId}_${new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)}.png`;
            a.href = url;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            
            this.showNotification('图片下载成功', 'success', 3000);
            
        } catch (error) {
            console.error('图片导出失败:', error);
            this.showNotification(`图片导出失败: ${error.message}`, 'error');
            throw error;
        } finally {
            // 恢复折叠状态
            collapsedElements.forEach(item => {
                if (item.type === 'details') {
                    item.elem.removeAttribute('open');
                } else if (item.type === 'hidden') {
                    item.elem.classList.add('hidden');
                } else if (item.classList) {
                    item.classList.add('collapsed');
                }
            });
        }
    }
    
    async downloadMarkdown() {
        try {
            this.showNotification('正在转换为Markdown格式...', 'info', 2000);
            
            // 临时移除工具栏
            const toolbar = document.getElementById('editorToolbar');
            if (toolbar) toolbar.remove();
            
            // 移除编辑模式
            document.body.classList.remove('edit-mode-active');
            const editableElements = document.querySelectorAll('[contenteditable="true"]');
            editableElements.forEach(el => {
                el.removeAttribute('contenteditable');
                el.classList.remove('editable');
            });
            
            const htmlContent = document.documentElement.outerHTML;
            
            const response = await fetch('/api/export_md', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    html: htmlContent,
                    filename: `report_${this.workspaceId}_${new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)}.md`
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || 'Markdown导出失败');
            }
            
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `report_${this.workspaceId}_${new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)}.md`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            this.showNotification('Markdown格式导出成功', 'success', 3000);
            
        } catch (error) {
            console.error('Markdown导出失败:', error);
            this.showNotification(`Markdown导出失败: ${error.message}`, 'error');
            throw error;
        } finally {
            // 恢复工具栏和编辑状态
            if (!document.getElementById('editorToolbar')) {
                this.createToolbar();
                this.bindEvents();
            }
        }
    }
    
    formatDate(timestamp) {
        if (!timestamp) return '未知时间';
        
        const date = new Date(timestamp);
        
        // 检查日期是否有效
        if (isNaN(date.getTime())) {
            // 尝试解析旧格式 (YYYYMMDD_HHMMSS)
            const match = String(timestamp).match(/^(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})$/);
            if (match) {
                const [, year, month, day, hour, minute, second] = match;
                return `${year}-${month}-${day} ${hour}:${minute}`;
            }
            return '无效日期';
        }
        
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}

// 页面加载完成后初始化编辑器
document.addEventListener('DOMContentLoaded', function() {
    // 从 URL 或页面元数据中获取 workspace_id
    let workspaceId = null;
    
    // 方法 1: 从 URL 获取（格式: /report/{workspace_id} 或 report.html?workspace={workspace_id}）
    const urlParams = new URLSearchParams(window.location.search);
    workspaceId = urlParams.get('workspace') || urlParams.get('session');
    
    if (!workspaceId) {
        const pathParts = window.location.pathname.split('/');
        const reportIndex = pathParts.indexOf('report');
        if (reportIndex >= 0 && pathParts[reportIndex + 1]) {
            workspaceId = pathParts[reportIndex + 1].replace('.html', '');
        }
    }
    
    // 方法 2: 从文件路径推断（本地文件打开的情况）
    if (!workspaceId && window.location.protocol === 'file:') {
        const filePath = window.location.pathname;
        const match = filePath.match(/workspaces[\/\\]([^\/\\]+)[\/\\]/);
        if (match && match[1]) {
            workspaceId = match[1];
        }
    }
    
    // 方法 3: 从页面元数据获取
    if (!workspaceId) {
        const metaWorkspace = document.querySelector('meta[name="workspace-id"]');
        if (metaWorkspace) {
            workspaceId = metaWorkspace.getAttribute('content');
        }
    }
    
    if (workspaceId) {
        console.log('[Editor] 初始化编辑器，workspace:', workspaceId);
        window.reportEditor = new ReportEditor(workspaceId);
    } else {
        console.warn('[Editor] 无法确定 workspace ID，编辑功能可能受限');
        // 即使没有 workspace ID 也初始化编辑器（仅支持本地编辑）
        window.reportEditor = new ReportEditor('unknown');
    }
});
