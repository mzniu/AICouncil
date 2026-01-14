/**
 * UI交互模块 - 负责所有UI相关的工具函数
 * @module ui
 */

import { showAlert, showConfirm } from '../core/utils.js';
import { 
    getOpenRouterModels, 
    getDeepSeekModels, 
    getPresets,
    savePreset,
    deletePreset as apiDeletePreset,
    getConfig,
    saveConfig,
    getRoles,
    validateRole,
    designRole,
    saveRole,
    deleteRole as apiDeleteRole
} from '../core/api.js';
import * as State from '../core/state.js';
import { t } from '../core/i18n.js';

/**
 * 显示提示气泡
 * @param {string} message - 提示消息
 */
export function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'fixed top-20 right-4 bg-slate-800 text-white px-4 py-2 rounded-lg shadow-lg z-50 transition-opacity duration-300';
    toast.innerText = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 2000);
}

/**
 * 切换Orchestrator模式
 */
export function toggleOrchestratorMode() {
    const toggle = document.getElementById('orchestrator-mode-toggle');
    const isOrchestratorMode = toggle.checked;
    State.setIsOrchestratorMode(isOrchestratorMode);
    
    // 保存到 localStorage
    localStorage.setItem('orchestrator_mode', isOrchestratorMode ? 'true' : 'false');
    
    // 显示提示
    const modeText = isOrchestratorMode 
        ? (State.getCurrentLang() === 'zh' ? '智能编排模式已启用' : 'Orchestrator Mode Enabled')
        : (State.getCurrentLang() === 'zh' ? '传统模式已启用' : 'Traditional Mode Enabled');
    
    console.log(modeText, isOrchestratorMode);
    showToast(modeText);
}

/**
 * 切换Modal显示/隐藏
 * @param {string} modalId - Modal的DOM ID
 */
export function toggleModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.toggle('hidden');
    }
}

/**
 * 切换角色管理模态框
 */
export async function toggleRolesModal() {
    const modal = document.getElementById('roles-modal');
    if (!modal) return;
    
    if (modal.classList.contains('hidden')) {
        modal.classList.remove('hidden');
        // 打开时加载角色列表
        await loadRolesList();
    } else {
        modal.classList.add('hidden');
    }
}

/**
 * 切换高级配置Modal
 */
export async function toggleAdvancedConfigModal() {
    const modal = document.getElementById('advanced-config-modal');
    if (modal.classList.contains('hidden')) {
        // 打开modal - 从隐藏字段加载值到modal字段
        document.getElementById('modal-backend-select').value = document.getElementById('backend-select').value || 'deepseek';
        document.getElementById('modal-global-model-input').value = document.getElementById('global-model-input').value || '';
        document.getElementById('modal-global-reasoning-input').value = document.getElementById('global-reasoning-input').value || '';
        document.getElementById('modal-rounds-input').value = document.getElementById('rounds-input').value || '3';
        document.getElementById('modal-planners-input').value = document.getElementById('planners-input').value || '2';
        document.getElementById('modal-auditors-input').value = document.getElementById('auditors-input').value || '2';
        
        // 更新推理强度容器显示
        updateModalReasoningVisibility();
        // 更新席位配置列表
        updateModalAgentConfigsUI();
        // 加载编制列表
        await loadModalPresetsList();
        
        modal.classList.remove('hidden');
    } else {
        modal.classList.add('hidden');
    }
}

/**
 * 切换高级配置Tab
 * @param {string} tabName - Tab名称 ('basic'|'agents'|'presets'|'settings'|'user')
 */
export function switchAdvancedTab(tabName) {
    const basicBtn = document.getElementById('tab-basic-btn');
    const agentsBtn = document.getElementById('tab-agents-btn');
    const presetsBtn = document.getElementById('tab-presets-btn');
    const settingsBtn = document.getElementById('tab-settings-btn');
    const userBtn = document.getElementById('tab-user-btn');
    const basicContent = document.getElementById('tab-basic-content');
    const agentsContent = document.getElementById('tab-agents-content');
    const presetsContent = document.getElementById('tab-presets-content');
    const settingsContent = document.getElementById('tab-settings-content');
    const userContent = document.getElementById('tab-user-content');
    
    // 重置所有tab样式
    [basicBtn, agentsBtn, presetsBtn, settingsBtn, userBtn].forEach(btn => {
        if (btn) {
            btn.classList.remove('text-blue-600', 'border-blue-600');
            btn.classList.add('text-slate-500', 'border-transparent');
        }
    });
    [basicContent, agentsContent, presetsContent, settingsContent, userContent].forEach(content => {
        if (content) content.classList.add('hidden');
    });
    
    // 激活选中的tab
    if (tabName === 'basic') {
        basicBtn.classList.add('text-blue-600', 'border-blue-600');
        basicBtn.classList.remove('text-slate-500', 'border-transparent');
        basicContent.classList.remove('hidden');
    } else if (tabName === 'agents') {
        agentsBtn.classList.add('text-blue-600', 'border-blue-600');
        agentsBtn.classList.remove('text-slate-500', 'border-transparent');
        agentsContent.classList.remove('hidden');
        updateModalAgentConfigsUI();
    } else if (tabName === 'presets') {
        presetsBtn.classList.add('text-blue-600', 'border-blue-600');
        presetsBtn.classList.remove('text-slate-500', 'border-transparent');
        presetsContent.classList.remove('hidden');
        loadModalPresetsList();
    } else if (tabName === 'settings') {
        settingsBtn.classList.add('text-blue-600', 'border-blue-600');
        settingsBtn.classList.remove('text-slate-500', 'border-transparent');
        settingsContent.classList.remove('hidden');
        loadSystemSettings();
    } else if (tabName === 'user') {
        userBtn.classList.add('text-blue-600', 'border-blue-600');
        userBtn.classList.remove('text-slate-500', 'border-transparent');
        userContent.classList.remove('hidden');
        loadUserInfo();
    }
}

/**
 * 应用高级配置
 */
export async function applyAdvancedConfig() {
    // 如果当前在系统设置tab，先保存系统设置
    const settingsTab = document.getElementById('tab-settings-content');
    if (!settingsTab.classList.contains('hidden')) {
        const saved = await saveSettings();
        if (!saved) {
            return; // 如果保存失败，不关闭modal
        }
    }
    
    // 从modal字段复制值到隐藏字段
    document.getElementById('backend-select').value = document.getElementById('modal-backend-select').value;
    document.getElementById('global-model-input').value = document.getElementById('modal-global-model-input').value;
    document.getElementById('global-reasoning-input').value = document.getElementById('modal-global-reasoning-input').value;
    document.getElementById('rounds-input').value = document.getElementById('modal-rounds-input').value;
    document.getElementById('planners-input').value = document.getElementById('modal-planners-input').value;
    document.getElementById('auditors-input').value = document.getElementById('modal-auditors-input').value;
    
    // 触发后端选择变化事件
    const backendSelect = document.getElementById('backend-select');
    const event = new Event('change');
    backendSelect.dispatchEvent(event);
    
    // 关闭modal
    toggleAdvancedConfigModal();
    
    console.log('高级配置已应用');
}





/**
 * 打开编制Tab
 */
