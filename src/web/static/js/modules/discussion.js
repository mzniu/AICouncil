/**
 * discussion.js
 * 讨论控制模块 - 处理讨论流程、报告生成和实时状态更新
 * 
 * 核心功能：
 * - startDiscussion: 启动讨论会话
 * - stopDiscussion: 停止讨论
 * - reReport: 重新生成报告
 * - sendIntervention: 人工介入
 * - updateStatusUI: 更新运行状态UI
 * - pollStatus: 定时轮询后端状态
 * - renderMessage: 渲染讨论消息
 * - handleFinalReport: 处理最终报告
 */

import { showAlert, showConfirm } from './core/utils.js';
import * as API from './core/api.js';
import * as State from './core/state.js';

// ==================== DOM元素引用 ====================
let flowContainer = null;
let logContainer = null;
let reportIframe = null;
let startBtn = null;
let stopBtn = null;
let statusDot = null;
let statusText = null;
let interventionArea = null;

// ==================== 常量定义 ====================
const POLL_INTERVAL = 1000; // 轮询间隔（毫秒）
let pollTimer = null;

/**
 * 初始化DOM引用
 */
export function initDOMReferences() {
    flowContainer = document.getElementById('discussion-flow');
    logContainer = document.getElementById('log-container');
    reportIframe = document.getElementById('report-iframe');
    startBtn = document.getElementById('start-btn');
    stopBtn = document.getElementById('stop-btn');
    statusDot = document.getElementById('status-dot');
    statusText = document.getElementById('status-text');
    interventionArea = document.getElementById('intervention-area');
}

// ==================== 讨论控制函数 ====================

/**
 * 启动讨论会话
 * - 收集表单参数和Agent配置
 * - 验证输入
 * - 重置UI并发起API请求
 */
export async function startDiscussion() {
    if (State.getIsRunning()) return;
    
    const issue = document.getElementById('issue-input').value.trim();
    const backend = document.getElementById('backend-select').value;
    const model = document.getElementById('global-model-input').value;
    const reasoningEffort = document.getElementById('global-reasoning-input').value;
    const rounds = document.getElementById('rounds-input').value;
    const planners = document.getElementById('planners-input').value;
    const auditors = document.getElementById('auditors-input').value;

    // 收集 Agent 配置
    const agentConfigs = {};
    document.querySelectorAll('.agent-backend').forEach(select => {
        const agentId = select.dataset.agent;
        const agentBackend = select.value;
        const modelEl = document.querySelector(`.agent-model[data-agent="${agentId}"]`);
        const reasoningEl = document.querySelector(`.agent-reasoning[data-agent="${agentId}"]`);
        
        const agentModel = modelEl ? modelEl.value.trim() : '';
        const agentReasoning = reasoningEl ? reasoningEl.value : '';
        
        if (agentBackend !== 'default' || agentModel !== '' || agentReasoning !== '') {
            agentConfigs[agentId] = {
                type: agentBackend === 'default' ? backend : agentBackend,
                model: agentModel || undefined,
                reasoning: agentReasoning ? { effort: agentReasoning } : undefined
            };
        }
    });

    if (!issue) {
        showAlert(t('msg_input_issue'), t('title_hint'));
        return;
    }

    // 设置运行状态
    State.setIsRunning(true);
    
    // 重置输入框高度
    const issueInput = document.getElementById('issue-input');
    issueInput.style.height = 'auto';

    // 清空旧内容并显示初始化状态
    flowContainer.innerHTML = `<div class="flex justify-center my-4 animate-pulse"><span class="bg-blue-100 text-blue-600 px-4 py-1 rounded-full text-sm font-medium">${t('msg_initializing_hall')}</span></div>`;
    logContainer.innerHTML = `<div class="text-slate-500 italic">${t('msg_connecting_backend')}</div>`;
    if (reportIframe) {
        reportIframe.srcdoc = '<div style="color:#94a3b8; font-style:italic; text-align:center; margin-top:100px; font-family:sans-serif;"></div>';
    }
    setLayoutMode('discussion');
    State.setIsReportingPhase(false);
    State.setLastEventCount(0);
    State.setLastLogCount(0);
    State.setCurrentProgress(0);
    document.getElementById('progress-bar').style.width = '0%';
    document.getElementById('progress-percentage').innerText = '0%';
    
    // 切换到讨论模式布局
    setLayoutMode('discussion');

    try {
        const data = await API.startDiscussion(
            issue,
            backend,
            model,
            reasoningEffort,
            rounds,
            planners,
            auditors,
            agentConfigs,
            State.getIsOrchestratorMode()
        );
        
        if (data.status === 'ok') {
            console.log('讨论已启动');
        } else {
            State.setIsRunning(false);
            updateStatusUI({ is_running: false });
            showAlert(t('msg_start_failed') + ': ' + data.message, t('title_error'), 'error');
        }
    } catch (error) {
        console.error('Start error:', error);
        State.setIsRunning(false);
        updateStatusUI({ is_running: false });
        showAlert(t('msg_request_failed'), t('title_error'), 'error');
    }
}

