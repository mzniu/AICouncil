/**
 * AICouncil 应用主入口
 * @module main
 */

import * as Utils from './core/utils.js';
import * as API from './core/api.js';
import * as State from './core/state.js';
import { t, setLanguage, initLanguage } from './core/i18n.js';
import * as Discussion from './modules/discussion.js';
import * as History from './modules/history.js';
import * as Export from './modules/export.js';
import * as UI from './modules/ui.js';

// ========================
// 全局函数挂载（供HTML内联事件使用）
// ========================

// 语言切换
window.t = t;
window.setLanguage = setLanguage;

// 讨论控制
window.startDiscussion = Discussion.startDiscussion;
window.stopDiscussion = Discussion.stopDiscussion;
window.submitIntervention = Discussion.submitIntervention;
window.submitRevisionFeedback = Discussion.submitRevisionFeedback;

// 认证相关
window.logout = API.logout;

// 历史管理
window.toggleHistoryModal = History.toggleHistoryModal;
window.loadWorkspace = History.loadWorkspace;
window.deleteWorkspace = History.deleteWorkspace;
window.toggleLogs = UI.toggleLogs;

// 导出功能
window.toggleDownloadDropdown = Export.toggleDownloadDropdown;
window.downloadHTML = Export.downloadHTML;
window.downloadMarkdown = Export.downloadMarkdown;
window.downloadPDF = Export.downloadPDF;
window.downloadImage = Export.downloadImage;
window.copyReport = Export.copyReport;
window.openReportInNewTab = Export.openReportInNewTab;

// UI交互
window.toggleOrchestratorMode = UI.toggleOrchestratorMode;
window.toggleAdvancedConfigModal = UI.toggleAdvancedConfigModal;
window.toggleRolesModal = UI.toggleRolesModal;
window.switchAdvancedTab = UI.switchAdvancedTab;
window.applyAdvancedConfig = UI.applyAdvancedConfig;
window.updateModalReasoningVisibility = UI.updateModalReasoningVisibility;
window.updateModalAgentConfigsUI = UI.updateModalAgentConfigsUI;
window.fetchOpenRouterModels = UI.fetchOpenRouterModels;
window.fetchDeepSeekModels = UI.fetchDeepSeekModels;
window.togglePresetsDropdown = UI.togglePresetsDropdown;
window.applyPreset = UI.applyPreset;
window.saveCurrentAsPreset = UI.saveCurrentAsPreset;
window.deletePreset = UI.deletePreset;
window.openPresetsTab = UI.openPresetsTab;
window.applyModalPreset = UI.applyModalPreset;
window.deleteModalPreset = UI.deleteModalPreset;
window.saveModalPreset = UI.saveModalPreset;
window.loadSystemSettings = UI.loadSystemSettings;
window.saveSettings = UI.saveSettings;
window.updateAgentConfigsUI = UI.updateAgentConfigsUI;
window.createAgentConfigItem = UI.createAgentConfigItem;

// 用户管理
window.loadUserInfo = UI.loadUserInfo;
window.loadMfaManagement = UI.loadMfaManagement;
window.disableMfa = UI.disableMfa;
window.changePassword = UI.changePassword;
window.handleLogout = UI.handleLogout;

// 角色管理
window.loadRolesList = UI.loadRolesList;
window.renderRolesList = UI.renderRolesList;
window.showRoleDetail = UI.showRoleDetail;
window.closeRoleDetail = UI.closeRoleDetail;
window.deleteRole = UI.deleteRole;
window.reloadRole = UI.reloadRole;
window.openRoleEditor = UI.openRoleEditor;
window.closeRoleEditor = UI.closeRoleEditor;
window.validateRoleConfig = UI.validateRoleConfig;
window.saveRoleConfig = UI.saveRoleConfig;
window.openRoleDesigner = UI.openRoleDesigner;
window.closeRoleDesigner = UI.closeRoleDesigner;
window.updateDesignerStep = UI.updateDesignerStep;
window.designerNextStep = UI.designerNextStep;
window.designerGoBack = UI.designerGoBack;
window.renderRolePreview = UI.renderRolePreview;
window.saveNewRole = UI.saveNewRole;
window.handleRoleDesignerEvent = UI.handleRoleDesignerEvent;

// 编制管理
window.togglePresetsDropdown = UI.togglePresetsDropdown;
window.loadPresets = UI.loadPresets;
window.renderPresetsList = UI.renderPresetsList;
window.saveCurrentAsPreset = UI.saveCurrentAsPreset;
window.applyPreset = UI.applyPreset;
window.deletePreset = UI.deletePreset;

