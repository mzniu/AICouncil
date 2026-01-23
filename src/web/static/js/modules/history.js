/**
 * @fileoverview 历史记录管理模块
 * @module modules/history
 * @description 负责历史工作区的加载、查看、删除等操作
 */

import { showAlert, showConfirm, formatDate } from '../core/utils.js';
import { getWorkspaces, deleteWorkspace as apiDeleteWorkspace, loadWorkspace as apiLoadWorkspace } from '../core/api.js';
import * as State from '../core/state.js';
import { pollStatus } from './discussion.js';

// 动态获取全局t()函数
const t = (key) => (window.t && typeof window.t === 'function') ? window.t(key) : key;

// 历史记录分页状态
let currentPage = 1;
let currentStatus = ''; // '', 'running', 'completed', 'failed'
const perPage = 20;

/**
 * 切换历史记录模态框的显示/隐藏状态
 * @async
 * @returns {Promise<void>}
 */
export async function toggleHistoryModal() {
    const modal = document.getElementById('history-modal');
    const list = document.getElementById('history-list');
    
    if (!modal || !list) {
        console.error('History modal elements not found');
        return;
    }
    
    if (modal.classList.contains('hidden')) {
        modal.classList.remove('hidden');
        // 重置分页
        currentPage = 1;
        currentStatus = '';
        await loadHistoryPage();
    } else {
        modal.classList.add('hidden');
    }
}

/**
 * 加载历史记录页面
 * @async
 * @returns {Promise<void>}
 */
async function loadHistoryPage() {
    const list = document.getElementById('history-list');
    list.innerHTML = `<div class="text-center py-8 text-slate-400 italic">${t('history_loading')}</div>`;
    
    try {
        const options = { page: currentPage, per_page: perPage };
        if (currentStatus) options.status = currentStatus;
        
        const data = await getWorkspaces(options);
        
        if (data.status === 'success' && data.workspaces && data.workspaces.length > 0) {
            renderHistoryList(data.workspaces, data.pagination);
        } else {
            list.innerHTML = `<div class="text-center py-8 text-slate-400 italic">${t('msg_history_empty')}</div>`;
        }
    } catch (error) {
        list.innerHTML = `<div class="text-center py-8 text-red-400 italic">加载失败: ${error.message}</div>`;
    }
}

/**
 * 渲染历史记录列表HTML
 * @param {Array<Object>} workspaces - 工作区数组
 * @param {Object} pagination - 分页信息
 * @returns {void}
 */