/**
 * 停止讨论会话
 * - 显示确认对话框
 * - 调用停止API
 */
export async function stopDiscussion() {
    if (!State.getIsRunning()) return;
    
    const confirmed = await showConfirm(t('msg_stop_confirm'), t('msg_stop_title'));
    if (!confirmed) return;
    
    try {
        const data = await API.stopDiscussion();
        if (data.status === 'ok') {
            State.setIsRunning(false);
            updateStatusUI({ is_running: false });
        }
    } catch (error) {
        console.error('Stop error:', error);
    }
}

/**
 * 重新生成报告
 * - 收集Agent配置
 * - 显示加载状态
 * - 调用reReport API
 */
export async function reReport() {
    if (State.getIsRunning()) return;
    
    const backend = document.getElementById('backend-select').value;
    const model = document.getElementById('global-model-input').value;
    const reasoningEffort = document.getElementById('global-reasoning-input').value;
    
    // 收集 Agent 配置
    const agentConfigs = {};
    document.querySelectorAll('.agent-backend').forEach(select => {
        const agentId = select.dataset.agent;
        const agentBackend = select.value;
        const modelEl = document.querySelector(`.agent-model[data-agent="${agentId}"]`);
        const reasoningEl = document.querySelector(`.agent-reasoning[data-agent="${agentId}"]`);
        
        const agentModel = modelEl ? modelEl.value.trim() : '';
        const agentReasoning = reasoningEl ? reasoningEl.value : '';
        
        if (agentBackend !== 'default' || agentModel !== '' || agentReasoning !== '') {
            agentConfigs[agentId] = {
                type: agentBackend === 'default' ? backend : agentBackend,
                model: agentModel || undefined,
                reasoning: agentReasoning ? { effort: agentReasoning } : undefined
            };
        }
    });
    
    // 清空旧报告内容并显示加载状态
    if (reportIframe) {
        reportIframe.srcdoc = '<div style="color:#94a3b8; font-style:italic; text-align:center; margin-top:100px; font-family:sans-serif;"></div>';
    }
    State.setIsReportingPhase(true);
    toggleReportLoading(true, t('msg_re_reporting'), t('msg_re_reporting_sub').replace('{backend}', backend));
    
    try {
        const data = await API.reReport(backend, model, reasoningEffort, agentConfigs);
        if (data.status !== 'ok') {
            const errorMsg = data.message || t('msg_request_failed');
            showAlert(errorMsg, t('title_error'), 'error');
            toggleReportLoading(false);
            State.setIsReportingPhase(false);
        }
    } catch (error) {
        console.error('Re-report error:', error);
        showAlert(t('msg_request_failed'), t('title_error'), 'error');
        toggleReportLoading(false);
        State.setIsReportingPhase(false);
    }
}

/**
 * 发送人工介入消息
 */
export async function sendIntervention() {
    const input = document.getElementById('intervention-input');
    const content = input.value.trim();
    if (!content) return;

    try {
        const data = await API.sendIntervention(content);
        if (data.status === 'ok') {
            input.value = '';
            showAlert(t('msg_intervention_sent'), t('title_success'));
        } else {
            showAlert(t('msg_intervention_failed') + ': ' + data.message, t('title_error'), 'error');
        }
    } catch (error) {
        console.error('Intervention error:', error);
        showAlert(t('msg_intervention_failed'), t('title_error'), 'error');
    }
}

// ==================== 状态更新函数 ====================

/**
 * 更新状态UI
 * @param {Object} statusData - 从/api/status获取的状态数据
 */