// 高级配置
window.updateModalReasoningVisibility = UI.updateModalReasoningVisibility;
window.updateModalAgentConfigsUI = UI.updateModalAgentConfigsUI;
window.saveModalPreset = UI.saveModalPreset;
window.loadModalPresetsList = UI.loadModalPresetsList;
window.applyModalPreset = UI.applyModalPreset;
window.deleteModalPreset = UI.deleteModalPreset;
window.fetchOpenRouterModels = UI.fetchOpenRouterModels;
window.fetchDeepSeekModels = UI.fetchDeepSeekModels;
window.loadSystemSettings = UI.loadSystemSettings;
window.saveSettings = UI.saveSettings;
window.saveRoleConfig = UI.saveRoleConfig;
window.openRoleDesigner = UI.openRoleDesigner;
window.closeRoleDesigner = UI.closeRoleDesigner;
window.designerGoBack = UI.designerGoBack;
window.generateRoleDesign = UI.generateRoleDesign;
window.saveNewRole = UI.saveNewRole;

// 工具函数
window.showAlert = Utils.showAlert;
window.showConfirm = Utils.showConfirm;
window.closeAlertModal = Utils.closeAlertModal;
window.closeConfirmModal = Utils.closeConfirmModal;
window.showToast = Utils.showToast;
window.clearLogs = Utils.clearLogs;

// 讨论UI函数
window.toggleRevisionPanel = Discussion.toggleRevisionPanel;
window.applyRevision = Discussion.applyRevision;
window.confirmSatisfied = Discussion.confirmSatisfied;
window.toggleMaximize = Discussion.toggleMaximize;
window.toggleReasoning = Discussion.toggleReasoning;
window.toggleSearchCard = Discussion.toggleSearchCard;
window.toggleStage = Discussion.toggleStage;
window.toggleSmartCard = Discussion.toggleSmartCard;
window.fetchReportVersions = Discussion.fetchReportVersions;
window.loadReportVersion = Discussion.loadReportVersion;

// ========================
// 辅助函数
// ========================

/**
 * 检查用户是否为管理员
 */
async function checkAdminStatus() {
    try {
        const data = await API.getUserInfo();
        if (data.is_admin) {
            document.getElementById('admin-btn').classList.remove('hidden');
        }
    } catch (error) {
        console.error('Failed to check admin status:', error);
    }
}

/**
 * 初始化后端选择器联动
 */
function initBackendSelectListeners() {
    // 全局后端选择（主表单）
    const backendSelect = document.getElementById('backend-select');
    if (backendSelect) {
        backendSelect.addEventListener('change', function() {
            const modelInput = document.getElementById('global-model-input');
            const reasoningContainer = document.getElementById('global-reasoning-container');
            
            if (this.value === 'openrouter') {
                modelInput.setAttribute('list', 'openrouter-models-list');
                reasoningContainer.classList.remove('hidden');
                UI.fetchOpenRouterModels();
            } else if (this.value === 'deepseek') {
                modelInput.setAttribute('list', 'deepseek-models-list');
                reasoningContainer.classList.add('hidden');
                UI.fetchDeepSeekModels();
            } else {
                modelInput.removeAttribute('list');
                reasoningContainer.classList.add('hidden');
            }
        });
    }

    // Modal后端选择
    const modalBackendSelect = document.getElementById('modal-backend-select');
    if (modalBackendSelect) {
        modalBackendSelect.addEventListener('change', function() {
            UI.updateModalReasoningVisibility();
            
            const modelInput = document.getElementById('modal-global-model-input');
            if (this.value === 'openrouter') {
                modelInput.setAttribute('list', 'openrouter-models-list');
                UI.fetchOpenRouterModels();
            } else if (this.value === 'deepseek') {
                modelInput.setAttribute('list', 'deepseek-models-list');
                UI.fetchDeepSeekModels();
            } else {
                modelInput.removeAttribute('list');
            }
        });
    }

    // Agent后端选择器（事件委托）
    document.addEventListener('change', function(e) {
        if (e.target && e.target.classList.contains('agent-backend')) {
            const agentId = e.target.dataset.agent;
            const modelInput = document.querySelector(`.agent-model[data-agent="${agentId}"]`);
            const reasoningSelect = document.querySelector(`.agent-reasoning[data-agent="${agentId}"]`);
            
            if (e.target.value === 'openrouter') {
                modelInput.setAttribute('list', 'openrouter-models-list');
                reasoningSelect.classList.remove('hidden');
                UI.fetchOpenRouterModels();
            } else if (e.target.value === 'deepseek') {
                modelInput.setAttribute('list', 'deepseek-models-list');
                reasoningSelect.classList.add('hidden');
                UI.fetchDeepSeekModels();
            } else {
                modelInput.removeAttribute('list');
                reasoningSelect.classList.add('hidden');
            }
        }
    });
}

/**
 * 初始化输入框人数变化监听
 */
function initAgentCountListeners() {
    const plannersInput = document.getElementById('modal-planners-input');
    const auditorsInput = document.getElementById('modal-auditors-input');
    
    if (plannersInput) {
        plannersInput.addEventListener('input', () => {
            UI.updateModalAgentConfigsUI();
        });
    }
    
    if (auditorsInput) {
        auditorsInput.addEventListener('input', () => {
            UI.updateModalAgentConfigsUI();
        });
    }
}

/**
 * 初始化Orchestrator模式开关
 */