export function openPresetsTab() {
    const modal = document.getElementById('advanced-config-modal');
    if (modal.classList.contains('hidden')) {
        document.getElementById('modal-backend-select').value = document.getElementById('backend-select').value || 'deepseek';
        document.getElementById('modal-global-model-input').value = document.getElementById('global-model-input').value || '';
        document.getElementById('modal-global-reasoning-input').value = document.getElementById('global-reasoning-input').value || '';
        document.getElementById('modal-rounds-input').value = document.getElementById('rounds-input').value || '3';
        document.getElementById('modal-planners-input').value = document.getElementById('planners-input').value || '2';
        document.getElementById('modal-auditors-input').value = document.getElementById('auditors-input').value || '2';
        
        modal.classList.remove('hidden');
    }
    switchAdvancedTab('presets');
}




/**
 * 生成角色
 */
export async function generateRoleDesign() {
    const requirement = document.getElementById('role-requirement-input').value.trim();
    if (!requirement) {
        showAlert('请输入角色需求描述', '提示', 'warning');
        return;
    }
    
    updateDesignerStep(2);
    
    try {
        const data = await generateRole(requirement);
        
        if (data.success) {
            generatedRoleDesign = data.design;
            setTimeout(() => {
                updateDesignerStep(3);
                renderRolePreview(generatedRoleDesign);
            }, 1000);
        } else {
            showAlert('生成失败: ' + (data.message || '未知错误'), '错误', 'error');
            setTimeout(() => updateDesignerStep(1), 2000);
        }
    } catch (error) {
        console.error('Failed to generate role:', error);
        showAlert('生成失败: ' + error.message, '错误', 'error');
        updateDesignerStep(1);
    }
}



/**
 * 处理角色设计师的实时更新（占位函数）
 * @param {Object} eventData - 事件数据
 */
export function handleRoleDesignerEvent(eventData) {
    if (eventData.type === 'role_designer_reasoning') {
        const reasoningDiv = document.getElementById('reasoning-display');
        if (reasoningDiv) {
            reasoningDiv.textContent += eventData.content;
            reasoningDiv.scrollTop = reasoningDiv.scrollHeight;
        }
    } else if (eventData.type === 'role_designer_content') {
        const contentDiv = document.getElementById('content-display');
        if (contentDiv) {
            contentDiv.textContent += eventData.content;
            contentDiv.scrollTop = contentDiv.scrollHeight;
        }
    }
}

/**
 * 切换日志区域的显示/隐藏
 */
export function toggleLogs() {
    const logSection = document.getElementById('log-section');
    if (logSection) {
        logSection.classList.toggle('hidden');
    }
}

/**
 * 更新主界面Agent配置UI（兼容函数）
 */
export function updateAgentConfigsUI() {
    // 调用modal版本
    updateModalAgentConfigsUI();
}

/**
 * 创建Agent配置项
 */
export function createAgentConfigItem(label, id, bgColor, dotColor) {
    const div = document.createElement('div');
    div.className = `p-3 ${bgColor} rounded-lg border border-slate-200`;
    div.setAttribute('data-agent-wrapper', id);
    div.innerHTML = `
        <h4 class="text-xs font-bold text-slate-500 uppercase mb-2 flex items-center">
            <span class="w-2 h-2 ${dotColor} rounded-full mr-2"></span>${label}
        </h4>
        <div class="flex gap-2">
            <select class="agent-backend flex-1 text-xs p-1 border rounded" data-agent="${id}">
                <option value="default">使用默认</option>
                <option value="deepseek">DeepSeek</option>
                <option value="openai">OpenAI</option>
                <option value="openrouter">OpenRouter</option>
                <option value="aliyun">Aliyun</option>
                <option value="ollama">Ollama</option>
            </select>
            <input type="text" class="agent-model flex-1 text-xs p-1 border rounded" placeholder="模型名称" data-agent="${id}">
        </div>
        <select class="agent-reasoning hidden text-[10px] p-1 border rounded mt-1 w-full" data-agent="${id}">
            <option value="">关闭推理</option>
            <option value="low">推理: Low</option>
            <option value="medium">推理: Medium</option>
            <option value="high">推理: High</option>
        </select>
    `;
    return div;
}

// ==================== 用户管理函数 ====================

/**
 * 加载用户信息
 */
export async function loadUserInfo() {
    try {
        const response = await fetch('/api/auth/user/info');
        if (response.ok) {
            const data = await response.json();
            const usernameEl = document.getElementById('user-display-username');
            const emailEl = document.getElementById('user-display-email');
            const mfaEl = document.getElementById('user-display-mfa');
            
            if (usernameEl) usernameEl.textContent = data.username;
            if (emailEl) emailEl.textContent = data.email;
            
            if (mfaEl) {
                const mfaStatus = data.mfa_enabled 
                    ? '<span class="text-green-600">✅ 已启用</span>' 
                    : '<span class="text-gray-500">❌ 未启用</span>';
                mfaEl.innerHTML = mfaStatus;
            }
            
            // 加载MFA管理界面
            loadMfaManagement(data.mfa_enabled);
        } else {
            showAlert('加载用户信息失败', '错误', 'error');
        }
    } catch (error) {
        console.error('Load user info error:', error);
        showAlert('网络错误，无法加载用户信息', '错误', 'error');
    }
}

/**
 * 加载MFA管理界面
 */
export function loadMfaManagement(mfaEnabled) {
    const container = document.getElementById('mfa-status-container');
    if (!container) return;
    
    if (mfaEnabled) {
        // MFA已启用
        container.innerHTML = `
            <div class="bg-green-50 border border-green-200 p-3 rounded-lg">
                <div class="flex items-center mb-2">
                    <svg class="w-5 h-5 text-green-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                    </svg>
                    <span class="text-sm font-bold text-green-800">双因素认证已启用</span>
                </div>
                <p class="text-xs text-green-700 mb-3">您的账户已受到额外保护。如需更换设备或重新配置，请先禁用再重新设置。</p>
                <button onclick="window.disableMfa()" class="w-full bg-yellow-600 hover:bg-yellow-700 text-white py-2 px-4 rounded-lg font-bold transition">
                    禁用双因素认证
                </button>
            </div>
            <div class="bg-white border border-blue-200 p-3 rounded-lg">
                <p class="text-xs text-slate-600 mb-2">
                    <span class="font-bold">💡 提示：</span>禁用后可以重新配置MFA
                </p>
                <a href="/mfa-setup" target="_blank" class="text-blue-600 hover:text-blue-800 text-xs font-bold underline">
                    需要帮助？查看设置指南 ↗
                </a>
            </div>
        `;
    } else {
        // MFA未启用
        container.innerHTML = `
            <div class="bg-yellow-50 border border-yellow-200 p-3 rounded-lg">
                <div class="flex items-center mb-2">
                    <svg class="w-5 h-5 text-yellow-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
                    </svg>
                    <span class="text-sm font-bold text-yellow-800">建议启用双因素认证</span>
                </div>
                <p class="text-xs text-yellow-700 mb-3">启用双因素认证可以大幅提升账户安全性，防止密码泄露导致的账户被盗。</p>
                <a href="/mfa-setup" class="block w-full bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-lg font-bold transition text-center">
                    立即启用
                </a>
            </div>
            <div class="bg-white border border-blue-200 p-3 rounded-lg">
                <p class="text-xs text-slate-600 mb-1">
                    <span class="font-bold">🔐 什么是双因素认证？</span>
                </p>
                <p class="text-xs text-slate-500">
                    除了密码外，还需要手机验证器应用生成的6位动态验证码，即使密码泄露也能保护账户安全。
                </p>
            </div>
        `;
    }
}

