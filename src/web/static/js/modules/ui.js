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
 * 切换高级配置Modal
 */
export function toggleAdvancedConfigModal() {
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
 * 更新Modal推理强度显示
 */
export function updateModalReasoningVisibility() {
    const backend = document.getElementById('modal-backend-select').value;
    const reasoningContainer = document.getElementById('modal-global-reasoning-container');
    const supportsReasoning = ['deepseek', 'openai', 'azure', 'openrouter'].includes(backend);
    
    if (supportsReasoning) {
        reasoningContainer.classList.remove('hidden');
    } else {
        reasoningContainer.classList.add('hidden');
    }
}

/**
 * 更新Agent配置UI（根据人数动态生成）
 */
export function updateModalAgentConfigsUI() {
    const container = document.getElementById('modal-agent-configs-container');
    const plannersCount = parseInt(document.getElementById('modal-planners-input').value) || 0;
    const auditorsCount = parseInt(document.getElementById('modal-auditors-input').value) || 0;
    
    // 处理 Planners
    for (let i = 0; i < 5; i++) {
        const id = `planner_${i}`;
        let el = container.querySelector(`[data-agent-wrapper="${id}"]`);
        if (i < plannersCount) {
            if (!el) {
                const div = createAgentConfigItem(`${t('role_planner')} ${i+1}`, id, 'bg-blue-50', 'bg-blue-500');
                container.appendChild(div);
            } else {
                // 更新标签语言
                const label = el.querySelector('h4');
                if (label) {
                    label.innerHTML = `<span class="w-2 h-2 bg-blue-500 rounded-full mr-2"></span>${t('role_planner')} ${i+1}`;
                }
            }
        } else if (el) {
            container.removeChild(el);
        }
    }

    // 处理 Auditors
    for (let i = 0; i < 5; i++) {
        const id = `auditor_${i}`;
        let el = container.querySelector(`[data-agent-wrapper="${id}"]`);
        if (i < auditorsCount) {
            if (!el) {
                const div = createAgentConfigItem(`${t('role_auditor')} ${i+1}`, id, 'bg-amber-50', 'bg-amber-500');
                container.appendChild(div);
            } else {
                // 更新标签语言
                const label = el.querySelector('h4');
                if (label) {
                    label.innerHTML = `<span class="w-2 h-2 bg-amber-500 rounded-full mr-2"></span>${t('role_auditor')} ${i+1}`;
                }
            }
        } else if (el) {
            container.removeChild(el);
        }
    }
}

/**
 * 创建Agent配置项
 * @param {string} label - 显示标签
 * @param {string} id - Agent ID
 * @param {string} bgColor - 背景颜色
 * @param {string} dotColor - 圆点颜色
 * @returns {HTMLElement} Agent配置DOM元素
 */
function createAgentConfigItem(label, id, bgColor, dotColor) {
    const div = document.createElement('div');
    div.className = `p-3 ${bgColor} rounded-lg border border-slate-200`;
    div.setAttribute('data-agent-wrapper', id);
    div.innerHTML = `
        <h4 class="text-xs font-bold text-slate-500 uppercase mb-2 flex items-center">
            <span class="w-2 h-2 ${dotColor} rounded-full mr-2"></span>${label}
        </h4>
        <div class="flex gap-2">
            <select class="agent-backend flex-1 text-xs p-1 border rounded" data-agent="${id}">
                <option value="default">${t('backend_default')}</option>
                <option value="deepseek">DeepSeek</option>
                <option value="openai">OpenAI</option>
                <option value="openrouter">OpenRouter</option>
                <option value="aliyun">Aliyun</option>
                <option value="ollama">Ollama</option>
            </select>
            <input type="text" class="agent-model flex-1 text-xs p-1 border rounded" placeholder="${t('agent_model_placeholder')}" data-agent="${id}">
        </div>
        <select class="agent-reasoning hidden text-[10px] p-1 border rounded mt-1 w-full" data-agent="${id}">
            <option value="">${t('reasoning_off')}</option>
            <option value="low">推理: Low</option>
            <option value="medium">推理: Medium</option>
            <option value="high">推理: High</option>
        </select>
    `;
    
    // 为后端选择添加监听器
    const select = div.querySelector('.agent-backend');
    const input = div.querySelector('.agent-model');
    const reasoningSelect = div.querySelector('.agent-reasoning');
    const updateList = () => {
        if (select.value === 'openrouter') {
            input.setAttribute('list', 'openrouter-models-list');
            reasoningSelect.classList.remove('hidden');
            fetchOpenRouterModels();
        } else if (select.value === 'deepseek') {
            input.setAttribute('list', 'deepseek-models-list');
            reasoningSelect.classList.add('hidden');
            fetchDeepSeekModels();
        } else {
            input.removeAttribute('list');
            reasoningSelect.classList.add('hidden');
        }
    };
    select.addEventListener('change', updateList);
    updateList(); // 初始检查
    
    return div;
}

/**
 * 获取OpenRouter模型列表
 */
export async function fetchOpenRouterModels() {
    if (State.getOpenRouterModelsFetched()) return;
    
    try {
        const models = await getOpenRouterModels();
        const datalist = document.getElementById('openrouter-models-list');
        datalist.innerHTML = '';
        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.id;
            option.textContent = model.name || model.id;
            datalist.appendChild(option);
        });
        State.setOpenRouterModelsFetched(true);
    } catch (error) {
        console.error('Error fetching OpenRouter models:', error);
    }
}