export function renderHistoryList(workspaces, pagination) {
    const list = document.getElementById('history-list');
    list.innerHTML = '';
    
    // 添加筛选器和分页控件容器
    const controls = document.createElement('div');
    controls.className = 'mb-4 flex items-center justify-between pb-3 border-b border-slate-200';
    controls.innerHTML = `
        <div class="flex items-center space-x-2">
            <label class="text-sm font-medium text-slate-600">状态筛选：</label>
            <select id="status-filter" class="px-3 py-1.5 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="">全部</option>
                <option value="running">运行中</option>
                <option value="completed">已完成</option>
                <option value="failed">失败</option>
            </select>
        </div>
        <div class="text-sm text-slate-500">
            共 <span class="font-bold text-slate-700">${pagination ? pagination.total : workspaces.length}</span> 条记录
        </div>
    `;
    list.appendChild(controls);
    
    // 设置当前筛选状态
    const statusFilter = document.getElementById('status-filter');
    statusFilter.value = currentStatus;
    statusFilter.onchange = async (e) => {
        currentStatus = e.target.value;
        currentPage = 1; // 重置页码
        await loadHistoryPage();
    };
    
    // 渲染工作区列表
    const wsContainer = document.createElement('div');
    wsContainer.className = 'space-y-2 mb-4';
    
    workspaces.forEach(ws => {
        const item = document.createElement('div');
        item.className = 'p-4 border border-slate-100 rounded-xl hover:bg-indigo-50 hover:border-indigo-200 cursor-pointer transition group';
        item.onclick = () => loadWorkspace(ws.id);
        
        // 状态徽章颜色
        const statusColors = {
            'running': 'bg-blue-100 text-blue-700',
            'completed': 'bg-green-100 text-green-700',
            'failed': 'bg-red-100 text-red-700'
        };
        const statusColor = statusColors[ws.status] || 'bg-gray-100 text-gray-700';
        
        // 后端图标
        const backendIcons = {
            'deepseek': '🧠',
            'openai': '🤖',
            'openrouter': '🔀',
            'aliyun': '☁️',
            'ollama': '🦙'
        };
        const backendIcon = backendIcons[ws.backend] || '⚙️';
        
        item.innerHTML = `
            <div class="flex justify-between items-start">
                <div class="flex-1">
                    <div class="flex items-center space-x-2 mb-1">
                        <h4 class="font-bold text-slate-800 group-hover:text-indigo-700">${ws.issue || t('msg_untitled_issue')}</h4>
                        <span class="text-xs px-2 py-0.5 rounded-full ${statusColor} font-medium">${ws.status || 'unknown'}</span>
                    </div>
                    <div class="flex items-center space-x-3 text-xs text-slate-500 mt-1">
                        <span>📅 ${ws.created_at || ws.timestamp || 'N/A'}</span>
                        <span>${backendIcon} ${ws.backend || 'unknown'}</span>
                        <span>🤖 ${ws.model || 'N/A'}</span>
                        ${ws.report_version ? `<span>📝 v${ws.report_version}</span>` : ''}
                    </div>
                    <p class="text-xs text-slate-400 mt-1">ID: ${ws.id}</p>
                </div>
                <div class="flex flex-col items-end space-y-2">
                    <button onclick="deleteWorkspace(event, '${ws.id}')" 
                            class="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition opacity-0 group-hover:opacity-100"
                            title="${t('btn_delete_record')}">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                        </svg>
                    </button>
                </div>
            </div>
        `;
        wsContainer.appendChild(item);
    });
    list.appendChild(wsContainer);
    
    // 渲染分页控件
    if (pagination && pagination.total > perPage) {
        const paginationEl = document.createElement('div');
        paginationEl.className = 'flex items-center justify-between pt-3 border-t border-slate-200';
        
        const prevDisabled = currentPage <= 1;
        const nextDisabled = currentPage >= pagination.pages;
        
        paginationEl.innerHTML = `
            <button id="prev-page" 
                    class="px-4 py-2 text-sm font-medium rounded-lg transition ${
                        prevDisabled 
                        ? 'bg-slate-100 text-slate-400 cursor-not-allowed' 
                        : 'bg-blue-600 text-white hover:bg-blue-700'
                    }"
                    ${prevDisabled ? 'disabled' : ''}>
                ← 上一页
            </button>
            <div class="text-sm text-slate-600">
                第 <span class="font-bold">${currentPage}</span> / <span class="font-bold">${pagination.pages}</span> 页
            </div>
            <button id="next-page" 
                    class="px-4 py-2 text-sm font-medium rounded-lg transition ${
                        nextDisabled 
                        ? 'bg-slate-100 text-slate-400 cursor-not-allowed' 
                        : 'bg-blue-600 text-white hover:bg-blue-700'
                    }"
                    ${nextDisabled ? 'disabled' : ''}>
                下一页 →
            </button>
        `;
        list.appendChild(paginationEl);
        
        // 绑定分页按钮事件
        if (!prevDisabled) {
            document.getElementById('prev-page').onclick = async () => {
                currentPage--;
                await loadHistoryPage();
            };
        }
        if (!nextDisabled) {
            document.getElementById('next-page').onclick = async () => {
                currentPage++;
                await loadHistoryPage();
            };
        }
    }
}

/**
 * 加载历史工作区
 * @async
 * @param {string} sessionId - 工作区会话ID
 * @returns {Promise<void>}
 */
