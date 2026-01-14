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

import { showAlert, showConfirm } from '../core/utils.js';
import * as API from '../core/api.js';
import * as State from '../core/state.js';

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
    if (State.isRunning) return;
    
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

    try {
        const data = await API.startDiscussion({
            issue,
            backend,
            model,
            reasoning: reasoningEffort ? { effort: reasoningEffort } : undefined,
            rounds,
            planners,
            auditors,
            agent_configs: agentConfigs,
            use_meta_orchestrator: State.isOrchestratorMode
        });
        
        if (data.status === 'ok') {
            console.log('讨论已启动，开始轮询状态更新');
            // 启动轮询以获取实时更新
            startPolling();
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
    if (!State.isRunning) return;
    
    const confirmed = await showConfirm(t('msg_stop_confirm'), t('msg_stop_title'));
    if (!confirmed) return;
    
    try {
        const data = await API.stopDiscussion();
        if (data.status === 'ok') {
            State.setIsRunning(false);
            updateStatusUI({ is_running: false });
            // 停止轮询
            stopPolling();
            console.log('讨论已停止，轮询已终止');
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
    if (State.isRunning) return;
    
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
        const isReporting = State.isReportingPhase || (
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
        if (State.lastEventCount === 0 && flowContainer.innerHTML.trim() === '') {
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
        
        // 讨论结束时停止轮询
        stopPolling();

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
    if (State.isRunning) {
        roundInfo.innerText = `Round ${State.currentRound} / ${maxRounds}`;
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
    
    let targetProgress = State.currentProgress;

    if (event.type === 'system_start') {
        targetProgress = 0;
        State.setCurrentRound(1);
    } else if (event.type === 'round_start') {
        State.setCurrentRound(event.round);
        targetProgress = ((State.currentRound - 1) / maxRounds) * 100;
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

    if (targetProgress > State.currentProgress || event.type === 'system_start') {
        State.setCurrentProgress(targetProgress);
        progressBar.style.width = `${State.currentProgress}%`;
        progressText.innerText = `${Math.round(State.currentProgress)}%`;
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
        console.log('Poll status response:', {
            is_running: data.is_running,
            events_count: data.events?.length,
            logs_count: data.logs?.length,
            has_final_report: !!data.final_report
        });
        
        updateStatusUI(data);
        
        if (data.events) {
            const events = data.events.slice(State.lastEventCount);
            if (events.length > 0) {
                console.log(`Processing ${events.length} new events`);
            }
            events.forEach(event => {
                appendEvent(event);
                updateProgress(event);
                if (event.type === 'final_report' && event.report_html && event.report_html.length > 100) {
                    console.log('[Discussion] Processing final_report event from WebSocket (length:', event.report_html.length, ')');
                    handleFinalReport(event);
                }
            });
            State.setLastEventCount(data.events.length);
        }
        
        if (data.logs) {
            const logs = data.logs.slice(State.lastLogCount);
            if (logs.length > 0) {
                console.log(`Processing ${logs.length} new logs`);
            }
            logs.forEach(log => appendLog(log));
            State.setLastLogCount(data.logs.length);
        }
        
        // 处理最终报告（后端直接返回的final_report字段）
        if (data.final_report && data.final_report.length > 100) {
            const reportIframe = document.getElementById('report-iframe');
            // 只有当iframe为空或显示占位符时才加载报告
            if (reportIframe && (!reportIframe.srcdoc || reportIframe.srcdoc.length < 200 || reportIframe.srcdoc.includes('italic'))) {
                console.log('[Discussion] Loading final report from status API (length:', data.final_report.length, ')');
                handleFinalReport({ report_html: data.final_report });
            }
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
        console.log('Starting polling (interval: 1000ms)');
        pollTimer = setInterval(pollStatus, POLL_INTERVAL);
        // 立即执行一次
        pollStatus();
    } else {
        console.log('Polling already active');
    }
}

/**
 * 停止轮询
 */
export function stopPolling() {
    if (pollTimer) {
        console.log('Stopping polling');
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
    if (State.lastEventCount === 0 && flowContainer.querySelector('.animate-pulse')) {
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
export function formatContent(content, roleType) {
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
            // 使用marked解析Markdown，如果marked未定义则降级为纯文本
            if (typeof marked !== 'undefined' && marked.parse) {
                html += marked.parse(remainingText);
            } else {
                // 降级：简单的文本处理（换行转<br>）
                html += `<div class="whitespace-pre-wrap">${escapeHtml(remainingText)}</div>`;
            }
        }
    }

    return html;
}

/**
 * 渲染结构化数据（JSON）
 * @param {Object} data - JSON数据
 * @returns {string} - HTML字符串
 */
export function renderStructuredData(data) {
    // 使用智能渲染
    try {
        return renderGenericJsonTree(data);
    } catch (e) {
        // 降级到简单渲染
        return `<pre class="whitespace-pre-wrap font-mono text-sm bg-slate-50 p-3 rounded-lg border border-slate-200 text-slate-600">${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
    }
}

// ==================== 智能数据渲染工具 ====================

// 智能高亮关键字映射
const SMART_HIGHLIGHT_KEYWORDS = {
    error: ['issues', 'problems', 'errors', 'error', 'bugs', 'failures', 'failed', 'critical', 'warnings', 'risks', 'concerns', 'weaknesses', 'limitations', 'gaps', 'missing', '问题', '错误', '风险', '缺陷', '不足', '隐患', '漏洞', '质疑', '挑战'],
    success: ['suggestions', 'recommendations', 'solutions', 'improvements', 'advantages', 'benefits', 'strengths', 'success', 'achieved', '建议', '优势', '方案', '改进', '解决', '优点', '成功', '选择', '推荐'],
    rating: ['rating', 'score', 'level', 'grade', 'priority', 'status', 'evaluation', 'assessment', '评分', '等级', '评级', '优先级', '状态', '类型', 'type']
};

// 评级值到Badge颜色映射
const SMART_BADGE_COLORS = {
    '优秀': 'green', '良好': 'blue', '合格': 'blue', '一般': 'yellow', '较差': 'red', '不合格': 'red', '不可行': 'red', '需重构': 'yellow',
    '高': 'red', '中': 'yellow', '低': 'green',
    '紧急': 'red', '重要': 'yellow', '普通': 'blue',
    '成功': 'green', '失败': 'red', '进行中': 'blue', '待处理': 'yellow',
    '决策类': 'purple', '分析类': 'blue', '创意类': 'green', '规划类': 'yellow',
    'excellent': 'green', 'good': 'blue', 'pass': 'blue', 'fair': 'yellow', 'poor': 'red', 'fail': 'red', 'infeasible': 'red',
    'high': 'red', 'medium': 'yellow', 'low': 'green',
    'critical': 'red', 'important': 'yellow', 'normal': 'blue',
    'success': 'green', 'failed': 'red', 'pending': 'yellow', 'in_progress': 'blue',
    'decision': 'purple', 'analysis': 'blue', 'creative': 'green', 'planning': 'yellow'
};

// 字段名称美化映射
const FIELD_DISPLAY_NAMES = {
    'analysis': '📊 需求分析', 'role_planning': '👥 角色规划', 'framework_selection': '🏗️ 框架选择',
    'execution_config': '⚙️ 执行配置', 'summary': '📋 规划摘要',
    'problem_type': '问题类型', 'core_requirement': '核心需求', 'complexity': '复杂度',
    'key_points': '关键要点', 'constraints': '约束条件',
    'recommended_roles': '推荐角色', 'custom_roles_needed': '需要自定义角色',
    'custom_role_descriptions': '自定义角色描述',
    'selected_framework': '选定框架', 'framework_reason': '选择原因', 'stage_customization': '阶段定制',
    'total_rounds': '总轮数', 'agents_per_role': '每角色Agent数',
    'key_decisions': '关键决策', 'expected_outcomes': '预期成果', 'risk_factors': '风险因素',
    'name': '名称', 'description': '描述', 'type': '类型', 'source': '来源',
    'stages': '阶段', 'roles': '角色', 'rounds': '轮数',
    'core_idea': '核心思路', 'steps': '执行步骤', 'feasibility': '可行性分析',
    'advantages': '优势', 'requirements': '资源需求',
    'reviews': '审查意见', 'issues': '发现问题', 'suggestions': '改进建议',
    'rating': '评级', 'plan_id': '方案ID',
    'decomposition': '问题拆解', 'core_goal': '核心目标', 'key_questions': '关键问题',
    'boundaries': '边界条件', 'report_design': '报告设计', 'instructions': '执行指令'
};

function getSmartHighlightType(key) {
    if (!key) return null;
    const lowerKey = key.toLowerCase();
    for (const [type, keywords] of Object.entries(SMART_HIGHLIGHT_KEYWORDS)) {
        if (keywords.some(kw => lowerKey.includes(kw))) {
            return type;
        }
    }
    return null;
}

function getSmartBadgeColor(value) {
    if (typeof value !== 'string') return null;
    const lowerValue = value.toLowerCase();
    for (const [val, color] of Object.entries(SMART_BADGE_COLORS)) {
        if (lowerValue === val.toLowerCase() || lowerValue.includes(val.toLowerCase())) {
            return color;
        }
    }
    return 'gray';
}

function getFieldDisplayName(key) {
    return FIELD_DISPLAY_NAMES[key] || key;
}

function getFieldIcon(key) {
    const icons = {
        'analysis': '📊', 'role_planning': '👥', 'framework_selection': '🏗️',
        'execution_config': '⚙️', 'summary': '📋', 'stages': '📑', 'roles': '👤',
        'key_points': '🎯', 'constraints': '🔒', 'risk_factors': '⚠️',
        'advantages': '✅', 'issues': '❌', 'suggestions': '💡',
        'steps': '📝', 'core_idea': '💡', 'decomposition': '🔍'
    };
    return icons[key] || '📄';
}

function isHomogeneousObjectArray(arr) {
    if (!Array.isArray(arr) || arr.length === 0) return false;
    if (arr.length === 1) return typeof arr[0] === 'object' && arr[0] !== null && !Array.isArray(arr[0]);
    
    const firstKeys = typeof arr[0] === 'object' && arr[0] !== null ? Object.keys(arr[0]).sort().join(',') : null;
    if (!firstKeys) return false;
    
    return arr.every(item => {
        if (typeof item !== 'object' || item === null || Array.isArray(item)) return false;
        return Object.keys(item).sort().join(',') === firstKeys;
    });
}

function isSimpleArray(arr) {
    if (!Array.isArray(arr)) return false;
    return arr.every(item => typeof item !== 'object' || item === null);
}

function isFlatObject(obj) {
    if (typeof obj !== 'object' || obj === null || Array.isArray(obj)) return false;
    return Object.values(obj).every(v => typeof v !== 'object' || v === null);
}

function renderGenericJsonTree(data, title = null) {
    return `
        <div class="smart-render-container">
            ${title ? `
                <div class="smart-render-header">
                    <span class="smart-render-header-icon">📋</span>
                    <span class="smart-render-header-title">${escapeHtml(title)}</span>
                </div>
            ` : ''}
            ${renderSmartValue(data, null, 0)}
        </div>
    `;
}

function renderSmartValue(data, key, depth) {
    if (data === null || data === undefined) {
        return `<span class="text-slate-400 italic">${data === null ? '空' : '未定义'}</span>`;
    }
    
    if (typeof data !== 'object') {
        return renderPrimitiveValue(data, key);
    }
    
    if (Array.isArray(data)) {
        if (data.length === 0) {
            return `<span class="text-slate-400 italic">（空列表）</span>`;
        }
        
        if (isHomogeneousObjectArray(data)) {
            return renderTable(data);
        }
        
        if (isSimpleArray(data)) {
            return renderSimpleList(data, key);
        }
        
        return renderComplexArray(data, key, depth);
    }
    
    const keys = Object.keys(data);
    if (keys.length === 0) {
        return `<span class="text-slate-400 italic">（空对象）</span>`;
    }
    
    if (depth === 0) {
        return renderTopLevelObject(data);
    }
    
    if (isFlatObject(data)) {
        return renderKeyValueGrid(data);
    }
    
    return renderNestedObject(data, key, depth);
}

function renderPrimitiveValue(value, key) {
    if (typeof value === 'string') {
        const badgeColor = key && getSmartHighlightType(key) === 'rating' ? getSmartBadgeColor(value) : null;
        if (badgeColor) {
            return `<span class="smart-badge smart-badge-${badgeColor}">${escapeHtml(value)}</span>`;
        }
        
        if (value.length > 80) {
            return `<div class="smart-kv-value-long">${escapeHtml(value)}</div>`;
        }
        
        return `<span class="text-slate-700">${escapeHtml(value)}</span>`;
    }
    
    if (typeof value === 'number') {
        return `<span class="text-blue-600 font-medium">${value}</span>`;
    }
    
    if (typeof value === 'boolean') {
        return value 
            ? `<span class="smart-badge smart-badge-green">是</span>`
            : `<span class="smart-badge smart-badge-gray">否</span>`;
    }
    
    return `<span class="text-slate-500">${String(value)}</span>`;
}

function renderTable(arr) {
    if (arr.length === 0) return '';
    
    const headers = Object.keys(arr[0]);
    
    return `
        <table class="smart-table">
            <thead>
                <tr>
                    ${headers.map(h => `<th>${escapeHtml(getFieldDisplayName(h))}</th>`).join('')}
                </tr>
            </thead>
            <tbody>
                ${arr.map(row => `
                    <tr>
                        ${headers.map(h => `<td>${renderPrimitiveValue(row[h], h)}</td>`).join('')}
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

function renderSimpleList(arr, key) {
    const useNumbers = key && (key.includes('step') || key.includes('point') || key.includes('question') || 
                              key.includes('步骤') || key.includes('要点') || key.includes('问题'));
    
    return `
        <ul class="smart-list">
            ${arr.map((item, i) => `
                <li class="smart-list-item">
                    ${useNumbers 
                        ? `<span class="smart-list-number">${i + 1}</span>`
                        : `<span class="smart-list-bullet"></span>`
                    }
                    <span>${renderPrimitiveValue(item, null)}</span>
                </li>
            `).join('')}
        </ul>
    `;
}

function renderComplexArray(arr, key, depth) {
    return arr.map((item, i) => {
        const nodeId = `arr-${Math.random().toString(36).substr(2, 9)}`;
        const itemTitle = item.name || item.title || item.id || `项目 ${i + 1}`;
        
        return `
            <div class="smart-card">
                <div class="smart-card-header" onclick="window.toggleSmartCard('${nodeId}')">
                    <span class="smart-card-title">
                        <span class="smart-card-title-icon">📌</span>
                        ${escapeHtml(String(itemTitle))}
                    </span>
                    <span class="smart-card-toggle" id="${nodeId}-icon">▼</span>
                </div>
                <div class="smart-card-content" id="${nodeId}">
                    ${renderSmartValue(item, null, depth + 1)}
                </div>
            </div>
        `;
    }).join('');
}

function renderKeyValueGrid(obj) {
    const entries = Object.entries(obj);
    
    return `
        <div class="smart-kv-grid">
            ${entries.map(([k, v]) => `
                <span class="smart-kv-key">${escapeHtml(getFieldDisplayName(k))}</span>
                <span class="smart-kv-value">${renderPrimitiveValue(v, k)}</span>
            `).join('')}
        </div>
    `;
}

function renderTopLevelObject(obj) {
    const entries = Object.entries(obj);
    const simpleFields = {};
    const complexFields = [];
    
    entries.forEach(([k, v]) => {
        if (typeof v !== 'object' || v === null) {
            simpleFields[k] = v;
        } else {
            complexFields.push([k, v]);
        }
    });
    
    let html = '';
    
    if (Object.keys(simpleFields).length > 0) {
        html += `
            <div class="smart-card">
                <div class="smart-card-header" onclick="window.toggleSmartCard('overview-card')">
                    <span class="smart-card-title">
                        <span class="smart-card-title-icon">📋</span>
                        概览
                    </span>
                    <span class="smart-card-toggle" id="overview-card-icon">▼</span>
                </div>
                <div class="smart-card-content" id="overview-card">
                    ${renderKeyValueGrid(simpleFields)}
                </div>
            </div>
        `;
    }
    
    complexFields.forEach(([k, v]) => {
        const nodeId = `card-${Math.random().toString(36).substr(2, 9)}`;
        const highlightType = getSmartHighlightType(k);
        const highlightClass = highlightType ? `smart-highlight-${highlightType}` : '';
        const displayName = getFieldDisplayName(k);
        const icon = getFieldIcon(k);
        const isArray = Array.isArray(v);
        const badge = isArray ? `${v.length} 项` : `${Object.keys(v).length} 字段`;
        
        html += `
            <div class="smart-card ${highlightClass}">
                <div class="smart-card-header" onclick="window.toggleSmartCard('${nodeId}')">
                    <span class="smart-card-title">
                        <span class="smart-card-title-icon">${icon}</span>
                        ${escapeHtml(displayName)}
                        <span class="smart-card-badge">${badge}</span>
                    </span>
                    <span class="smart-card-toggle" id="${nodeId}-icon">▼</span>
                </div>
                <div class="smart-card-content" id="${nodeId}">
                    ${renderSmartValue(v, k, 1)}
                </div>
            </div>
        `;
    });
    
    return html;
}

function renderNestedObject(obj, key, depth) {
    if (isFlatObject(obj)) {
        return renderKeyValueGrid(obj);
    }
    
    const entries = Object.entries(obj);
    let html = '<div class="space-y-2">';
    
    entries.forEach(([k, v]) => {
        const displayName = getFieldDisplayName(k);
        
        if (typeof v !== 'object' || v === null) {
            html += `
                <div class="flex items-start gap-2">
                    <span class="smart-kv-key min-w-[100px]">${escapeHtml(displayName)}</span>
                    <span class="smart-kv-value">${renderPrimitiveValue(v, k)}</span>
                </div>
            `;
        } else {
            const nodeId = `nested-${Math.random().toString(36).substr(2, 9)}`;
            const collapsed = depth >= 2 ? 'collapsed' : '';
            const icon = collapsed ? '▶' : '▼';
            
            html += `
                <div class="border-l-2 border-slate-200 pl-3 mt-2">
                    <div class="flex items-center gap-2 cursor-pointer text-slate-600 hover:text-slate-800 mb-1" onclick="window.toggleSmartCard('${nodeId}')">
                        <span class="text-xs" id="${nodeId}-icon">${icon}</span>
                        <span class="font-medium text-sm">${escapeHtml(displayName)}</span>
                    </div>
                    <div class="${collapsed}" id="${nodeId}">
                        ${renderSmartValue(v, k, depth + 1)}
                    </div>
                </div>
            `;
        }
    });
    
    html += '</div>';
    return html;
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
    console.log('[Discussion] handleFinalReport called, report_html length:', event?.report_html?.length);
    
    // 移除校验：由 pollStatus 在调用前确保数据有效性
    // 此处直接处理可避免延迟加载时丢失配置
    
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
    const reportSection = document.getElementById('report-section');
    const discussionSection = document.getElementById('discussion-section');
    
    if (!reportSection) {
        console.warn('report-section element not found');
        return;
    }
    
    if (mode === 'discussion') {
        // 讨论模式：隐藏报告区，讨论区扩展为100%
        reportSection.classList.add('hidden');
        reportSection.classList.remove('lg:hidden');
        if (discussionSection) {
            discussionSection.classList.remove('lg:w-1/2');
            discussionSection.classList.add('lg:w-full');
        }
    } else {
        // 报告模式：显示报告区，恢复两栏布局
        reportSection.classList.remove('hidden', 'lg:hidden');
        if (discussionSection) {
            discussionSection.classList.remove('lg:w-full');
            discussionSection.classList.add('lg:w-1/2');
        }
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
    const sessionId = State.currentSessionId;
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

// ==================== UI Toggle Functions ====================

// 用于跟踪修订面板状态
let panelCollapsed = true;

/**
 * 切换修订面板显示/隐藏
 */
export function toggleRevisionPanel() {
    const content = document.getElementById('revision-content');
    const toggle = document.getElementById('revision-toggle');
    
    if (panelCollapsed) {
        content.style.display = 'block';
        toggle.innerHTML = '✕ 关闭';
        panelCollapsed = false;
    } else {
        content.style.display = 'none';
        toggle.innerHTML = '💬 修订反馈';
        panelCollapsed = true;
    }
}

/**
 * 提交修订反馈
 */
export async function submitRevisionFeedback() {
    const feedback = document.getElementById('revision-feedback')?.value.trim();
    if (!feedback) {
        showAlert('请输入修改要求', '提示');
        return;
    }
    
    const statusDiv = document.getElementById('revision-status');
    const statusText = document.getElementById('revision-status-text');
    const resultDiv = document.getElementById('revision-result');
    const submitBtn = document.getElementById('btn-submit-revision');
    
    // 显示加载状态
    if (statusDiv) statusDiv.style.display = 'block';
    if (statusText) statusText.innerHTML = '⏳ 报告审核官正在处理您的修订要求...';
    if (resultDiv) resultDiv.style.display = 'none';
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '⏳ 处理中...';
    }
    
    try {
        // 获取workspace ID
        const workspaceId = State.sessionId || '';
        
        // 获取当前报告HTML
        const reportIframe = document.getElementById('report-iframe');
        let reportContent = '';
        if (reportIframe && reportIframe.contentDocument) {
            reportContent = reportIframe.contentDocument.documentElement.outerHTML;
        }
        
        const response = await API.reviseReport(workspaceId, feedback, reportContent);
        
        if (response.status === 'success') {
            // 显示修订结果
            if (statusDiv) statusDiv.style.display = 'none';
            if (resultDiv) {
                resultDiv.style.display = 'block';
                
                let changesHtml = `<h4 style="margin:0 0 10px 0;color:#667eea;">✅ 修订完成（版本 ${response.version}）</h4>`;
                changesHtml += `<p style="margin:0 0 10px 0;"><strong>概要：</strong>${response.revision_summary}</p>`;
                
                if (response.changes_made && response.changes_made.length > 0) {
                    changesHtml += '<p style="margin:0 0 5px 0;"><strong>修改内容：</strong></p><ul style="margin:0;padding-left:20px;">';
                    response.changes_made.forEach(c => {
                        changesHtml += `<li>${c}</li>`;
                    });
                    changesHtml += '</ul>';
                }
                
                if (response.warnings && response.warnings.length > 0) {
                    changesHtml += '<p style="margin:10px 0 5px 0;color:#f59e0b;"><strong>⚠️ 注意：</strong></p><ul style="margin:0;padding-left:20px;color:#f59e0b;">';
                    response.warnings.forEach(w => {
                        changesHtml += `<li>${w}</li>`;
                    });
                    changesHtml += '</ul>';
                }
                
                changesHtml += '<p style="margin:15px 0 0 0;"><button onclick="window.applyRevision()" style="background:#667eea;color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;">🔄 应用修订</button></p>';
                
                resultDiv.innerHTML = changesHtml;
                
                // 保存修订后的HTML
                window._revisedHtml = response.revised_html;
            }
            
        } else {
            if (statusText) statusText.innerHTML = `❌ 修订失败：${response.message || '未知错误'}`;
        }
        
    } catch (error) {
        if (statusText) statusText.innerHTML = `❌ 请求失败：${error.message}`;
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '📤 提交修订';
        }
    }
}

/**
 * 应用修订后的报告
 */
export function applyRevision() {
    if (window._revisedHtml) {
        const reportIframe = document.getElementById('report-iframe');
        if (reportIframe) {
            reportIframe.srcdoc = window._revisedHtml;
        }
        showAlert('报告已更新', '成功');
    }
}

/**
 * 确认满意当前报告
 */
export function confirmSatisfied() {
    showConfirm('确认对当前报告满意？', '确认', () => {
        const panel = document.getElementById('revision-panel');
        if (panel) panel.style.display = 'none';
    });
}

/**
 * 最大化/还原功能
 */
export function toggleMaximize(sectionId) {
    const section = document.getElementById(sectionId);
    if (!section) return;
    
    const btn = section.querySelector('button[onclick^="toggleMaximize"]');
    const icon = document.getElementById(sectionId === 'discussion-section' ? 'discussion-maximize-icon' : 'report-maximize-icon');
    const isMaximized = section.classList.toggle('maximized');
    
    if (isMaximized) {
        // 切换为还原图标
        if (icon) icon.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 14h6v6M20 10h-6V4M3 21l7-7M21 3l-7 7"></path>';
        if (btn) {
            btn.setAttribute('data-i18n-title', 'btn_restore');
            btn.title = '还原';
        }
        document.body.style.overflow = 'hidden';
    } else {
        // 切换为最大化图标
        if (icon) icon.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"></path>';
        if (btn) {
            btn.setAttribute('data-i18n-title', 'btn_maximize');
            btn.title = '最大化';
        }
        document.body.style.overflow = '';
    }
}

/**
 * 切换智能卡片显示/隐藏
 */
export function toggleSmartCard(nodeId) {
    const card = document.querySelector(`[data-node-id="${nodeId}"]`);
    if (!card) return;
    
    const content = card.querySelector('.smart-card-content');
    const icon = card.querySelector('.toggle-icon');
    if (!content || !icon) return;
    
    if (content.classList.contains('collapsed')) {
        content.classList.remove('collapsed');
        icon.textContent = '▼';
    } else {
        content.classList.add('collapsed');
        icon.textContent = '▶';
    }
}

/**
 * 切换推理内容显示/隐藏
 */
export function toggleReasoning(header) {
    const wrapper = header.closest('.reasoning-wrapper');
    const content = wrapper?.querySelector('.event-reasoning');
    const icon = header.querySelector('.toggle-icon');
    if (!content || !icon) return;
    
    if (content.classList.contains('collapsed')) {
        content.classList.remove('collapsed');
        icon.textContent = '▼';
    } else {
        content.classList.add('collapsed');
        icon.textContent = '▶';
    }
}

/**
 * 切换搜索卡片显示/隐藏
 */
export function toggleSearchCard(header) {
    const card = header.closest('.search-progress-card');
    const content = card?.querySelector('.search-content');
    const icon = header.querySelector('.toggle-icon');
    if (!content || !icon) return;
    
    if (content.classList.contains('collapsed')) {
        content.classList.remove('collapsed');
        icon.textContent = '▼';
    } else {
        content.classList.add('collapsed');
        icon.textContent = '▶';
    }
}

/**
 * 切换讨论阶段显示/隐藏
 */
export function toggleStage(stageId) {
    const stage = document.getElementById(stageId);
    if (!stage) return;
    const content = stage.querySelector(`#${stageId}-content`);
    const icon = document.getElementById(`${stageId}-icon`);
    if (!content || !icon) return;
    if (content.classList.contains('hidden')) {
        content.classList.remove('hidden');
        icon.style.transform = 'rotate(0deg)';
    } else {
        content.classList.add('hidden');
        icon.style.transform = 'rotate(-90deg)';
    }
}