/**
 * 获取DeepSeek模型列表
 */
export async function fetchDeepSeekModels() {
    if (State.getDeepSeekModelsFetched()) return;
    
    try {
        const models = await getDeepSeekModels();
        const datalist = document.getElementById('deepseek-models-list');
        datalist.innerHTML = '';
        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.id;
            option.textContent = model.id;
            datalist.appendChild(option);
        });
        State.setDeepSeekModelsFetched(true);
    } catch (error) {
        console.error('Error fetching DeepSeek models:', error);
    }
}

/**
 * 切换预设下拉菜单
 */
export function togglePresetsDropdown() {
    const dropdown = document.getElementById("presets-dropdown");
    dropdown.classList.toggle("show");
    if (dropdown.classList.contains("show")) {
        loadPresets();
    }
}

/**
 * 加载预设列表（下拉菜单）
 */
export async function loadPresets() {
    try {
        const data = await getPresets();
        
        if (data.presets) {
            renderPresetsList(data.presets);
        }
    } catch (error) {
        console.error('Failed to load presets:', error);
    }
}

/**
 * 渲染预设列表
 * @param {Object} presets - 预设对象
 */
function renderPresetsList(presets) {
    const dropdownContainer = document.getElementById('presets-list-container');
    
    if (!dropdownContainer) return;

    dropdownContainer.innerHTML = '';

    const presetArray = Object.entries(presets || {});
    
    if (presetArray.length === 0) {
        const emptyHtml = `<div class="text-center text-gray-400 py-4 text-xs">暂无存档</div>`;
        dropdownContainer.innerHTML = emptyHtml;
        return;
    }

    for (const [name, config] of presetArray) {
        const dropdownItem = document.createElement('button');
        dropdownItem.onclick = () => { applyPreset(name); togglePresetsDropdown(); };
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
 * 应用预设
 * @param {string} name - 预设名称
 */
export async function applyPreset(name) {
    try {
        const data = await getPresets();
        const config = data.presets[name];
        
        if (config) {
            document.getElementById('backend-select').value = config.backend || 'deepseek';
            document.getElementById('global-model-input').value = config.global_model || '';
            document.getElementById('global-reasoning-input').value = config.global_reasoning || '';
            document.getElementById('rounds-input').value = config.rounds || 3;
            document.getElementById('planners-input').value = config.planners || 2;
            document.getElementById('auditors-input').value = config.auditors || 2;

            document.getElementById('backend-select').dispatchEvent(new Event('change'));

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

            showAlert(t('msg_preset_loaded'), t('title_success'));
        } else {
            showAlert('编制不存在', t('title_error'), 'error');
        }
    } catch (error) {
        showAlert(error.message, t('title_error'), 'error');
    }
}

/**
 * 保存当前配置为预设（从下拉菜单）
 */
export async function saveCurrentAsPreset() {
    let name = prompt(t('msg_preset_name_empty'));
    if (!name || !name.trim()) return;
    
    name = name.trim();

    const config = {
        backend: document.getElementById('backend-select').value,
        global_model: document.getElementById('global-model-input').value,
        global_reasoning: document.getElementById('global-reasoning-input').value,
        rounds: parseInt(document.getElementById('rounds-input').value),
        planners: parseInt(document.getElementById('planners-input').value),
        auditors: parseInt(document.getElementById('auditors-input').value),
        agents: {}
    };

    document.querySelectorAll('.agent-backend').forEach(select => {
        const agentId = select.dataset.agent;
        config.agents[agentId] = {
            backend: select.value,
            model: document.querySelector(`.agent-model[data-agent="${agentId}"]`).value,
            reasoning: document.querySelector(`.agent-reasoning[data-agent="${agentId}"]`).value
        };
    });

    try {
        await savePreset(name, config);
        showAlert(t('msg_preset_saved'), t('title_success'));
        loadPresets();
    } catch (error) {
        showAlert(error.message, t('title_error'), 'error');
    }
}

/**
 * 删除预设
 * @param {string} name - 预设名称
 */
export async function deletePreset(name) {
    if (!confirm(t('confirm_delete_preset'))) return;

    try {
        await apiDeletePreset(name);
        showAlert(t('msg_preset_deleted'), t('title_success'));
        loadPresets();
    } catch (error) {
        showAlert(error.message, t('title_error'), 'error');
    }
}

/**
 * 加载Modal预设列表
 */
export async function loadModalPresetsList() {
    const container = document.getElementById('modal-presets-list');
    try {
        const data = await getPresets();
        const presetArray = Object.entries(data.presets || {});
        
        if (presetArray.length > 0) {
            container.innerHTML = presetArray.map(([name, config]) => `
                <div class="bg-white p-3 rounded-lg border border-slate-200 hover:border-blue-300 transition flex items-center justify-between">
                    <div class="flex-1">
                        <div class="font-bold text-slate-700 mb-1">${name}</div>
                        <div class="text-xs text-slate-500">
                            ${config.backend || 'default'} | ${t('input_rounds_label')}: ${config.rounds || 3} | 
                            ${t('input_planners_label')}: ${config.planners || 2} | ${t('input_auditors_label')}: ${config.auditors || 2}
                        </div>
                    </div>
                    <div class="flex space-x-2">
                        <button onclick="window.applyModalPreset('${name}')" class="text-xs bg-blue-500 hover:bg-blue-600 text-white px-3 py-1 rounded transition" data-i18n="btn_load">
                            加载
                        </button>
                        <button onclick="window.deleteModalPreset('${name}')" class="text-xs bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded transition" data-i18n="btn_delete">
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
 * 应用Modal预设
 * @param {string} name - 预设名称
 */
export async function applyModalPreset(name) {
    try {
        const data = await getPresets();
        const config = data.presets[name];
        
        if (!config) {
            showAlert('编制不存在', t('title_error'), 'error');
            return;
        }
        
        document.getElementById('modal-backend-select').value = config.backend || 'deepseek';
        document.getElementById('modal-global-model-input').value = config.global_model || '';
        document.getElementById('modal-global-reasoning-input').value = config.global_reasoning || '';
        document.getElementById('modal-rounds-input').value = config.rounds || 3;
        document.getElementById('modal-planners-input').value = config.planners || 2;
        document.getElementById('modal-auditors-input').value = config.auditors || 2;
        
        updateModalReasoningVisibility();
        
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
        
        updateModalAgentConfigsUI();
        showAlert(t('msg_preset_loaded'), t('title_success'));
    } catch (error) {
        showAlert(error.message, t('title_error'), 'error');
    }
}

/**
 * 删除Modal预设
 * @param {string} name - 预设名称
 */
export async function deleteModalPreset(name) {
    if (!confirm(t('confirm_delete_preset'))) return;

    try {
        await apiDeletePreset(name);
        showAlert(t('msg_preset_deleted'), t('title_success'));
        loadModalPresetsList();
        loadPresets();
    } catch (error) {
        showAlert(error.message, t('title_error'), 'error');
    }
}

/**
 * 保存Modal预设
 */
export async function saveModalPreset() {
    const nameInput = document.getElementById('modal-new-preset-name');
    let name = nameInput.value.trim();
    
    if (!name) {
        showAlert(t('msg_preset_name_empty'), t('title_hint'), 'warning');
        return;
    }

    const config = {
        backend: document.getElementById('modal-backend-select').value,
        global_model: document.getElementById('modal-global-model-input').value,
        global_reasoning: document.getElementById('modal-global-reasoning-input').value,
        rounds: parseInt(document.getElementById('modal-rounds-input').value),
        planners: parseInt(document.getElementById('modal-planners-input').value),
        auditors: parseInt(document.getElementById('modal-auditors-input').value),
        agents: {}
    };

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
        await savePreset(name, config);
        showAlert(t('msg_preset_saved'), t('title_success'));
        nameInput.value = ''; 
        loadModalPresetsList();
        loadPresets();
    } catch (error) {
        showAlert(error.message, t('title_error'), 'error');
    }
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
 * 加载系统设置
 */
export async function loadSystemSettings() {
    try {
        const data = await getConfig();
        if (data.status === 'success') {
            const cfg = data.config;
            document.getElementById('settings-key-deepseek').value = cfg.DEEPSEEK_API_KEY || '';
            document.getElementById('settings-key-openai').value = cfg.OPENAI_API_KEY || '';
            document.getElementById('settings-key-azure').value = cfg.AZURE_OPENAI_API_KEY || '';
            document.getElementById('settings-azure-endpoint').value = cfg.AZURE_OPENAI_ENDPOINT || '';
            document.getElementById('settings-azure-deployment').value = cfg.AZURE_OPENAI_DEPLOYMENT_NAME || '';
            document.getElementById('settings-key-anthropic').value = cfg.ANTHROPIC_API_KEY || '';
            document.getElementById('settings-key-gemini').value = cfg.GEMINI_API_KEY || '';
            document.getElementById('settings-key-openrouter').value = cfg.OPENROUTER_API_KEY || '';
            document.getElementById('settings-key-aliyun').value = cfg.ALIYUN_API_KEY || '';
            document.getElementById('settings-key-tavily').value = cfg.TAVILY_API_KEY || '';
            document.getElementById('settings-key-google').value = cfg.GOOGLE_API_KEY || '';
            document.getElementById('settings-google-cx').value = cfg.GOOGLE_SEARCH_ENGINE_ID || '';
            document.getElementById('settings-browser-path').value = cfg.BROWSER_PATH || '';
            
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
 * @returns {Promise<boolean>} 是否保存成功
 */
export async function saveSettings() {
    const selectedProviders = Array.from(document.querySelectorAll('.search-provider-checkbox:checked'))
        .map(cb => cb.value)
        .join(',');

    const keys = {
        DEEPSEEK_API_KEY: document.getElementById('settings-key-deepseek').value.trim(),
        OPENAI_API_KEY: document.getElementById('settings-key-openai').value.trim(),
        AZURE_OPENAI_API_KEY: document.getElementById('settings-key-azure').value.trim(),
        AZURE_OPENAI_ENDPOINT: document.getElementById('settings-azure-endpoint').value.trim(),
        AZURE_OPENAI_DEPLOYMENT_NAME: document.getElementById('settings-azure-deployment').value.trim(),
        ANTHROPIC_API_KEY: document.getElementById('settings-key-anthropic').value.trim(),
        GEMINI_API_KEY: document.getElementById('settings-key-gemini').value.trim(),
        OPENROUTER_API_KEY: document.getElementById('settings-key-openrouter').value.trim(),
        ALIYUN_API_KEY: document.getElementById('settings-key-aliyun').value.trim(),
        TAVILY_API_KEY: document.getElementById('settings-key-tavily').value.trim(),
        GOOGLE_API_KEY: document.getElementById('settings-key-google').value.trim(),
        GOOGLE_SEARCH_ENGINE_ID: document.getElementById('settings-google-cx').value.trim(),
        BROWSER_PATH: document.getElementById('settings-browser-path').value.trim(),
        SEARCH_PROVIDER: selectedProviders
    };

    try {
        const data = await saveConfig(keys);
        if (data.status === 'success') {
            showAlert(t('msg_config_saved'), t('title_success'));
            return true;
        } else {
            showAlert(data.message, t('title_error'), 'error');
            return false;
        }
    } catch (error) {
        showAlert(error.message, t('title_error'), 'error');
        return false;
    }
}

/**
 * 加载用户信息（占位函数）
 */
export async function loadUserInfo() {
    // TODO: 实现用户信息加载逻辑
    console.log('Loading user info...');
}

/**
 * 加载角色列表
 */
export async function loadRolesList() {
    const listContainer = document.getElementById('roles-list-container');
    try {
        const data = await getRoles();
        
        if (!data.roles || data.roles.length === 0) {
            listContainer.innerHTML = '<div class="text-center text-slate-400 py-8">暂无自定义角色</div>';
            return;
        }
        
        listContainer.innerHTML = '';
        
        data.roles.forEach(role => {
            const card = document.createElement('div');
            card.className = 'bg-white border border-slate-200 rounded-lg p-4 hover:shadow-md transition';
            card.innerHTML = `
                <div class="flex items-start justify-between">
                    <div class="flex-1">
                        <h4 class="font-bold text-slate-800 text-base mb-1">${role.display_name}</h4>
                        <p class="text-sm text-slate-600 mb-2">${role.description || '无描述'}</p>
                        <div class="flex items-center space-x-2 text-xs text-slate-500">
                            <span class="bg-slate-100 px-2 py-1 rounded">内部名: ${role.name}</span>
                            <span class="bg-blue-100 text-blue-700 px-2 py-1 rounded">阶段: ${role.stages_count || 0}</span>
                        </div>
                    </div>
                    <div class="flex flex-col space-y-2 ml-4">
                        <button onclick="window.showRoleDetail('${role.name}')" 
                                class="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded-lg transition">
                            ${t('role_btn_detail')}
                        </button>
                        <button onclick="window.reloadRole('${role.name}')" 
                                class="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-xs rounded-lg transition">
                            ${t('role_btn_reload')}
                        </button>
                    </div>
                </div>
            `;
            listContainer.appendChild(card);
        });
    } catch (error) {
        listContainer.innerHTML = `<div class="text-center text-red-400 py-8">加载失败: ${error.message}</div>`;
    }
}

/**
 * 显示角色详情
 * @param {string} roleName - 角色名称
 */
export async function showRoleDetail(roleName) {
    try {
        const data = await getRoleDetail(roleName);
        
        if (data.status !== 'success') {
            showAlert(t('msg_load_failed') + ': ' + data.message, t('title_error'), 'error');
            return;
        }
        
        const role = data.role;
        let contentHtml = '';
        
        // 阶段信息
        if (role.stages && role.stages.length > 0) {
            contentHtml += `
                <section class="space-y-2">
                    <h4 class="text-sm font-bold text-slate-700">${t('role_stages')}</h4>
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
                    <h4 class="text-sm font-bold text-slate-700">${t('role_parameters')}</h4>
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
                    <h4 class="text-sm font-bold text-slate-700">${t('role_prompt_preview')}</h4>
                    <div class="bg-slate-50 p-3 rounded-lg border border-slate-200 max-h-96 overflow-y-auto">
                        ${promptContent}
                    </div>
                </section>
            `;
        }
        
        document.getElementById('detail-role-name').textContent = role.display_name;
        document.getElementById('detail-role-desc').textContent = role.description;
        document.getElementById('detail-role-content').innerHTML = contentHtml;
        
        // 添加编辑和删除按钮
        const detailHeader = document.getElementById('role-detail-modal').querySelector('.flex.justify-between');
        const existingBtns = detailHeader.querySelector('.role-action-btns');
        if (existingBtns) {
            existingBtns.remove();
        }
        
        const btnContainer = document.createElement('div');
        btnContainer.className = 'role-action-btns flex space-x-2 mr-2';
        
        const editBtn = document.createElement('button');
        editBtn.className = 'px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg transition text-sm';
        editBtn.innerHTML = '✏️ 编辑';
        editBtn.onclick = () => openRoleEditor(roleName);
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg transition text-sm';
        deleteBtn.innerHTML = '🗑️ 删除';
        deleteBtn.onclick = () => deleteRole(roleName);
        
        btnContainer.appendChild(editBtn);
        btnContainer.appendChild(deleteBtn);
        
        const closeBtn = detailHeader.querySelector('button');
        closeBtn.parentElement.insertBefore(btnContainer, closeBtn);
        
        document.getElementById('role-detail-modal').classList.remove('hidden');
    } catch (error) {
        console.error('Failed to load role detail:', error);
        showAlert(t('msg_load_failed') + ': ' + error.message, t('title_error'), 'error');
    }
}

/**
 * 关闭角色详情Modal
 */
export function closeRoleDetail() {
    document.getElementById('role-detail-modal').classList.add('hidden');
}

/**
 * 删除角色
 * @param {string} roleName - 角色名称
 */
export async function deleteRole(roleName) {
    const confirmed = confirm(`确定要删除角色 "${roleName}" 吗？\n\n此操作将删除角色配置文件和所有相关Prompt文件，且不可恢复！`);
    if (!confirmed) return;
    
    try {
        const data = await apiDeleteRole(roleName);
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
 * @param {string} roleName - 角色名称
 */
export async function reloadRole(roleName) {
    // TODO: API endpoint not implemented yet
    showAlert('角色重载功能暂未实现', t('title_info'));
    return;
    /* try {
        const data = await apiReloadRole(roleName);
        if (data.status === 'success') {
            showAlert(t('role_reload_success'), t('title_success'));
            await loadRolesList();
            closeRoleDetail();
        } else {
            showAlert(t('role_reload_failed') + ': ' + data.message, t('title_error'), 'error');
        }
    } catch (error) {
        console.error('Failed to reload role:', error);
        showAlert(t('role_reload_failed') + ': ' + error.message, t('title_error'), 'error');
    }
}

// 角色编辑器相关状态
let currentEditingRole = null;

/**
 * 打开角色编辑器
 * @param {string} roleName - 角色名称
 */
export async function openRoleEditor(roleName) {
    // TODO: API endpoint not implemented yet
    showAlert('角色编辑功能暂未实现', t('title_info'));
    return;
    /* try {
        const data = await getRoleConfig(roleName);
        
        if (data.status !== 'success') {
            showAlert('加载配置失败: ' + data.message, t('title_error'), 'error');
            return;
        }
        
        currentEditingRole = roleName;
        
        document.getElementById('role-edit-modal').classList.remove('hidden');
        document.getElementById('edit-role-name').textContent = roleName;
        document.getElementById('role-yaml-editor').value = data.data.yaml_content;
        
        const promptsContainer = document.getElementById('prompt-editors');
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
    } catch (error) {
        console.error('Failed to load role config:', error);
        showAlert('加载配置失败: ' + error.message, t('title_error'), 'error');
    }
}

/**
 * 关闭角色编辑器
 */
export function closeRoleEditor() {
    document.getElementById('role-edit-modal').classList.add('hidden');
    currentEditingRole = null;
}

/**
 * 验证角色配置
 */
export async function validateRoleConfig() {
    // TODO: API endpoint not implemented yet
    showAlert('配置验证功能暂未实现', t('title_info'));
    return;
    /* const yamlContent = document.getElementById('role-yaml-editor').value;
    
    try {
        const data = await apiValidateRoleConfig(yamlContent);
        if (data.status === 'success' && data.valid) {
            showAlert('✅ 配置验证通过', t('title_success'));
        } else {
            showAlert('❌ 配置验证失败:\n' + data.error, t('title_error'), 'error');
        }
    } catch (error) {
        showAlert('验证失败: ' + error.message, t('title_error'), 'error');
    } */

/**
 * 保存角色配置
 */
export async function saveRoleConfig() {
    if (!currentEditingRole) return;
    
    const yamlContent = document.getElementById('role-yaml-editor').value;
    const prompts = {};
    
    document.querySelectorAll('.prompt-editor').forEach(textarea => {
        const stageName = textarea.getAttribute('data-stage');
        prompts[stageName] = textarea.value;
    });
    
    try {
        const data = await updateRoleConfig(currentEditingRole, yamlContent, prompts);
        if (data.status === 'success') {
            showAlert('✅ 角色配置已保存并重载', t('title_success'));
            closeRoleEditor();
            await loadRolesList();
            closeRoleDetail();
        } else {
            showAlert('❌ 保存失败:\n' + data.message, t('title_error'), 'error');
        }
    } catch (error) {
        console.error('Failed to save role config:', error);
        showAlert('保存失败: ' + error.message, t('title_error'), 'error');
    }
}

// 角色设计师相关状态
let currentDesignerStep = 1;
let generatedRoleDesign = null;

/**
 * 打开角色设计师
 */
export function openRoleDesigner() {
    currentDesignerStep = 1;
    generatedRoleDesign = null;
    document.getElementById('role-requirement-input').value = '';
    document.getElementById('role-designer-modal').classList.remove('hidden');
    updateDesignerStep(1);
}

/**
 * 关闭角色设计师
 */
export function closeRoleDesigner() {
    document.getElementById('role-designer-modal').classList.add('hidden');
}

/**
 * 更新设计师步骤（占位函数 - 具体实现在HTML中）
 * @param {number} step - 步骤号
 */
function updateDesignerStep(step) {
    currentDesignerStep = step;
    // 具体的DOM更新逻辑保留在HTML中
    console.log('Designer step updated to:', step);
}

/**
 * 设计师返回
 */
export function designerGoBack() {
    if (currentDesignerStep === 3) {
        updateDesignerStep(1);
    }
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
 * 渲染角色预览（占位函数 - 具体实现在HTML中）
 * @param {Object} design - 角色设计对象
 */
function renderRolePreview(design) {
    // 具体的DOM更新逻辑保留在HTML中
    console.log('Rendering role preview:', design);
}

/**
 * 保存新角色
 */
export async function saveNewRole() {
    try {
        const updatedDesign = {
            ...generatedRoleDesign,
            display_name: document.getElementById('preview-display-name').value,
            role_description: document.getElementById('preview-description').value
        };
        
        const data = await createRole(updatedDesign);
        
        if (data.success) {
            showAlert(`✅ 成功创建角色: ${data.display_name}`, '成功', 'success');
            closeRoleDesigner();
            if (typeof loadRoles === 'function') {
                loadRoles();
            }
        } else {
            showAlert('创建失败: ' + (data.message || '未知错误'), '错误', 'error');
        }
    } catch (error) {
        console.error('Failed to create role:', error);
        showAlert('创建失败: ' + error.message, '错误', 'error');
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