export function updateStatusUI(statusData) {
    const running = statusData.is_running;
    const config = statusData.config;
    State.setIsRunning(running);
    
    const reportLoader = document.getElementById('report-loader');
    const loaderText = document.getElementById('loader-text');
    const loaderSubtext = document.getElementById('loader-subtext');
    const browserWarning = document.getElementById('browser-warning');
    
    // 更新浏览器状态警告
    if (statusData.browser_found === false) {
        browserWarning.classList.remove('hidden');
    } else {
        browserWarning.classList.add('hidden');
    }
    
    // 如果正在运行且输入框为空（说明是刷新页面），则填充配置
    if (running && config) {
        const issueInput = document.getElementById('issue-input');
        if (!issueInput.value.trim()) {
            issueInput.value = config.issue || '';
            document.getElementById('backend-select').value = config.backend || 'deepseek';
            document.getElementById('rounds-input').value = config.rounds || 3;
            document.getElementById('planners-input').value = config.planners || 2;
            document.getElementById('auditors-input').value = config.auditors || 2;
            // 触发高度自适应
            issueInput.style.height = '';
            issueInput.style.height = issueInput.scrollHeight + 'px';
        }
    }

    if (running) {
        // 检查是否正在生成报告
        const currentText = loaderText ? loaderText.innerText.toLowerCase() : '';
        const isReporting = State.getIsReportingPhase() || (
            currentText.includes('报告') || 
            currentText.includes('撰写') || 
            currentText.includes('report') || 
            currentText.includes('writing') ||
            currentText.includes('达成共识') ||
            currentText.includes('consensus')
        );

        // 只有在还没有报告内容且不在报告生成阶段时，才在运行状态下强制切换到讨论模式
        // 这样可以防止报告生成过程中布局忽大忽小
        if (!isReporting && (!reportIframe.srcdoc || reportIframe.srcdoc.includes('italic'))) {
            setLayoutMode('discussion');
        } else if (isReporting) {
            setLayoutMode('report');
        }
        
        startBtn.disabled = true;
        startBtn.innerText = t('status_processing');
        stopBtn.classList.remove('hidden');
        statusDot.className = 'w-3 h-3 bg-green-500 rounded-full animate-pulse';
        statusText.innerText = t('status_running');
        interventionArea.classList.remove('hidden');

        // 如果是刷新页面且还没有加载出事件，显示恢复状态
        if (State.getLastEventCount() === 0 && flowContainer.innerHTML.trim() === '') {
            flowContainer.innerHTML = `<div class="flex justify-center my-4 animate-pulse"><span class="bg-blue-100 text-blue-600 px-4 py-1 rounded-full text-sm font-medium">${t('msg_restoring_progress')}</span></div>`;
        }

        // 显示报告加载遮罩
        if (reportLoader && (isReporting || !reportIframe.srcdoc || reportIframe.srcdoc.includes('italic'))) {
            let targetText = t('loader_text');
            let targetSub = t('loader_subtext');
            
            if (isReporting) {
                if (loaderText.innerText && !loaderText.innerText.includes(t('loader_text'))) {
                    targetText = loaderText.innerText;
                    targetSub = loaderSubtext.innerText;
                } else {
                    targetText = t('msg_writing_report');
                    targetSub = t('msg_writing_report_sub');
                }
            }
            toggleReportLoading(true, targetText, targetSub);
        }
    } else {
        State.setIsReportingPhase(false);
        startBtn.disabled = false;
        startBtn.innerText = t('btn_start');
        stopBtn.classList.add('hidden');
        statusDot.className = 'w-3 h-3 bg-blue-500 rounded-full';
        statusText.innerText = t('status_ready');
        interventionArea.classList.add('hidden');
        toggleReportLoading(false);

        // 如果不运行，且已经有报告内容，则切换到报告模式
        if (reportIframe && reportIframe.srcdoc && reportIframe.srcdoc.length > 200 && !reportIframe.srcdoc.includes('italic')) {
            setLayoutMode('report');
        }
    }
    updateRoundUI();
}

/**
 * 更新轮次显示UI
 */
export function updateRoundUI() {
    const roundInfo = document.getElementById('round-info');
    const maxRounds = parseInt(document.getElementById('rounds-input').value) || 3;
    if (State.getIsRunning()) {
        roundInfo.innerText = `Round ${State.getCurrentRound()} / ${maxRounds}`;
        roundInfo.classList.remove('hidden');
    } else {
        roundInfo.classList.add('hidden');
    }
}

