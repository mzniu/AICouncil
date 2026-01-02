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
        // 显示醒目的错误提示
        const errorBanner = document.createElement('div');
        errorBanner.className = 'critical-error-banner';
        errorBanner.innerHTML = `
            <div class="error-content">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="8" x2="12" y2="12"></line>
                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
                <div>
                    <h3>⚠️ 无法使用编辑器</h3>
                    <p>报告必须通过 Flask 服务器访问才能编辑。</p>
                    <p><strong>正确方式</strong>: 访问 <code>http://127.0.0.1:5000/report/${this.extractSessionIdFromPath()}</code></p>
                    <p><strong>错误方式</strong>: 直接打开本地 HTML 文件 (file:///...)</p>
                </div>
            </div>
        `;
        document.body.insertBefore(errorBanner, document.body.firstChild);
        
        // 添加错误样式
        const style = document.createElement('style');
        style.textContent = `
            .critical-error-banner {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
                color: white;
                padding: 20px;
                z-index: 10000;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            }
            .critical-error-banner .error-content {
                display: flex;
                align-items: flex-start;
                gap: 16px;
                max-width: 1200px;
                margin: 0 auto;
            }
            .critical-error-banner svg {
                flex-shrink: 0;
                margin-top: 4px;
            }
            .critical-error-banner h3 {
                margin: 0 0 8px 0;
                font-size: 18px;
            }
            .critical-error-banner p {
                margin: 4px 0;
                font-size: 14px;
            }
            .critical-error-banner code {
                background: rgba(255,255,255,0.2);
                padding: 2px 8px;
                border-radius: 4px;
                font-family: monospace;
            }
        `;
        document.head.appendChild(style);
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
                
                <div class="toolbar-status" id="editorStatus">
                    <span class="status-indicator"></span>
                    <span class="status-text">查看模式</span>
                </div>
            </div>
        `;
        
        document.body.insertBefore(toolbar, document.body.firstChild);
    }
    
    bindEvents() {
        document.getElementById('toggleEditMode').addEventListener('click', () => this.toggleEditMode());
        document.getElementById('saveReport').addEventListener('click', () => this.saveReport());
        document.getElementById('cancelEdit').addEventListener('click', () => this.cancelEdit());
        document.getElementById('versionHistory').addEventListener('click', () => this.showVersionHistory());
        
        // 监听内容变化
        document.addEventListener('input', (e) => {
            if (this.isEditMode && e.target.hasAttribute('contenteditable')) {
                this.hasUnsavedChanges = true;
                this.updateStatus('未保存的修改', 'warning');
            }
        });
    }
    
    makeElementEditable(el) {
        // 跳过图表容器、引用列表和脚本标签
        if (el.querySelector('.chart-container') || 
            el.classList.contains('references') ||
            el.tagName === 'SCRIPT' ||
            el.tagName === 'STYLE') {
            return;
        }
        
        // 查找所有文本元素
        const textElements = el.querySelectorAll('p, h1, h2, h3, h4, h5, h6, li, .data-point, .methodology-note, div:not(:has(*))');
        
        if (textElements.length > 0) {
            textElements.forEach(textEl => {
                // 确保元素有实际文本内容
                if (textEl.textContent.trim().length > 0) {
                    textEl.setAttribute('contenteditable', 'true');
                    textEl.classList.add('editable-active');
                }
            });
        } else {
            // 如果没有找到子元素，尝试直接编辑该元素
            if (el.textContent.trim().length > 0 && !el.querySelector('*')) {
                el.setAttribute('contenteditable', 'true');
                el.classList.add('editable-active');
            }
        }
    }
    
    toggleEditMode() {
        if (this.isEditMode) {
            this.exitEditMode();
        } else {
            this.enterEditMode();
        }
    }
    
    enterEditMode() {
        this.isEditMode = true;
        
        // 查找主容器，支持多种可能的选择器
        const mainContainer = document.querySelector('.container') || 
                             document.querySelector('main') || 
                             document.querySelector('body > div') ||
                             document.body;
        
        if (!mainContainer) {
            console.error('[Editor] 找不到主容器元素');
            this.showNotification('无法进入编辑模式：找不到报告容器', 'error');
            return;
        }
        
        this.originalContent = mainContainer.cloneNode(true);
        
        // 为可编辑区域添加contenteditable属性
        const editableElements = document.querySelectorAll('.card, .executive-summary-card, [data-section-id]');
        
        if (editableElements.length === 0) {
            console.warn('[Editor] 未找到可编辑的卡片元素，尝试使用通用选择器');
            // 如果没有找到标准的卡片元素，尝试找其他可编辑内容
            const fallbackElements = document.querySelectorAll('section, article, .content, main > div');
            fallbackElements.forEach(el => {
                this.makeElementEditable(el);
            });
        } else {
            editableElements.forEach(el => {
                this.makeElementEditable(el);
            });
        }
        
        // 更新UI
        document.getElementById('toggleEditMode').style.display = 'none';
        document.getElementById('saveReport').style.display = 'inline-flex';
        document.getElementById('cancelEdit').style.display = 'inline-flex';
        document.body.classList.add('edit-mode-active');
        
        this.updateStatus('编辑模式', 'editing');
        this.showNotification('已进入编辑模式，可以直接点击文本进行编辑', 'info');
        
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
        const container = document.querySelector('.container') || 
                         document.querySelector('main') || 
                         document.querySelector('body > div') ||
                         document.body;
        
        if (!container) {
            console.error('[Editor] 无法提取报告数据：找不到容器');
            return {
                html_content: document.body.innerHTML,
                sections: [],
                citations: []
            };
        }
        
        // 提取章节内容
        const sections = [];
        const sectionCards = container.querySelectorAll('.card, [data-section-id], section, article');
        sectionCards.forEach((card, index) => {
            const title = card.querySelector('.section-title, h2, h1')?.textContent.trim() || '';
            const content = card.innerHTML;
            
            sections.push({
                id: card.getAttribute('data-section-id') || `section-${index}`,
                title: title,
                content: content,
                order: index
            });
        });
        
        // 提取引用列表
        const citations = [];
        const citationItems = container.querySelectorAll('.ref-item, .citation-item');
        citationItems.forEach(item => {
            const num = item.querySelector('.ref-num')?.textContent.trim() || '';
            const title = item.querySelector('.ref-title')?.textContent.trim() || '';
            const link = item.querySelector('.ref-link, a')?.getAttribute('href') || '';
            const source = item.querySelector('.ref-source')?.textContent.trim() || '';
            
            citations.push({
                num: num,
                title: title,
                url: link,
                source: source
            });
        });
        
        return {
            html_content: container.innerHTML,
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
        
        return versions.map((version, index) => `
            <div class="version-item ${index === 0 ? 'current' : ''}">
                <div class="version-header">
                    <span class="version-tag">${index === 0 ? '当前版本' : version.id}</span>
                    <span class="version-time">${this.formatDate(version.timestamp)}</span>
                </div>
                <div class="version-changes">
                    ${version.changes_summary || '无修改说明'}
                </div>
                ${index > 0 ? `
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
        `).join('');
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
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // 触发动画
        setTimeout(() => notification.classList.add('show'), 100);
        
        // 自动关闭
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, duration);
    }
    
    formatDate(timestamp) {
        const date = new Date(timestamp);
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