export async function loadWorkspace(sessionId) {
    console.log('[History] loadWorkspace called with sessionId:', sessionId);
    const confirmed = await showConfirm(t('msg_confirm_load'), t('title_confirm_load'));
    console.log('[History] User confirmed load:', confirmed);
    if (!confirmed) return;
    
    try {
        const data = await apiLoadWorkspace(sessionId);
        console.log('[History] Load workspace response:', data);
        
        if (data.status === 'success') {
            // 设置当前会话ID（重要：用于重新生成报告等操作）
            State.setCurrentSessionId(sessionId);
            console.log('[History] Session ID set:', sessionId);
            
            // 重置UI
            document.getElementById('discussion-flow').innerHTML = '';
            
            // 清空并隐藏报告
            const reportIframe = document.getElementById('report-iframe');
            reportIframe.srcdoc = "<div style='color:#94a3b8; font-style:italic; text-align:center; margin-top:100px; font-family:sans-serif;'></div>";
            
            // 重置进度条
            State.setCurrentProgress(0);
            State.setIsReportingPhase(false);
            document.getElementById('progress-bar').style.width = '0%';
            document.getElementById('progress-percentage').innerText = '0%';
            
            // 更新输入框
            document.getElementById('issue-input').value = data.issue || '';
            if (data.rounds) {
                document.getElementById('rounds-input').value = data.rounds;
            }
            
            // 关闭模态框
            toggleHistoryModal();
            
            // 提示成功
            showAlert(t('msg_load_success'), t('title_success'));
            
            // 重置计数器以强制全量拉取
            State.setLastEventCount(0);
            State.setLastLogCount(0);
            
            console.log('[History] Triggering pollStatus to load historical events...');
            // 触发一次轮询以拉取所有历史事件
            pollStatus();
            
            // 显示报告版本信息（如果有）
            if (data.report_version) {
                // 动态导入discussion模块以避免循环依赖
                import('./discussion.js').then(Discussion => {
                    Discussion.updateReportVersionDisplay(data.report_version, data.updated_at || data.created_at);
                });
            }
        } else {
            console.error('[History] Load failed:', data.message);
            showAlert(t('msg_load_failed') + ': ' + (data.message || 'unknown'), t('title_error'), 'error');
        }
    } catch (error) {
        console.error('[History] Load error:', error);
        
        // 特殊处理403权限错误
        if (error.status === 403 || (error.message && error.message.includes('[403]'))) {
            showAlert(
                '🔒 您没有权限访问此会话\\n\\n可能原因：\\n• 此会话属于其他用户\\n• 您的账户权限不足\\n\\n请联系会话所有者或管理员获取访问权限。',
                '⛔ 访问被拒绝',
                'error'
            );
        } else if (error.status === 404 || (error.message && error.message.includes('[404]'))) {
            showAlert(
                '📂 找不到此会话\\n\\n可能原因：\\n• 会话已被删除\\n• 会话ID不正确\\n\\n请刷新列表后重试。',
                '🔍 会话不存在',
                'error'
            );
        } else {
            showAlert(t('msg_load_failed') + ': ' + error.message, t('title_error'), 'error');
        }
    }
}

/**
 * 删除历史记录
 * @async
 * @param {Event} event - 点击事件对象
 * @param {string} sessionId - 工作区会话ID
 * @returns {Promise<void>}
 */
export async function deleteHistory(event, sessionId) {
    console.log('[History] deleteHistory called with:', { event, sessionId });
    event.stopPropagation(); // 阻止触发 loadWorkspace
    
    const confirmed = await showConfirm(t('msg_confirm_delete'), t('title_confirm_delete'));
    console.log('[History] User confirmed:', confirmed);
    if (!confirmed) return;
    
    try {
        const data = await apiDeleteWorkspace(sessionId);
        
        if (data.status === 'success') {
            // 重新加载历史列表
            const modal = document.getElementById('history-modal');
            modal.classList.add('hidden'); // 先关闭
            await toggleHistoryModal(); // 再打开以触发刷新
            showAlert(t('msg_delete_success'), t('title_success'));
        } else {
            showAlert(t('msg_delete_failed') + ': ' + (data.message || 'unknown'), t('title_error'), 'error');
        }
    } catch (error) {
        showAlert(t('msg_delete_failed') + ': ' + error.message, t('title_error'), 'error');
    }
}

/**
 * 查看历史详情（预留函数）
 * @param {string} workspaceId - 工作区ID
 * @returns {void}
 */
export function viewHistoryDetails(workspaceId) {
    // TODO: 实现历史详情查看功能
    console.log('View history details:', workspaceId);
}

// 导出所有函数作为命名空间
export default {
    toggleHistoryModal,
    renderHistoryList,
    loadWorkspace,
    deleteHistory,
    viewHistoryDetails
};