/**
 * 禁用MFA
 */
export async function disableMfa() {
    const password = prompt('为了安全，请输入您的当前密码以禁用双因素认证：');
    
    if (!password) {
        return; // 用户取消
    }

    try {
        const response = await fetch('/api/auth/mfa/disable', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password })
        });

        const data = await response.json();

        if (response.ok) {
            showAlert('双因素认证已禁用。您可以随时重新启用。', '成功', 'success');
            // 重新加载用户信息
            loadUserInfo();
        } else {
            showAlert(data.error || '禁用失败', '错误', 'error');
        }
    } catch (error) {
        console.error('Disable MFA error:', error);
        showAlert('网络错误，请稍后重试', '错误', 'error');
    }
}

/**
 * 修改密码
 */
export async function changePassword() {
    const currentPassword = document.getElementById('user-current-password')?.value.trim();
    const newPassword = document.getElementById('user-new-password')?.value.trim();
    const confirmPassword = document.getElementById('user-confirm-password')?.value.trim();

    // 前端验证
    if (!currentPassword || !newPassword || !confirmPassword) {
        showAlert('请填写所有密码字段', '错误', 'error');
        return;
    }

    if (newPassword !== confirmPassword) {
        showAlert('两次输入的新密码不一致', '错误', 'error');
        return;
    }

    if (newPassword.length < 8) {
        showAlert('新密码长度至少8位', '错误', 'error');
        return;
    }

    try {
        const response = await fetch('/api/auth/user/change-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })
        });

        const data = await response.json();

        if (response.ok) {
            showAlert(data.message || '密码修改成功！', '成功', 'success');
            // 清空输入框
            const currentPwdEl = document.getElementById('user-current-password');
            const newPwdEl = document.getElementById('user-new-password');
            const confirmPwdEl = document.getElementById('user-confirm-password');
            if (currentPwdEl) currentPwdEl.value = '';
            if (newPwdEl) newPwdEl.value = '';
            if (confirmPwdEl) confirmPwdEl.value = '';
        } else {
            if (data.details) {
                const errors = Object.values(data.details).join('、');
                showAlert(`${data.error}：${errors}`, '错误', 'error');
            } else {
                showAlert(data.error || '密码修改失败', '错误', 'error');
            }
        }
    } catch (error) {
        console.error('Change password error:', error);
        showAlert('网络错误，请稍后重试', '错误', 'error');
    }
}

/**
 * 退出登录
 */
export async function handleLogout() {
    if (!confirm('确定要退出登录吗？')) {
        return;
    }

    try {
        const response = await fetch('/api/auth/logout', {
            method: 'POST'
        });

        if (response.ok) {
            window.location.href = '/login';
        } else {
            showAlert('登出失败，请稍后重试', '错误', 'error');
        }
    } catch (error) {
        console.error('Logout error:', error);
        showAlert('网络错误，请稍后重试', '错误', 'error');
    }
}

// ==================== 角色管理函数 ====================

/**
 * 加载角色列表
 */
export async function loadRolesList(tagFilter = null) {
    try {
        let url = '/api/roles';
        if (tagFilter) {
            url += `?tag=${tagFilter}`;
        }
        
        const response = await fetch(url);
        const data = await response.json();
        console.log('Roles API response:', data);
        
        if (data.status === 'success') {
            if (!data.roles) {
                console.error('API returned success but no roles array:', data);
                showAlert('角色数据格式错误：缺少roles字段', '错误', 'error');
                return;
            }
            renderRolesList(data.roles);
        } else {
            showAlert('加载失败: ' + (data.message || 'Unknown error'), '错误', 'error');
        }
    } catch (error) {
        console.error('Failed to load roles:', error);
        showAlert('加载失败: ' + error.message, '错误', 'error');
    }
}

/**
 * 渲染角色列表
 */
export function renderRolesList(roles) {
    const listContainer = document.getElementById('roles-list');
    if (!listContainer) return;

    listContainer.innerHTML = '';

    if (!roles || !Array.isArray(roles)) {
        console.error('renderRolesList: roles is not an array:', roles);
        listContainer.innerHTML = `<div class="col-span-2 text-center text-red-400 py-8">数据格式错误</div>`;
        return;
    }

    if (roles.length === 0) {
        listContainer.innerHTML = `<div class="col-span-2 text-center text-gray-400 py-8">暂无角色</div>`;
        return;
    }

    roles.forEach(role => {
        const card = document.createElement('div');
        card.className = 'bg-gradient-to-br from-slate-50 to-slate-100 p-4 rounded-xl border border-slate-200 hover:shadow-lg transition group';
        
        const colorMap = {
            'blue': 'bg-blue-500',
            'green': 'bg-green-500',
            'purple': 'bg-purple-500',
            'orange': 'bg-orange-500',
            'red': 'bg-red-500',
            'pink': 'bg-pink-500',
            'indigo': 'bg-indigo-500'
        };
        
        const bgColor = colorMap[role.ui.color] || 'bg-slate-500';
        const tags = role.tags.map(tag => {
            const tagColor = tag === 'core' ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-600';
            const tagText = tag === 'core' ? '核心' : (tag === 'advanced' ? '高级' : tag);
            return `<span class="px-2 py-0.5 ${tagColor} rounded-full text-xs">${tagText}</span>`;
        }).join(' ');
        
        card.innerHTML = `
            <div class="flex items-start justify-between mb-3">
                <div class="flex items-center space-x-3">
                    <div class="w-10 h-10 ${bgColor} rounded-lg flex items-center justify-center text-white text-xl">
                        ${role.ui.icon}
                    </div>
                    <div>
                        <h4 class="font-bold text-slate-800">${role.display_name}</h4>
                        <p class="text-xs text-slate-500">版本: ${role.version}</p>
                    </div>
                </div>
            </div>
            <p class="text-sm text-slate-600 mb-3 line-clamp-2">${role.ui.description_short}</p>
            <div class="flex flex-wrap gap-1 mb-3">
                ${tags}
            </div>
            <div class="flex justify-between items-center pt-2 border-t border-slate-200">
                <div class="text-xs text-slate-500">
                    阶段: ${role.stages.length}
                </div>
                <div class="flex gap-2">
                    <button onclick="window.showRoleDetail('${role.name}')" 
                            class="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded-lg transition">
                        详情
                    </button>
                    <button onclick="window.reloadRole('${role.name}')" 
                            class="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-xs rounded-lg transition">
                        重载
                    </button>
                </div>
            </div>
        `;
        
        listContainer.appendChild(card);
    });
}

/**
 * 显示角色详情
 */