function initOrchestratorToggle() {
    const toggle = document.getElementById('orchestrator-mode-toggle');
    if (toggle) {
        const savedMode = localStorage.getItem('orchestrator_mode');
        if (savedMode === 'true') {
            toggle.checked = true;
            State.setIsOrchestratorMode(true);
        }
    }
}

/**
 * 初始化全局Agent后端选择器监听器
 */
function initGlobalAgentBackendListeners() {
    document.querySelectorAll('.agent-backend').forEach(select => {
        const agentId = select.dataset.agent;
        const input = document.querySelector(`.agent-model[data-agent="${agentId}"]`);
        if (input) {
            const updateAgentList = () => {
                if (select.value === 'openrouter') {
                    input.setAttribute('list', 'openrouter-models-list');
                    UI.fetchOpenRouterModels();
                } else if (select.value === 'deepseek') {
                    input.setAttribute('list', 'deepseek-models-list');
                    UI.fetchDeepSeekModels();
                } else {
                    input.removeAttribute('list');
                }
            };
            select.addEventListener('change', updateAgentList);
            updateAgentList(); // 初始检查
        }
    });
}

/**
 * 初始化按钮事件监听器
 */
function initButtonListeners() {
    // 主要操作按钮
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    
    if (startBtn) {
        startBtn.addEventListener('click', Discussion.startDiscussion);
    }
    
    if (stopBtn) {
        stopBtn.addEventListener('click', Discussion.stopDiscussion);
    }

    // 配置按钮
    const advancedBtn = document.getElementById('advanced-config-btn');
    if (advancedBtn) {
        advancedBtn.addEventListener('click', UI.toggleAdvancedConfigModal);
    }

    // 历史记录按钮
    const historyBtn = document.getElementById('history-btn');
    if (historyBtn) {
        historyBtn.addEventListener('click', History.toggleHistoryModal);
    }

    // 管理员按钮
    const adminBtn = document.getElementById('admin-btn');
    if (adminBtn) {
        adminBtn.addEventListener('click', () => {
            window.location.href = '/admin';
        });
    }
}

/**
 * 初始化点击外部关闭下拉菜单
 */
function initOutsideClickListeners() {
    window.addEventListener('click', function(event) {
        // 关闭预设下拉菜单
        const presetsDropdown = document.getElementById('presets-dropdown');
        const presetsBtn = document.querySelector('[onclick="togglePresetsDropdown()"]');
        
        if (presetsDropdown && !presetsDropdown.contains(event.target) && 
            presetsBtn && !presetsBtn.contains(event.target)) {
            presetsDropdown.classList.remove('show');
        }

        // 关闭下载下拉菜单
        const downloadDropdown = document.getElementById('download-dropdown');
        const downloadBtn = document.querySelector('[onclick="toggleDownloadDropdown()"]');
        
        if (downloadDropdown && !downloadDropdown.contains(event.target) && 
            downloadBtn && !downloadBtn.contains(event.target)) {
            downloadDropdown.classList.remove('show');
        }
    });
}

// ========================
// DOM加载完成后初始化
// ========================

document.addEventListener('DOMContentLoaded', async () => {
    console.log('AICouncil initializing...');
    
    try {
        // 1. 初始化语言
        initLanguage();
        console.log('Language initialized');
        
        // 2. 初始化DOM引用
        Discussion.initDOMReferences();
        console.log('Discussion module initialized');
        
        const reportIframe = document.getElementById('report-iframe');
        if (reportIframe) {
            Export.initExportModule(reportIframe);
            console.log('Export module initialized');
        }
        
        // 3. 初始化事件监听器
        initButtonListeners();
        initBackendSelectListeners();
        initAgentCountListeners();
        initOrchestratorToggle();
        initGlobalAgentBackendListeners();
        initOutsideClickListeners();
        console.log('Event listeners initialized');
        
        // 4. 启动状态轮询
        Discussion.startPolling();
        console.log('Status polling started');
        
        // 5. 检查管理员状态
        await checkAdminStatus();
        console.log('Admin status checked');
        
        // 6. 加载URL参数（如果存在）
        const urlParams = new URLSearchParams(window.location.search);
        const sessionId = urlParams.get('session');
        if (sessionId) {
            console.log('Loading session from URL:', sessionId);
            // 自动加载指定的session
            setTimeout(() => {
                History.loadWorkspace(sessionId);
            }, 500);
        }
        
        console.log('AICouncil initialized successfully');
    } catch (error) {
        console.error('Failed to initialize AICouncil:', error);
        Utils.showAlert('应用初始化失败: ' + error.message, '错误', 'error');
    }
});

// ========================
// 页面卸载清理
// ========================

window.addEventListener('beforeunload', () => {
    Discussion.stopPolling();
    console.log('AICouncil cleanup completed');
});

// ========================
// 错误处理
// ========================

window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
    // 可以在这里添加错误上报逻辑
});

window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    // 可以在这里添加错误上报逻辑
});

// 导出模块（用于调试）
export {
    Utils,
    API,
    State,
    Discussion,
    History,
    Export,
    UI
};
