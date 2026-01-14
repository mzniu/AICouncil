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
        list.innerHTML = `<div class="text-center py-8 text-slate-400 italic">${t('history_loading')}</div>`;
        
        try {
            const data = await getWorkspaces();
            
            if (data.status === 'success' && data.workspaces.length > 0) {
                renderHistoryList(data.workspaces);
            } else {
                list.innerHTML = `<div class="text-center py-8 text-slate-400 italic">${t('msg_history_empty')}</div>`;
            }
        } catch (error) {
            list.innerHTML = `<div class="text-center py-8 text-red-400 italic">加载失败: ${error.message}</div>`;
        }
    } else {
        modal.classList.add('hidden');
    }
}

/**
 * 渲染历史记录列表HTML
 * @param {Array<Object>} workspaces - 工作区数组
 * @param {string} workspaces[].id - 工作区ID
 * @param {string} workspaces[].issue - 议题标题
 * @param {string} workspaces[].timestamp - 时间戳
 * @returns {void}
 */
export function renderHistoryList(workspaces) {
    const list = document.getElementById('history-list');
    list.innerHTML = '';
    
    workspaces.forEach(ws => {
        const item = document.createElement('div');
        item.className = 'p-4 border border-slate-100 rounded-xl hover:bg-indigo-50 hover:border-indigo-200 cursor-pointer transition group';
        item.onclick = () => loadWorkspace(ws.id);
        item.innerHTML = `
            <div class="flex justify-between items-start">
                <div class="flex-1">
                    <h4 class="font-bold text-slate-800 group-hover:text-indigo-700">${ws.issue || t('msg_untitled_issue')}</h4>
                    <p class="text-xs text-slate-400 mt-1">ID: ${ws.id}</p>
                </div>
                <div class="flex flex-col items-end space-y-2">
                    <span class="text-xs font-mono text-slate-400 bg-slate-50 px-2 py-1 rounded">${ws.timestamp}</span>
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
        list.appendChild(item);
    });
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
        } else {
            console.error('[History] Load failed:', data.message);
            showAlert(t('msg_load_failed') + ': ' + (data.message || 'unknown'), t('title_error'), 'error');
        }
    } catch (error) {
        console.error('[History] Load error:', error);
        showAlert(t('msg_load_failed') + ': ' + error.message, t('title_error'), 'error');
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