export async function showRoleDetail(roleName) {
    try {
        const response = await fetch(`/api/roles/${roleName}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            const role = data.role;
            
            let contentHtml = '';
            
            // 阶段信息
            if (role.stages && role.stages.length > 0) {
                contentHtml += `
                    <section class="space-y-2">
                        <h4 class="text-sm font-bold text-slate-700">阶段</h4>
                        ${role.stages.map(stage => `
                            <div class="bg-slate-50 p-3 rounded-lg border border-slate-200">
                                <div class="font-bold text-slate-800 mb-1">${stage.name}</div>
                                <div class="text-xs text-slate-600">${stage.description || '无描述'}</div>
                                ${stage.input_vars && stage.input_vars.length > 0 ? `
                                    <div class="text-xs text-slate-500 mt-2">
                                        输入变量: ${stage.input_vars.join(', ')}
                                    </div>
                                ` : ''}
                            </div>
                        `).join('')}
                    </section>
                `;
            }
            
            // 参数信息
            if (role.parameters) {
                contentHtml += `
                    <section class="space-y-2">
                        <h4 class="text-sm font-bold text-slate-700">参数</h4>
                        <div class="bg-slate-50 p-3 rounded-lg border border-slate-200">
                            <div class="grid grid-cols-2 gap-2 text-xs">
                                <div><span class="text-slate-500">Temperature:</span> <span class="font-mono">${role.parameters.temperature}</span></div>
                                <div><span class="text-slate-500">Max Retries:</span> <span class="font-mono">${role.parameters.max_retries}</span></div>
                            </div>
                        </div>
                    </section>
                `;
            }
            
            // 提示词预览
            if (role.prompt_preview || role.prompts) {
                let promptContent = '';
                if (role.prompts) {
                    promptContent = Object.entries(role.prompts).map(([stage, prompt]) => 
                        `<div class="mb-3 pb-3 border-b border-slate-200 last:border-0 last:pb-0">
                            <h5 class="text-xs font-bold text-blue-700 mb-2">阶段: ${stage}</h5>
                            <pre class="text-xs text-slate-600 whitespace-pre-wrap font-mono">${prompt}</pre>
                        </div>`
                    ).join('');
                } else {
                    promptContent = `<pre class="text-xs text-slate-600 whitespace-pre-wrap font-mono">${role.prompt_preview}</pre>`;
                }
                
                contentHtml += `
                    <section class="space-y-2">
                        <h4 class="text-sm font-bold text-slate-700">提示词预览</h4>
                        <div class="bg-slate-50 p-3 rounded-lg border border-slate-200 max-h-96 overflow-y-auto">
                            ${promptContent}
                        </div>
                    </section>
                `;
            }
            
            // 显示Modal
            const nameEl = document.getElementById('detail-role-name');
            const descEl = document.getElementById('detail-role-desc');
            const contentEl = document.getElementById('detail-role-content');
            
            if (nameEl) nameEl.textContent = role.display_name;
            if (descEl) descEl.textContent = role.description;
            if (contentEl) contentEl.innerHTML = contentHtml;
            
            // 添加编辑和删除按钮
            const modal = document.getElementById('role-detail-modal');
            if (modal) {
                const detailHeader = modal.querySelector('.flex.justify-between');
                if (detailHeader) {
                    const existingBtns = detailHeader.querySelector('.role-action-btns');
                    if (existingBtns) {
                        existingBtns.remove();
                    }
                    
                    const btnContainer = document.createElement('div');
                    btnContainer.className = 'role-action-btns flex space-x-2 mr-2';
                    
                    const editBtn = document.createElement('button');
                    editBtn.className = 'px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg transition text-sm';
                    editBtn.innerHTML = '✏️ 编辑';
                    editBtn.onclick = () => window.openRoleEditor(roleName);
                    
                    const deleteBtn = document.createElement('button');
                    deleteBtn.className = 'px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg transition text-sm';
                    deleteBtn.innerHTML = '🗑️ 删除';
                    deleteBtn.onclick = () => window.deleteRole(roleName);
                    
                    btnContainer.appendChild(editBtn);
                    btnContainer.appendChild(deleteBtn);
                    
                    const closeBtn = detailHeader.querySelector('button');
                    if (closeBtn) {
                        closeBtn.parentElement.insertBefore(btnContainer, closeBtn);
                    }
                }
                
                modal.classList.remove('hidden');
            }
        } else {
            showAlert('加载失败: ' + data.message, '错误', 'error');
        }
    } catch (error) {
        console.error('Failed to load role detail:', error);
        showAlert('加载失败: ' + error.message, '错误', 'error');
    }
}

/**
 * 关闭角色详情
 */
export function closeRoleDetail() {
    const modal = document.getElementById('role-detail-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

/**
 * 删除角色
 */
export async function deleteRole(roleName) {
    const confirmed = confirm(`确定要删除角色 "${roleName}" 吗？\n\n此操作将删除角色配置文件和所有相关Prompt文件，且不可恢复！`);
    if (!confirmed) return;
    
    try {
        const response = await fetch(`/api/roles/${roleName}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        
        if (data.status === 'success') {
            showAlert('角色已成功删除', '删除成功');
            closeRoleDetail();
            await loadRolesList();
        } else {
            showAlert('删除失败: ' + data.message, '错误', 'error');
        }
    } catch (error) {
        console.error('Failed to delete role:', error);
        showAlert('删除失败: ' + error.message, '错误', 'error');
    }
}

/**
 * 重载角色
 */
export async function reloadRole(roleName) {
    try {
        const response = await fetch(`/api/roles/${roleName}/reload`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        
        if (data.status === 'success') {
            showAlert('角色重载成功', '成功');
            await loadRolesList();
            closeRoleDetail();
        } else {
            showAlert('重载失败: ' + data.message, '错误', 'error');
        }
    } catch (error) {
        console.error('Failed to reload role:', error);
        showAlert('重载失败: ' + error.message, '错误', 'error');
    }
}

// 编辑器状态
let currentEditingRole = null;

/**
 * 打开角色编辑器
 */
export async function openRoleEditor(roleName) {
    try {
        const response = await fetch(`/api/roles/${roleName}/config`);
        const data = await response.json();
        
        if (data.status === 'success') {
            currentEditingRole = roleName;
            
            const modal = document.getElementById('role-edit-modal');
            const nameEl = document.getElementById('edit-role-name');
            const editorEl = document.getElementById('role-yaml-editor');
            
            if (modal) modal.classList.remove('hidden');
            if (nameEl) nameEl.textContent = roleName;
            if (editorEl) editorEl.value = data.data.yaml_content;
            
            // 加载prompts
            const promptsContainer = document.getElementById('prompt-editors');
            if (promptsContainer) {
                promptsContainer.innerHTML = '';
                
                for (const [stageName, promptContent] of Object.entries(data.data.prompts)) {
                    const editorHtml = `
                        <div class="border border-slate-300 rounded-lg p-4">
                            <label class="block text-xs font-bold text-slate-600 uppercase mb-2">${stageName} Prompt</label>
                            <textarea data-stage="${stageName}" 
                                      class="prompt-editor w-full h-48 px-3 py-2 border border-slate-300 rounded-lg font-mono text-sm outline-none focus:border-blue-500 transition"
                                      placeholder="Prompt内容...">${promptContent}</textarea>
                        </div>
                    `;
                    promptsContainer.insertAdjacentHTML('beforeend', editorHtml);
                }
            }
        } else {
            showAlert('加载配置失败: ' + data.message, '错误', 'error');
        }
    } catch (error) {
        console.error('Failed to load role config:', error);
        showAlert('加载配置失败: ' + error.message, '错误', 'error');
    }
}

/**
 * 关闭角色编辑器
 */
export function closeRoleEditor() {
    const modal = document.getElementById('role-edit-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
    currentEditingRole = null;
}

/**
 * 验证角色配置
 */
export async function validateRoleConfig() {
    const editorEl = document.getElementById('role-yaml-editor');
    if (!editorEl) return;
    
    const yamlContent = editorEl.value;
    
    try {
        const response = await fetch('/api/roles/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ yaml_content: yamlContent })
        });
        const data = await response.json();
        
        if (data.status === 'success' && data.valid) {
            showAlert('✅ 配置验证通过', '成功');
        } else {
            showAlert('❌ 配置验证失败:\n' + data.error, '错误', 'error');
        }
    } catch (error) {
        showAlert('验证失败: ' + error.message, '错误', 'error');
    }
}

/**
 * 保存角色配置
 */
export async function saveRoleConfig() {
    if (!currentEditingRole) return;
    
    const editorEl = document.getElementById('role-yaml-editor');
    if (!editorEl) return;
    
    const yamlContent = editorEl.value;
    
    // 收集所有prompt
    const prompts = {};
    document.querySelectorAll('.prompt-editor').forEach(textarea => {
        const stageName = textarea.getAttribute('data-stage');
        prompts[stageName] = textarea.value;
    });
    
    try {
        const response = await fetch(`/api/roles/${currentEditingRole}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                yaml_content: yamlContent,
                prompts: prompts
            })
        });
        const data = await response.json();
        
        if (data.status === 'success') {
            showAlert('✅ 角色配置已保存并重载', '成功');
            closeRoleEditor();
            await loadRolesList();
            closeRoleDetail();
        } else {
            showAlert('❌ 保存失败:\n' + data.message, '错误', 'error');
        }
    } catch (error) {
        console.error('Failed to save role config:', error);
        showAlert('保存失败: ' + error.message, '错误', 'error');
    }
}

// 设计器状态
let currentDesignerStep = 1;
let generatedRoleDesign = null;

/**
 * 打开角色设计师
 */
export function openRoleDesigner() {
    currentDesignerStep = 1;
    generatedRoleDesign = null;
    
    const inputEl = document.getElementById('role-requirement-input');
    if (inputEl) inputEl.value = '';
    
    const modal = document.getElementById('role-designer-modal');
    if (modal) {
        modal.classList.remove('hidden');
    }
    
    updateDesignerStep(1);
}

/**
 * 关闭角色设计师
 */
export function closeRoleDesigner() {
    const modal = document.getElementById('role-designer-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
    currentDesignerStep = 1;
    generatedRoleDesign = null;
}

/**
 * 更新设计器步骤
 */
export function updateDesignerStep(step) {
    currentDesignerStep = step;
    
    // 隐藏所有步骤
    for (let i = 1; i <= 3; i++) {
        const stepEl = document.getElementById(`designer-step-${i}`);
        if (stepEl) {
            stepEl.classList.add('hidden');
        }
    }
    
    // 显示当前步骤
    const currentStepEl = document.getElementById(`designer-step-${step}`);
    if (currentStepEl) {
        currentStepEl.classList.remove('hidden');
    }
    
    // 更新步骤指示器
    for (let i = 1; i <= 3; i++) {
        const indicator = document.getElementById(`step-indicator-${i}`);
        const label = document.getElementById(`step-label-${i}`);
        
        if (!indicator || !label) continue;
        
        if (i < step) {
            indicator.className = 'w-10 h-10 rounded-full bg-green-500 text-white flex items-center justify-center font-bold';
            indicator.innerHTML = '✓';
            label.className = 'ml-2 text-green-600 font-bold';
        } else if (i === step) {
            indicator.className = 'w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold';
            indicator.textContent = i;
            label.className = 'ml-2 font-bold text-blue-600';
        } else {
            indicator.className = 'w-10 h-10 rounded-full bg-slate-200 text-slate-400 flex items-center justify-center font-bold';
            indicator.textContent = i;
            label.className = 'ml-2 text-slate-400';
        }
    }
    
    // 更新进度条
    for (let i = 1; i <= 2; i++) {
        const progress = document.getElementById(`step-progress-${i}`);
        if (progress) {
            progress.style.width = i < step ? '100%' : '0%';
        }
    }
    
    // 更新按钮
    const backBtn = document.getElementById('designer-back-btn');
    const nextBtn = document.getElementById('designer-next-btn');
    
    if (backBtn && nextBtn) {
        if (step === 1) {
            backBtn.classList.add('hidden');
            nextBtn.textContent = '开始生成 →';
            nextBtn.onclick = () => window.designerNextStep();
        } else if (step === 2) {
            backBtn.classList.add('hidden');
            nextBtn.classList.add('hidden');
        } else if (step === 3) {
            backBtn.classList.remove('hidden');
            nextBtn.classList.remove('hidden');
            nextBtn.textContent = '保存角色';
            nextBtn.onclick = () => window.saveNewRole();
        }
    }
}

/**
 * 设计器下一步
 */
export async function designerNextStep() {
    if (currentDesignerStep === 1) {
        const inputEl = document.getElementById('role-requirement-input');
        if (!inputEl) return;
        
        const requirement = inputEl.value.trim();
        if (!requirement) {
            showAlert('请输入角色需求描述', '提示', 'warning');
            return;
        }
        
        updateDesignerStep(2);
        
        // 清空显示区
        const reasoningEl = document.getElementById('reasoning-display');
        const contentEl = document.getElementById('content-display');
        if (reasoningEl) reasoningEl.textContent = '';
        if (contentEl) contentEl.textContent = '';
        
        try {
            const response = await fetch('/api/roles/design', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ requirement })
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                generatedRoleDesign = data.design;
                
                setTimeout(() => {
                    updateDesignerStep(3);
                    renderRolePreview(generatedRoleDesign);
                }, 1000);
            } else {
                showAlert('生成失败: ' + (data.message || '未知错误'), '错误', 'error');
                setTimeout(() => updateDesignerStep(1), 2000);
            }
        } catch (error) {
            console.error('Failed to generate role:', error);
            showAlert('生成失败: ' + error.message, '错误', 'error');
            updateDesignerStep(1);
        }
    }
}

/**
 * 设计器返回
 */
export function designerGoBack() {
    if (currentDesignerStep === 3) {
        updateDesignerStep(1);
    }
}

/**
 * 渲染角色预览
 */
export function renderRolePreview(design) {
    // 渲染基本信息
    const nameEl = document.getElementById('preview-role-name');
    const displayNameEl = document.getElementById('preview-display-name');
    const descEl = document.getElementById('preview-description');
    
    if (nameEl) nameEl.value = design.role_name;
    if (displayNameEl) displayNameEl.value = design.display_name;
    if (descEl) descEl.value = design.role_description;
    
    // 渲染阶段
    const stagesContainer = document.getElementById('preview-stages-container');
    if (stagesContainer) {
        stagesContainer.innerHTML = '';
        
        design.stages.forEach((stage) => {
            const stageCard = document.createElement('div');
            stageCard.className = 'bg-white border border-slate-300 rounded-lg p-3';
            stageCard.innerHTML = `
                <div class="flex items-center justify-between mb-2">
                    <h5 class="font-bold text-slate-700">${stage.stage_name}</h5>
                    <span class="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">${stage.output_schema}</span>
                </div>
                <p class="text-sm text-slate-600 mb-2"><strong>思维方式:</strong> ${stage.thinking_style}</p>
                <div class="text-sm text-slate-600">
                    <strong>职责:</strong>
                    <ul class="list-disc list-inside mt-1 space-y-1">
                        ${stage.responsibilities.map(r => `<li>${r}</li>`).join('')}
                    </ul>
                </div>
                <p class="text-xs text-slate-500 mt-2"><strong>输出格式:</strong> ${stage.output_format}</p>
            `;
            stagesContainer.appendChild(stageCard);
        });
    }
    
    // 渲染推荐人物
    const personasContainer = document.getElementById('preview-personas-container');
    if (personasContainer) {
        personasContainer.innerHTML = '';
        
        if (design.recommended_personas && design.recommended_personas.length > 0) {
            design.recommended_personas.forEach(persona => {
                const personaCard = document.createElement('div');
                personaCard.className = 'bg-white border border-slate-300 rounded-lg p-3 flex items-start';
                personaCard.innerHTML = `
                    <div class="text-2xl mr-3">👤</div>
                    <div class="flex-1">
                        <h5 class="font-bold text-slate-700 mb-1">${persona.name}</h5>
                        <p class="text-sm text-slate-600 mb-2">${persona.reason}</p>
                        <div class="flex flex-wrap gap-1">
                            ${persona.traits.map(t => `<span class="text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded">${t}</span>`).join('')}
                        </div>
                    </div>
                `;
                personasContainer.appendChild(personaCard);
            });
        } else {
            personasContainer.innerHTML = '<p class="text-sm text-slate-400">无推荐人物</p>';
        }
    }
}

/**
 * 保存新角色
 */
export async function saveNewRole() {
    try {
        const displayNameEl = document.getElementById('preview-display-name');
        const descEl = document.getElementById('preview-description');
        
        const updatedDesign = {
            ...generatedRoleDesign,
            display_name: displayNameEl ? displayNameEl.value : generatedRoleDesign.display_name,
            role_description: descEl ? descEl.value : generatedRoleDesign.role_description
        };
        
        const response = await fetch('/api/roles', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(updatedDesign)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert(`✅ 成功创建角色: ${data.display_name}`, '成功', 'success');
            closeRoleDesigner();
            
            // 刷新角色列表
            if (typeof window.loadRoles === 'function') {
                window.loadRoles();
            } else if (typeof loadRolesList === 'function') {
                loadRolesList();
            }
        } else {
            showAlert('创建失败: ' + (data.message || '未知错误'), '错误', 'error');
        }
    } catch (error) {
        console.error('Failed to create role:', error);
        showAlert('创建失败: ' + error.message, '错误', 'error');
    }
}

// ==================== 编制管理函数 ====================

/**
 * 切换编制下拉菜单
 */
export function togglePresetsDropdown() {
    const dropdown = document.getElementById('presets-dropdown');
    if (dropdown) {
        dropdown.classList.toggle('show');
        if (dropdown.classList.contains('show')) {
            loadPresets();
        }
    }
}

/**
 * 加载编制列表
 */
export async function loadPresets() {
    try {
        const response = await fetch('/api/presets');
        const data = await response.json();
        
        if (data.presets) {
            renderPresetsList(data.presets);
        }
    } catch (error) {
        console.error('Failed to load presets:', error);
    }
}

/**
 * 渲染编制列表
 */
export function renderPresetsList(presets) {
    const dropdownContainer = document.getElementById('presets-list-container');
    
    if (!dropdownContainer) return;

    dropdownContainer.innerHTML = '';

    // API返回的是对象格式 {name: config, ...}，需要转换为数组
    const presetArray = Object.entries(presets || {});
    
    if (presetArray.length === 0) {
        const emptyHtml = `<div class="text-center text-gray-400 py-4 text-xs">暂无存档</div>`;
        dropdownContainer.innerHTML = emptyHtml;
        return;
    }

    for (const [name, config] of presetArray) {
        const dropdownItem = document.createElement('button');
        dropdownItem.onclick = () => { 
            window.applyPreset(name); 
            window.togglePresetsDropdown(); 
        };
        dropdownItem.className = 'w-full text-left px-4 py-3 text-sm text-slate-700 hover:bg-slate-50 transition group border-b border-slate-100 last:border-0';
        dropdownItem.innerHTML = `
            <div class="font-bold text-slate-700 mb-1 truncate">${name}</div>
            <div class="text-xs text-slate-500 group-hover:text-slate-600 flex items-center space-x-2">
                <span class="bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded text-[10px] border border-blue-100 font-medium">${config.backend || 'default'}</span>
                <span class="bg-slate-100 px-1.5 py-0.5 rounded text-[10px] border border-slate-200">R${config.rounds || 3}</span>
                <span class="flex items-center space-x-1">
                    <span title="策论家">🧠 ${config.planners || 2}</span>
                    <span class="text-slate-300">|</span>
                    <span title="监察官">👁️ ${config.auditors || 2}</span>
                </span>
            </div>
        `;
        dropdownContainer.appendChild(dropdownItem);
    }
}

/**
 * 保存当前配置为编制
 */
export async function saveCurrentAsPreset() {
    let name = prompt('请输入编制名称：');
    if (!name || !name.trim()) return;
    
    name = name.trim();

    // 收集当前配置
    const config = {
        backend: document.getElementById('backend-select')?.value || 'deepseek',
        global_model: document.getElementById('global-model-input')?.value || '',
        global_reasoning: document.getElementById('global-reasoning-input')?.value || '',
        rounds: parseInt(document.getElementById('rounds-input')?.value || 3),
        planners: parseInt(document.getElementById('planners-input')?.value || 2),
        auditors: parseInt(document.getElementById('auditors-input')?.value || 2),
        agents: {}
    };

    // 收集Agent配置
    document.querySelectorAll('.agent-backend').forEach(select => {
        const agentId = select.dataset.agent;
        const modelInput = document.querySelector(`.agent-model[data-agent="${agentId}"]`);
        const reasoningSelect = document.querySelector(`.agent-reasoning[data-agent="${agentId}"]`);
        
        config.agents[agentId] = {
            backend: select.value,
            model: modelInput ? modelInput.value : '',
            reasoning: reasoningSelect ? reasoningSelect.value : ''
        };
    });

    try {
        const response = await fetch('/api/presets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, config })
        });
        const data = await response.json();
        
        if (data.status === 'success') {
            showAlert('编制已保存', '成功');
            loadPresets();
        } else {
            showAlert(data.message, '错误', 'error');
        }
    } catch (error) {
        showAlert(error.message, '错误', 'error');
    }
}

/**
 * 应用编制
 */
export function applyPreset(name) {
    fetch('/api/presets')
        .then(res => res.json())
        .then(data => {
            const config = data.presets[name];
            if (config) {
                const backendSelect = document.getElementById('backend-select');
                const globalModelInput = document.getElementById('global-model-input');
                const globalReasoningInput = document.getElementById('global-reasoning-input');
                const roundsInput = document.getElementById('rounds-input');
                const plannersInput = document.getElementById('planners-input');
                const auditorsInput = document.getElementById('auditors-input');
                
                if (backendSelect) {
                    backendSelect.value = config.backend || 'deepseek';
                    backendSelect.dispatchEvent(new Event('change'));
                }
                if (globalModelInput) globalModelInput.value = config.global_model || '';
                if (globalReasoningInput) globalReasoningInput.value = config.global_reasoning || '';
                if (roundsInput) roundsInput.value = config.rounds || 3;
                if (plannersInput) plannersInput.value = config.planners || 2;
                if (auditorsInput) auditorsInput.value = config.auditors || 2;

                // 应用Agent配置
                if (config.agents) {
                    for (const [agentId, agentConfig] of Object.entries(config.agents)) {
                        const backendSelect = document.querySelector(`.agent-backend[data-agent="${agentId}"]`);
                        const modelInput = document.querySelector(`.agent-model[data-agent="${agentId}"]`);
                        const reasoningSelect = document.querySelector(`.agent-reasoning[data-agent="${agentId}"]`);
                        
                        if (backendSelect) {
                            backendSelect.value = agentConfig.backend;
                            backendSelect.dispatchEvent(new Event('change'));
                        }
                        if (modelInput) modelInput.value = agentConfig.model || '';
                        if (reasoningSelect) reasoningSelect.value = agentConfig.reasoning || '';
                    }
                }

                showAlert('编制已加载', '成功');
            } else {
                showAlert('编制不存在', '错误', 'error');
            }
        })
        .catch(error => {
            showAlert(error.message, '错误', 'error');
        });
}

/**
 * 删除编制
 */
export async function deletePreset(name) {
    if (!confirm('确定要删除此编制吗？')) return;

    try {
        const response = await fetch(`/api/presets/${encodeURIComponent(name)}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        
        if (data.status === 'success') {
            showAlert('编制已删除', '成功');
            loadPresets();
        } else {
            showAlert(data.message, '错误', 'error');
        }
    } catch (error) {
        showAlert(error.message, '错误', 'error');
    }
}

// ==================== 高级配置函数 ====================

/**
 * 更新Modal推理强度显示
 */
export function updateModalReasoningVisibility() {
    const backendSelect = document.getElementById('modal-backend-select');
    const reasoningContainer = document.getElementById('modal-global-reasoning-container');
    
    if (backendSelect && reasoningContainer) {
        const backend = backendSelect.value;
        const supportsReasoning = ['deepseek', 'openai', 'azure', 'openrouter'].includes(backend);
        
        if (supportsReasoning) {
            reasoningContainer.classList.remove('hidden');
        } else {
            reasoningContainer.classList.add('hidden');
        }
    }
}

/**
 * 更新Modal中的Agent配置UI
 */
export function updateModalAgentConfigsUI() {
    const container = document.getElementById('modal-agent-configs-container');
    if (!container) return;
    
    const plannersInput = document.getElementById('modal-planners-input');
    const auditorsInput = document.getElementById('modal-auditors-input');
    
    const plannersCount = parseInt(plannersInput?.value || 0);
    const auditorsCount = parseInt(auditorsInput?.value || 0);
    
    // 处理策论家
    for (let i = 0; i < 5; i++) {
        const id = `planner_${i}`;
        let el = container.querySelector(`[data-agent-wrapper="${id}"]`);
        
        if (i < plannersCount) {
            if (!el) {
                const div = window.createAgentConfigItem(`策论家 ${i+1}`, id, 'bg-blue-50', 'bg-blue-500');
                container.appendChild(div);
            } else {
                const label = el.querySelector('h4');
                if (label) {
                    label.innerHTML = `<span class="w-2 h-2 bg-blue-500 rounded-full mr-2"></span>策论家 ${i+1}`;
                }
            }
        } else if (el) {
            container.removeChild(el);
        }
    }

    // 处理监察官
    for (let i = 0; i < 5; i++) {
        const id = `auditor_${i}`;
        let el = container.querySelector(`[data-agent-wrapper="${id}"]`);
        
        if (i < auditorsCount) {
            if (!el) {
                const div = window.createAgentConfigItem(`监察官 ${i+1}`, id, 'bg-amber-50', 'bg-amber-500');
                container.appendChild(div);
            } else {
                const label = el.querySelector('h4');
                if (label) {
                    label.innerHTML = `<span class="w-2 h-2 bg-amber-500 rounded-full mr-2"></span>监察官 ${i+1}`;
                }
            }
        } else if (el) {
            container.removeChild(el);
        }
    }
}

/**
 * 保存Modal编制
 */
export async function saveModalPreset() {
    const nameInput = document.getElementById('modal-new-preset-name');
    if (!nameInput) return;
    
    let name = nameInput.value.trim();
    
    if (!name) {
        showAlert('请输入编制名称', '提示', 'warning');
        return;
    }

    // 从modal字段收集配置
    const config = {
        backend: document.getElementById('modal-backend-select')?.value || 'deepseek',
        global_model: document.getElementById('modal-global-model-input')?.value || '',
        global_reasoning: document.getElementById('modal-global-reasoning-input')?.value || '',
        rounds: parseInt(document.getElementById('modal-rounds-input')?.value || 3),
        planners: parseInt(document.getElementById('modal-planners-input')?.value || 2),
        auditors: parseInt(document.getElementById('modal-auditors-input')?.value || 2),
        agents: {}
    };

    // 收集Agent配置
    document.querySelectorAll('.agent-backend').forEach(select => {
        const agentId = select.dataset.agent;
        const modelInput = document.querySelector(`.agent-model[data-agent="${agentId}"]`);
        const reasoningSelect = document.querySelector(`.agent-reasoning[data-agent="${agentId}"]`);
        
        if (modelInput && reasoningSelect) {
            config.agents[agentId] = {
                backend: select.value,
                model: modelInput.value,
                reasoning: reasoningSelect.value
            };
        }
    });

    try {
        const response = await fetch('/api/presets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, config })
        });
        const data = await response.json();
        
        if (data.status === 'success') {
            showAlert('编制已保存', '成功');
            nameInput.value = ''; 
            loadModalPresetsList();
            if (typeof loadPresets === 'function') {
                loadPresets();
            }
        } else {
            showAlert(data.message, '错误', 'error');
        }
    } catch (error) {
        showAlert(error.message, '错误', 'error');
    }
}

/**
 * 加载Modal编制列表
 */
export async function loadModalPresetsList() {
    const container = document.getElementById('modal-presets-list');
    if (!container) return;
    
    try {
        const response = await fetch('/api/presets');
        const data = await response.json();
        
        const presetArray = Object.entries(data.presets || {});
        
        if (presetArray.length > 0) {
            container.innerHTML = presetArray.map(([name, config]) => `
                <div class="bg-white p-3 rounded-lg border border-slate-200 hover:border-blue-300 transition flex items-center justify-between">
                    <div class="flex-1">
                        <div class="font-bold text-slate-700 mb-1">${name}</div>
                        <div class="text-xs text-slate-500">
                            ${config.backend || 'default'} | 轮次: ${config.rounds || 3} | 
                            策论家: ${config.planners || 2} | 监察官: ${config.auditors || 2}
                        </div>
                    </div>
                    <div class="flex space-x-2">
                        <button onclick="window.applyModalPreset('${name}')" class="text-xs bg-blue-500 hover:bg-blue-600 text-white px-3 py-1 rounded transition">
                            加载
                        </button>
                        <button onclick="window.deleteModalPreset('${name}')" class="text-xs bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded transition">
                            删除
                        </button>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<div class="text-center text-gray-400 py-4">暂无存档</div>';
        }
    } catch (error) {
        container.innerHTML = `<div class="text-center text-red-400 py-4">加载失败: ${error.message}</div>`;
    }
}

/**
 * 应用Modal编制
 */
export async function applyModalPreset(name) {
    try {
        const response = await fetch('/api/presets');
        const data = await response.json();
        
        const config = data.presets[name];
        if (!config) {
            showAlert('编制不存在', '错误', 'error');
            return;
        }
        
        // 应用到modal字段
        const backendSelect = document.getElementById('modal-backend-select');
        const modelInput = document.getElementById('modal-global-model-input');
        const reasoningInput = document.getElementById('modal-global-reasoning-input');
        const roundsInput = document.getElementById('modal-rounds-input');
        const plannersInput = document.getElementById('modal-planners-input');
        const auditorsInput = document.getElementById('modal-auditors-input');
        
        if (backendSelect) backendSelect.value = config.backend || 'deepseek';
        if (modelInput) modelInput.value = config.global_model || '';
        if (reasoningInput) reasoningInput.value = config.global_reasoning || '';
        if (roundsInput) roundsInput.value = config.rounds || 3;
        if (plannersInput) plannersInput.value = config.planners || 2;
        if (auditorsInput) auditorsInput.value = config.auditors || 2;
        
        // 更新推理强度显示
        updateModalReasoningVisibility();
        
        // 应用Agent配置
        if (config.agents) {
            Object.keys(config.agents).forEach(agentId => {
                const agentConfig = config.agents[agentId];
                const backendSelect = document.querySelector(`.agent-backend[data-agent="${agentId}"]`);
                const modelInput = document.querySelector(`.agent-model[data-agent="${agentId}"]`);
                const reasoningSelect = document.querySelector(`.agent-reasoning[data-agent="${agentId}"]`);
                
                if (backendSelect) backendSelect.value = agentConfig.backend || 'default';
                if (modelInput) modelInput.value = agentConfig.model || '';
                if (reasoningSelect) reasoningSelect.value = agentConfig.reasoning || '';
            });
        }
        
        // 更新席位配置UI
        updateModalAgentConfigsUI();
        
        showAlert('编制已加载', '成功');
    } catch (error) {
        showAlert(error.message, '错误', 'error');
    }
}

/**
 * 删除Modal编制
 */
export async function deleteModalPreset(name) {
    if (!confirm('确定要删除此编制吗？')) return;

    try {
        const response = await fetch(`/api/presets/${encodeURIComponent(name)}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        
        if (data.status === 'success') {
            showAlert('编制已删除', '成功');
            loadModalPresetsList();
            if (typeof loadPresets === 'function') {
                loadPresets();
            }
        } else {
            showAlert(data.message, '错误', 'error');
        }
    } catch (error) {
        showAlert(error.message, '错误', 'error');
    }
}

/**
 * 获取OpenRouter模型列表
 */
export async function fetchOpenRouterModels() {
    try {
        const response = await fetch('/api/openrouter/models');
        const models = await response.json();
        const datalist = document.getElementById('openrouter-models-list');
        
        if (datalist) {
            datalist.innerHTML = '';
            models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = model.name || model.id;
                datalist.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error fetching OpenRouter models:', error);
    }
}

/**
 * 获取DeepSeek模型列表
 */
export async function fetchDeepSeekModels() {
    try {
        const response = await fetch('/api/deepseek/models');
        const models = await response.json();
        const datalist = document.getElementById('deepseek-models-list');
        
        if (datalist) {
            datalist.innerHTML = '';
            models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = model.id;
                datalist.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error fetching DeepSeek models:', error);
    }
}

/**
 * 加载系统设置
 */
export async function loadSystemSettings() {
    try {
        const response = await fetch('/api/config');
        const data = await response.json();
        
        if (data.status === 'success') {
            const cfg = data.config;
            
            const setVal = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.value = val || '';
            };
            
            setVal('settings-key-deepseek', cfg.DEEPSEEK_API_KEY);
            setVal('settings-key-openai', cfg.OPENAI_API_KEY);
            setVal('settings-key-azure', cfg.AZURE_OPENAI_API_KEY);
            setVal('settings-azure-endpoint', cfg.AZURE_OPENAI_ENDPOINT);
            setVal('settings-azure-deployment', cfg.AZURE_OPENAI_DEPLOYMENT_NAME);
            setVal('settings-key-anthropic', cfg.ANTHROPIC_API_KEY);
            setVal('settings-key-gemini', cfg.GEMINI_API_KEY);
            setVal('settings-key-openrouter', cfg.OPENROUTER_API_KEY);
            setVal('settings-key-aliyun', cfg.ALIYUN_API_KEY);
            setVal('settings-key-tavily', cfg.TAVILY_API_KEY);
            setVal('settings-key-google', cfg.GOOGLE_API_KEY);
            setVal('settings-google-cx', cfg.GOOGLE_SEARCH_ENGINE_ID);
            setVal('settings-browser-path', cfg.BROWSER_PATH);
            
            // 处理多选搜索供应商
            if (cfg.SEARCH_PROVIDER) {
                const providers = cfg.SEARCH_PROVIDER.split(',').map(p => p.trim());
                document.querySelectorAll('.search-provider-checkbox').forEach(cb => {
                    cb.checked = providers.includes(cb.value);
                });
            }
        }
    } catch (error) {
        console.error('Failed to load config:', error);
    }
}

/**
 * 保存系统设置
 */
export async function saveSettings() {
    const getVal = (id) => {
        const el = document.getElementById(id);
        return el ? el.value.trim() : '';
    };
    
    const selectedProviders = Array.from(document.querySelectorAll('.search-provider-checkbox:checked'))
        .map(cb => cb.value)
        .join(',');

    const keys = {
        DEEPSEEK_API_KEY: getVal('settings-key-deepseek'),
        OPENAI_API_KEY: getVal('settings-key-openai'),
        AZURE_OPENAI_API_KEY: getVal('settings-key-azure'),
        AZURE_OPENAI_ENDPOINT: getVal('settings-azure-endpoint'),
        AZURE_OPENAI_DEPLOYMENT_NAME: getVal('settings-azure-deployment'),
        ANTHROPIC_API_KEY: getVal('settings-key-anthropic'),
        GEMINI_API_KEY: getVal('settings-key-gemini'),
        OPENROUTER_API_KEY: getVal('settings-key-openrouter'),
        ALIYUN_API_KEY: getVal('settings-key-aliyun'),
        TAVILY_API_KEY: getVal('settings-key-tavily'),
        GOOGLE_API_KEY: getVal('settings-key-google'),
        GOOGLE_SEARCH_ENGINE_ID: getVal('settings-google-cx'),
        BROWSER_PATH: getVal('settings-browser-path'),
        SEARCH_PROVIDER: selectedProviders
    };

    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(keys)
        });
        const data = await response.json();
        
        if (data.status === 'success') {
            showAlert('设置已保存', '成功');
            return true;
        } else {
            showAlert('保存失败: ' + data.message, '错误', 'error');
            return false;
        }
    } catch (error) {
        showAlert('保存失败: ' + error.message, '错误', 'error');
        return false;
    }
}