/**
 * 更新进度条
 * @param {Object} event - 事件对象
 */
export function updateProgress(event) {
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-percentage');
    const maxRounds = parseInt(document.getElementById('rounds-input').value) || 3;
    
    let targetProgress = State.getCurrentProgress();

    if (event.type === 'system_start') {
        targetProgress = 0;
        State.setCurrentRound(1);
    } else if (event.type === 'round_start') {
        State.setCurrentRound(event.round);
        targetProgress = ((State.getCurrentRound() - 1) / maxRounds) * 100;
    } else if (event.type === 'agent_action') {
        if (event.role_type === 'Reporter') {
            targetProgress = 95;
            setLayoutMode('report');
        }
    } else if (event.type === 'role_designer_reasoning' || event.type === 'role_designer_content') {
        // 处理角色设计师的实时更新
        handleRoleDesignerEvent(event);
    } else if (event.type === 'discussion_complete' || event.type === 'final_report') {
        targetProgress = 100;
        setLayoutMode('report');
    }

    // 确保进度不会超过 100% 或出现异常值
    targetProgress = Math.min(100, Math.max(0, targetProgress));

    if (targetProgress > State.getCurrentProgress() || event.type === 'system_start') {
        State.setCurrentProgress(targetProgress);
        progressBar.style.width = `${State.getCurrentProgress()}%`;
        progressText.innerText = `${Math.round(State.getCurrentProgress())}%`;
    }
    updateRoundUI();
}

// ==================== 轮询函数 ====================

/**
 * 定时轮询后端状态和事件
 */
export async function pollStatus() {
    try {
        const data = await API.getStatus();
        updateStatusUI(data);
        
        if (data.events) {
            const events = data.events.slice(State.getLastEventCount());
            events.forEach(event => {
                appendEvent(event);
                updateProgress(event);
                if (event.type === 'final_report') {
                    handleFinalReport(event);
                }
            });
            State.setLastEventCount(data.events.length);
        }
        
        if (data.logs) {
            const logs = data.logs.slice(State.getLastLogCount());
            logs.forEach(log => appendLog(log));
            State.setLastLogCount(data.logs.length);
        }
    } catch (error) {
        console.error('Poll status error:', error);
    }
}

/**
 * 启动轮询
 */
export function startPolling() {
    if (!pollTimer) {
        pollTimer = setInterval(pollStatus, POLL_INTERVAL);
    }
}

/**
 * 停止轮询
 */
export function stopPolling() {
    if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
    }
}

// ==================== 消息渲染函数 ====================

/**
 * HTML转义
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * 追加事件到讨论流容器
 * @param {Object} event - 事件对象
 */
function appendEvent(event) {
    // 如果是第一个事件，且容器内只有初始化消息，则清空
    if (State.getLastEventCount() === 0 && flowContainer.querySelector('.animate-pulse')) {
        flowContainer.innerHTML = '';
    }

    if (event.chunk_id) {
        let existing = document.getElementById(`event-${event.chunk_id}`);
        if (existing) {
            const contentDiv = existing.querySelector('.event-content');
            const reasoningDiv = existing.querySelector('.event-reasoning');
            
            if (event.reasoning && reasoningDiv) {
                reasoningDiv.textContent += event.reasoning;
                const trimmed = reasoningDiv.textContent.replace(/^\s+/, '');
                if (reasoningDiv.textContent !== trimmed) {
                    reasoningDiv.textContent = trimmed;
                }
                reasoningDiv.closest('.reasoning-wrapper').classList.remove('hidden');
            }
            if (event.content && contentDiv) {
                const oldRaw = contentDiv.dataset.raw || "";
                const newRaw = oldRaw + event.content;
                
                // 自动收缩推理 (Reasoning)
                if (reasoningDiv && !reasoningDiv.classList.contains('collapsed')) {
                    if (event.content.trim() && !event.content.includes('SEARCH PROGRESS')) {
                        const header = reasoningDiv.closest('.reasoning-wrapper').querySelector('.cursor-pointer');
                        if (header) toggleReasoning(header);
                    }
                }

                // 自动收缩搜索 (Search)
                if (newRaw.includes('重新生成最终方案') || newRaw.includes('Regenerating final plan')) {
                    const hasEndMarker = newRaw.includes('搜索完成') || 
                                       newRaw.includes('搜索已完成') || 
                                       newRaw.includes('重新生成最终方案') ||
                                       newRaw.includes('Search completed') ||
                                       newRaw.includes('Search finished') ||
                                       newRaw.includes('Regenerating final plan');
                    
                    if (hasEndMarker) {
                        const searchCard = existing.querySelector('.search-progress-card');
                        if (searchCard) {
                            const searchContent = searchCard.querySelector('.search-content');
                            if (!searchContent.classList.contains('collapsed')) {
                                const header = searchCard.querySelector('.cursor-pointer');
                                if (header) toggleSearchCard(header);
                            }
                        }
                    }
                }

                contentDiv.dataset.raw = newRaw;
                
                let text = contentDiv.dataset.raw;
                // 实时清理 Markdown 标签
                if (text.includes('```')) {
                    text = text.replace(/^(\s*```json\s*|\s*```\s*)/, '');
                    text = text.replace(/(\s*```\s*)$/, '');
                }
                
                contentDiv.innerHTML = formatContent(text);
            }
            return;
        }
    }

    const div = document.createElement('div');
    if (event.chunk_id) div.id = `event-${event.chunk_id}`;
    
    if (event.type === 'system_start') {
        // 捕获并保存当前会话ID
        if (event.session_id) {
            State.setCurrentSessionId(event.session_id);
            console.log('[Discussion] Session ID captured:', event.session_id);
        }
        
        div.className = 'space-y-4 my-6';
        div.innerHTML = `
            <div class="bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl p-5 shadow-xl border border-slate-700 text-white">
                <div class="flex items-center mb-3">
                    <span class="text-xl mr-2">🎯</span>
                    <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider">${t('input_issue_label')}</h4>
                </div>
                <p class="text-lg font-medium leading-relaxed">${event.issue || t('msg_history_empty')}</p>
                <div class="mt-4 pt-4 border-t border-slate-700/50 flex justify-between items-center text-[10px] text-slate-500 uppercase tracking-widest">
                    <span>AI Council Protocol v1.0</span>
                    <span>${new Date().toLocaleTimeString()}</span>
                </div>
            </div>
            <div class="flex justify-center">
                <span class="bg-slate-800 text-white px-4 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest shadow-lg shadow-slate-200 border border-slate-700">System Startup</span>
            </div>
        `;
    } else if (event.type === 'round_start') {
        div.className = 'flex justify-center my-4';
        div.innerHTML = `<span class="bg-slate-200 text-slate-600 px-3 py-0.5 rounded-full text-xs font-bold uppercase">Round ${event.round}</span>`;
    } else if (event.type === 'agent_action') {
        const roleClass = `role-${event.role_type.toLowerCase()}`;
        const roleIcon = getIcon(event.role_type);
        
        // 如果是记录员（Reporter）开始行动，更新报告窗口的加载文字
        if (event.role_type === 'Reporter') {
            State.setIsReportingPhase(true);
            toggleReportLoading(true, t('msg_writing_report'), t('msg_writing_report_sub'));
            setLayoutMode('report');
        }

        const hasReasoning = !!event.reasoning;
        const reasoningContent = (event.reasoning || '').replace(/^\s+/, '');
        const content = event.content || '';

        div.className = `bg-white rounded-lg shadow-sm p-4 border-l-4 ${roleClass} text-base discussion-card`;
        div.innerHTML = `
            <div class="flex items-center mb-2">
                <span class="text-xl mr-2">${roleIcon}</span>
                <div>
                    <h4 class="font-bold text-slate-800 text-base">${event.agent_name}</h4>
                </div>
            </div>
            <div class="reasoning-wrapper mb-2 ${hasReasoning ? '' : 'hidden'}">
                <div class="flex items-center justify-between px-2 py-1 bg-amber-100/50 rounded-t-lg border-l-2 border-amber-200 cursor-pointer hover:bg-amber-200/50 transition-colors" onclick="window.toggleReasoning(this)">
                    <span class="text-[10px] text-amber-700 font-bold uppercase tracking-wider flex items-center">
                        <span class="toggle-icon mr-1">▼</span> ${t('msg_thinking_process')}
                    </span>
                </div>
                <div class="event-reasoning p-3 bg-amber-50/40 border-l-2 border-amber-200 text-[13px] leading-relaxed text-slate-600 italic whitespace-pre-wrap relative rounded-b-lg">
                    ${reasoningContent}
                </div>
            </div>
            <div class="text-slate-600 leading-relaxed text-base event-content markdown-body">${formatContent(content, event.role_type)}</div>
        `;
    } else if (event.type === 'final_report') {
        // 进入报告生成阶段
        State.setIsReportingPhase(true);
        const loaderText = document.getElementById('loader-text');
        if (loaderText && !loaderText.innerText.includes('撰写') && !loaderText.innerText.includes('Writing')) {
            toggleReportLoading(true, t('msg_consensus_reached'), t('msg_consensus_reached_sub'));
        }
        setLayoutMode('report');
        return; // 报告内容由 handleFinalReport 处理
    }
    
    flowContainer.appendChild(div);
}

/**
 * 切换推理内容折叠
 */
window.toggleReasoning = function(header) {
    const wrapper = header.closest('.reasoning-wrapper');
    const content = wrapper.querySelector('.event-reasoning');
    const icon = header.querySelector('.toggle-icon');
    if (content.classList.contains('collapsed')) {
        content.classList.remove('collapsed');
        icon.textContent = '▼';
    } else {
        content.classList.add('collapsed');
        icon.textContent = '▶';
    }
};

/**
 * 切换搜索卡片折叠
 */
window.toggleSearchCard = function(header) {
    const card = header.closest('.search-progress-card');
    const content = card.querySelector('.search-content');
    const icon = header.querySelector('.toggle-icon');
    if (content.classList.contains('collapsed')) {
        content.classList.remove('collapsed');
        icon.textContent = '▼';
    } else {
        content.classList.add('collapsed');
        icon.textContent = '▶';
    }
};

/**
 * 获取角色图标
 */
function getIcon(role) {
    const icons = {
        'Leader': '👨‍⚖️',
        'Planner': '💡',
        'Auditor': '🔍',
        'Reporter': '📝',
        'devils_advocate': '⚠️',
        'reference_refiner': '📚'
    };
    return icons[role] || '👤';
}

/**
 * 格式化内容（处理Markdown和JSON）
 * @param {string} content - 原始内容
 * @param {string} roleType - 角色类型（可选）
 * @returns {string} - HTML字符串
 */
function formatContent(content, roleType) {
    if (!content) return '';
    
    let text = content.trim();
    let prefix = '';
    let jsonData = null;

    // 寻找 JSON 的起始位置
    let jsonStartIndex = -1;
    
    const searchMarkers = ["重新生成", "搜索完成", "搜索已完成", "系统正在搜索", "SEARCH PROGRESS", "Regenerating", "Search completed", "Search finished", "System searching"];
    let lastMarkerIndex = -1;
    searchMarkers.forEach(marker => {
        const idx = text.lastIndexOf(marker);
        if (idx !== -1 && idx + marker.length > lastMarkerIndex) {
            lastMarkerIndex = idx + marker.length;
        }
    });

    if (lastMarkerIndex !== -1) {
        const afterMarker = text.substring(lastMarkerIndex);
        const match = afterMarker.match(/\{|\[(?!\s*SEARCH)/);
        if (match) {
            jsonStartIndex = lastMarkerIndex + match.index;
        }
    } else {
        const match = text.match(/\{|\[(?!\s*SEARCH)/);
        if (match) {
            jsonStartIndex = match.index;
        }
    }

    // 提取前缀和尝试解析 JSON
    if (jsonStartIndex !== -1) {
        prefix = text.substring(0, jsonStartIndex).trim();
        let potentialJson = text.substring(jsonStartIndex).trim();
        potentialJson = potentialJson.replace(/(\s*```\s*)$/, '');
        
        try {
            jsonData = JSON.parse(potentialJson);
        } catch (e) {
            // JSON 可能不完整
        }
    } else if (text.includes('SEARCH PROGRESS')) {
        prefix = text;
    }

    let html = '';
    if (prefix) {
        let cleanPrefix = prefix.replace(/\[SEARCH:.*?\]/g, '')
                                .replace(/```(json)?\s*$/, '')
                                .trim();
        
        if (cleanPrefix || prefix.includes('SEARCH PROGRESS')) {
            let prefixHtml = marked.parse(cleanPrefix);
            if (prefix.includes('SEARCH PROGRESS')) {
                prefixHtml = prefixHtml.replace(/<h3[^>]*>SEARCH PROGRESS<\/h3>/gi, '');
                
                const hasEndMarker = text.includes('搜索完成') || 
                                   text.includes('搜索已完成') || 
                                   text.includes('重新生成最终方案') ||
                                   text.includes('Search completed') ||
                                   text.includes('Search finished') ||
                                   text.includes('Regenerating final plan');
                
                const collapsedClass = hasEndMarker ? 'collapsed' : '';
                const iconChar = hasEndMarker ? '▶' : '▼';

                html += `
                    <div class="search-progress-card mb-2">
                        <div class="search-header" onclick="window.toggleSearchCard(this)">
                            <h5>
                                <span class="toggle-icon mr-1">${iconChar}</span>
                                <span class="mr-1">🌐</span> ${t('msg_search_progress')}
                            </h5>
                            <span class="text-[10px] text-blue-400 uppercase font-bold tracking-widest">${t('msg_details')}</span>
                        </div>
                        <div class="search-content markdown-body ${collapsedClass}">
                            ${prefixHtml}
                        </div>
                    </div>
                `;
            } else {
                html += `<div class="mb-4 p-3 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-600 italic shadow-sm">${prefixHtml}</div>`;
            }
        }
    }

    if (jsonData) {
        html += renderStructuredData(jsonData);
    } else {
        const remainingText = jsonStartIndex !== -1 ? text.substring(jsonStartIndex) : text;
        
        if (jsonStartIndex !== -1) {
            let rawJson = remainingText.replace(/^```(json)?\s*/, '').replace(/```\s*$/, '');
            html += `<pre class="whitespace-pre-wrap font-mono text-sm bg-slate-50 p-3 rounded-lg border border-slate-200 text-slate-600">${escapeHtml(rawJson)}</pre>`;
        } else if (!text.includes('SEARCH PROGRESS')) {
            html += marked.parse(remainingText);
        }
    }

    return html;
}

/**
 * 渲染结构化数据（JSON）
 * @param {Object} data - JSON数据
 * @returns {string} - HTML字符串
 */
function renderStructuredData(data) {
    // 这里简化处理，实际实现需要根据具体的JSON结构渲染
    // 可以复用index.html中的renderStructuredData逻辑
    return `<pre class="whitespace-pre-wrap font-mono text-sm bg-slate-50 p-3 rounded-lg border border-slate-200 text-slate-600">${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
}

/**
 * 追加日志
 */
function appendLog(logText) {
    const p = document.createElement('p');
    p.className = 'break-all border-b border-slate-800 pb-1 last:border-0';
    if (logText.includes('ERROR')) p.classList.add('text-red-400');
    else if (logText.includes('WARNING')) p.classList.add('text-yellow-400');
    else if (logText.includes('INFO')) p.classList.add('text-blue-300');
    p.textContent = logText;
    logContainer.appendChild(p);
}

// ==================== 报告处理函数 ====================

/**
 * 处理最终报告
 * @param {Object} event - final_report事件对象
 */
export async function handleFinalReport(event) {
    if (!event.report_html) {
        console.error('报告内容为空');
        return;
    }
    
    let html = event.report_html;
    
    // 修复静态资源路径
    const baseUrl = window.location.origin;
    html = html
        .replace(/src=["']\/static\/vendor\/echarts\.min\.js["']/g, `src="${baseUrl}/static/vendor/echarts.min.js"`)
        .replace(/href=["']\/static\//g, `href="${baseUrl}/static/`);
    
    // 注入修订面板
    if (!html.includes('revision-panel')) {
        html = injectRevisionPanel(html);
    }
    
    // 显示报告
    reportIframe.srcdoc = html;
    State.setCachedReportHtml(event.report_html);
    
    // 关闭加载遮罩
    toggleReportLoading(false);
    State.setIsReportingPhase(false);
    
    // 切换到报告模式
    setLayoutMode('report');
    
    // 获取报告版本列表
    fetchReportVersions();
}

/**
 * 注入修订面板到报告HTML
 * @param {string} html - 原始报告HTML
 * @returns {string} - 注入后的HTML
 */
export function injectRevisionPanel(html) {
    if (!html || html.includes('revision-panel')) return html;
    
    const panelHtml = `
        <div id="revision-panel" style="position: fixed; bottom: 20px; right: 20px; background: white; border: 2px solid #3b82f6; border-radius: 12px; padding: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); max-width: 400px; z-index: 9999; font-family: system-ui, -apple-system, sans-serif;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <h3 style="margin: 0; font-size: 16px; font-weight: 600; color: #1f2937;">📝 报告修订</h3>
                <button onclick="document.getElementById('revision-panel').style.display='none'" style="background: none; border: none; font-size: 20px; cursor: pointer; color: #6b7280;">&times;</button>
            </div>
            <textarea id="revision-feedback" placeholder="请描述需要修订的内容..." style="width: 100%; min-height: 80px; padding: 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; resize: vertical; font-family: inherit;"></textarea>
            <button onclick="sendRevisionRequest()" style="margin-top: 12px; width: 100%; padding: 10px; background: #3b82f6; color: white; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 14px; transition: background 0.2s;" onmouseover="this.style.background='#2563eb'" onmouseout="this.style.background='#3b82f6'">
                提交修订请求
            </button>
        </div>
        <script>
            async function sendRevisionRequest() {
                const feedback = document.getElementById('revision-feedback').value.trim();
                if (!feedback) {
                    alert('请输入修订意见');
                    return;
                }
                
                try {
                    const response = await fetch('/api/revise_report', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ feedback })
                    });
                    
                    const data = await response.json();
                    if (data.status === 'success') {
                        alert('修订请求已提交，正在处理...');
                        document.getElementById('revision-feedback').value = '';
                        // 通知父窗口开始轮询
                        window.parent.postMessage({ type: 'start_revision_poll' }, '*');
                    } else {
                        alert('修订请求失败: ' + (data.message || '未知错误'));
                    }
                } catch (error) {
                    alert('网络错误: ' + error.message);
                }
            }
        </script>
    `;
    
    // 在</body>前注入
    return html.replace('</body>', panelHtml + '</body>');
}

// ==================== 工具函数 ====================

/**
 * 切换布局模式
 * @param {'discussion'|'report'} mode - 布局模式
 */
export function setLayoutMode(mode) {
    const discussionCol = document.getElementById('discussion-column');
    const reportCol = document.getElementById('report-column');
    
    if (mode === 'discussion') {
        discussionCol.classList.remove('md:w-1/2');
        discussionCol.classList.add('md:w-full');
        reportCol.classList.add('hidden');
    } else {
        discussionCol.classList.remove('md:w-full');
        discussionCol.classList.add('md:w-1/2');
        reportCol.classList.remove('hidden');
    }
}

/**
 * 切换报告加载遮罩
 * @param {boolean} show - 是否显示
 * @param {string} text - 主文本
 * @param {string} subtext - 副文本
 */
export function toggleReportLoading(show, text = '', subtext = '') {
    const loader = document.getElementById('report-loader');
    const loaderText = document.getElementById('loader-text');
    const loaderSubtext = document.getElementById('loader-subtext');
    const exportBtns = document.querySelectorAll('#export-actions button');
    
    if (show) {
        if (text) loaderText.innerText = text;
        if (subtext) loaderSubtext.innerText = subtext;
        loader.classList.remove('hidden');
        exportBtns.forEach(btn => btn.disabled = true);
    } else {
        loader.classList.add('hidden');
        exportBtns.forEach(btn => btn.disabled = false);
    }
}

/**
 * 获取报告版本列表
 */
async function fetchReportVersions() {
    const sessionId = State.getCurrentSessionId();
    if (!sessionId) return;
    
    try {
        const data = await API.getReportVersions(sessionId);
        const select = document.getElementById('report-version-select');
        if (!select) return;
        
        if (!data.versions || data.versions.length <= 1) {
            select.classList.add('hidden');
            return;
        }
        
        select.innerHTML = '';
        data.versions.forEach((v) => {
            const option = document.createElement('option');
            option.value = v.filename;
            option.textContent = v.label;
            if (v.filename === 'report.html') {
                option.selected = true;
            }
            select.appendChild(option);
        });
        
        select.classList.remove('hidden');
    } catch (error) {
        console.error('获取报告版本失败:', error);
    }
}

// ==================== 导出 ====================
export {
    escapeHtml,
    appendEvent,
    appendLog,
    updateProgress,
    setLayoutMode,
    toggleReportLoading,
    getIcon
};
