/**
 * API调用封装模块
 * 统一管理所有后端API通信
 * @module api
 */

import { showAlert } from './utils.js';

/**
 * API基础URL
 * @constant {string}
 */
const API_BASE = '/api';

/**
 * 统一的fetch封装 - 处理错误和JSON解析
 * @private
 * @param {string} url - API路径
 * @param {Object} options - fetch配置项
 * @returns {Promise<Object>} 解析后的JSON数据
 * @throws {Error} 网络错误或API错误
 */
async function apiFetch(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || `HTTP ${response.status}`);
        }

        return data;
    } catch (error) {
        if (error instanceof SyntaxError) {
            throw new Error('服务器返回数据格式错误');
        }
        throw error;
    }
}

// ==================== 讨论相关API ====================

/**
 * 启动新讨论
 * @param {Object} config - 讨论配置
 * @param {string} config.issue - 议题内容
 * @param {string} config.backend - 后端提供商
 * @param {string} [config.model] - 模型名称
 * @param {Object} [config.reasoning] - 推理配置
 * @param {number} config.rounds - 讨论轮数
 * @param {number} config.planners - 策论家数量
 * @param {number} config.auditors - 监察官数量
 * @param {Object} [config.agent_configs] - 代理配置
 * @param {boolean} [config.use_meta_orchestrator] - 是否使用元编排器
 * @returns {Promise<Object>} 启动结果
 */
export async function startDiscussion(config) {
    return apiFetch(`${API_BASE}/start`, {
        method: 'POST',
        body: JSON.stringify(config)
    });
}

/**
 * 停止当前讨论
 * @returns {Promise<Object>} 停止结果
 */
export async function stopDiscussion() {
    return apiFetch(`${API_BASE}/stop`, {
        method: 'POST'
    });
}

/**
 * 获取讨论状态
 * @returns {Promise<Object>} 讨论状态
 */
export async function getStatus() {
    return apiFetch(`${API_BASE}/status`);
}

/**
 * 获取实时事件流
 * @returns {Promise<Object>} 事件数据
 */
export async function getEvents() {
    return apiFetch(`${API_BASE}/events`);
}

/**
 * 重新生成报告
 * @param {Object} config - 重报配置
 * @param {string} config.backend - 后端提供商
 * @param {string} [config.model] - 模型名称
 * @param {Object} [config.reasoning] - 推理配置
 * @returns {Promise<Object>} 生成结果
 */
export async function reReport(config) {
    return apiFetch(`${API_BASE}/rereport`, {
        method: 'POST',
        body: JSON.stringify(config)
    });
}

/**
 * 修订报告
 * @param {Object} config - 修订配置
 * @param {string} config.feedback - 用户反馈
 * @param {string} config.backend - 后端提供商
 * @param {string} [config.model] - 模型名称
 * @param {Object} [config.reasoning] - 推理配置
 * @returns {Promise<Object>} 修订结果
 */
export async function reviseReport(config) {
    return apiFetch(`${API_BASE}/revise_report`, {
        method: 'POST',
        body: JSON.stringify(config)
    });
}

/**
 * 人工介入讨论
 * @param {Object} config - 介入配置
 * @param {string} config.stage - 介入阶段
 * @param {string} config.task - 介入任务
 * @returns {Promise<Object>} 介入结果
 */
export async function intervention(config) {
    return apiFetch(`${API_BASE}/intervention`, {
        method: 'POST',
        body: JSON.stringify(config)
    });
}

// ==================== 工作区管理API ====================

/**
 * 获取工作区列表
 * @returns {Promise<Object>} 工作区列表
 */
export async function getWorkspaces() {
    return apiFetch(`${API_BASE}/workspaces`);
}

/**
 * 删除工作区
 * @param {string} workspaceId - 工作区ID
 * @returns {Promise<Object>} 删除结果
 */
export async function deleteWorkspace(workspaceId) {
    return apiFetch(`${API_BASE}/workspaces/${workspaceId}`, {
        method: 'DELETE'
    });
}

// ==================== 导出相关API ====================

/**
 * 导出Markdown报告
 * @param {Object} config - 导出配置
 * @param {string} [config.workspace_id] - 工作区ID
 * @returns {Promise<Blob>} Markdown文件Blob
 */
export async function exportMarkdown(config = {}) {
    const response = await fetch(`${API_BASE}/export_md`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    });

    if (!response.ok) {
        const data = await response.json();
        throw new Error(data.message || '导出失败');
    }

    return response.blob();
}

/**
 * 导出PDF报告
 * @param {Object} config - 导出配置
 * @param {string} config.html_content - HTML内容
 * @returns {Promise<Blob>} PDF文件Blob
 */
export async function exportPdf(config) {
    const response = await fetch(`${API_BASE}/export_pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    });

    if (!response.ok) {
        const data = await response.json();
        throw new Error(data.message || 'PDF导出失败');
    }

    return response.blob();
}

// ==================== 预设管理API ====================

/**
 * 获取预设列表
 * @returns {Promise<Object>} 预设列表
 */
export async function getPresets() {
    return apiFetch(`${API_BASE}/presets`);
}

/**
 * 保存预设
 * @param {Object} preset - 预设配置
 * @param {string} preset.name - 预设名称
 * @param {Object} preset.config - 预设配置
 * @returns {Promise<Object>} 保存结果
 */
export async function savePreset(preset) {
    return apiFetch(`${API_BASE}/presets`, {
        method: 'POST',
        body: JSON.stringify(preset)
    });
}

/**
 * 删除预设
 * @param {string} name - 预设名称
 * @returns {Promise<Object>} 删除结果
 */
export async function deletePreset(name) {
    return apiFetch(`${API_BASE}/presets/${encodeURIComponent(name)}`, {
        method: 'DELETE'
    });
}

// ==================== 模型管理API ====================

/**
 * 获取OpenRouter模型列表
 * @returns {Promise<Object>} 模型列表
 */
export async function getOpenRouterModels() {
    return apiFetch(`${API_BASE}/openrouter/models`);
}

/**
 * 获取DeepSeek模型列表
 * @returns {Promise<Object>} 模型列表
 */
export async function getDeepSeekModels() {
    return apiFetch(`${API_BASE}/deepseek/models`);
}

// ==================== 系统配置API ====================

/**
 * 获取系统配置
 * @returns {Promise<Object>} 配置信息
 */
export async function getConfig() {
    return apiFetch(`${API_BASE}/config`);
}

/**
 * 保存系统配置
 * @param {Object} config - 配置对象
 * @returns {Promise<Object>} 保存结果
 */
export async function saveConfig(config) {
    return apiFetch(`${API_BASE}/config`, {
        method: 'POST',
        body: JSON.stringify(config)
    });
}

// ==================== 角色管理API ====================

/**
 * 获取角色列表
 * @returns {Promise<Object>} 角色列表
 */
export async function getRoles() {
    return apiFetch(`${API_BASE}/roles`);
}

/**
 * 验证角色配置
 * @param {Object} roleConfig - 角色配置
 * @returns {Promise<Object>} 验证结果
 */
export async function validateRole(roleConfig) {
    return apiFetch(`${API_BASE}/roles/validate`, {
        method: 'POST',
        body: JSON.stringify(roleConfig)
    });
}

/**
 * 设计新角色
 * @param {Object} designConfig - 设计配置
 * @param {string} designConfig.description - 角色描述
 * @param {string} designConfig.backend - 后端提供商
 * @param {string} [designConfig.model] - 模型名称
 * @returns {Promise<Object>} 设计结果
 */
export async function designRole(designConfig) {
    return apiFetch(`${API_BASE}/roles/design`, {
        method: 'POST',
        body: JSON.stringify(designConfig)
    });
}

/**
 * 保存角色
 * @param {Object} roleData - 角色数据
 * @returns {Promise<Object>} 保存结果
 */
export async function saveRole(roleData) {
    return apiFetch(`${API_BASE}/roles`, {
        method: 'POST',
        body: JSON.stringify(roleData)
    });
}

/**
 * 删除角色
 * @param {string} roleId - 角色ID
 * @returns {Promise<Object>} 删除结果
 */
export async function deleteRole(roleId) {
    return apiFetch(`${API_BASE}/roles/${roleId}`, {
        method: 'DELETE'
    });
}

// ==================== 认证相关API ====================

/**
 * 获取用户信息（简化版）
 * @returns {Promise<Object>} 用户信息
 */
export async function getUserInfo() {
    return apiFetch(`${API_BASE}/auth/user-info`);
}

/**
 * 获取用户详细信息
 * @returns {Promise<Object>} 详细用户信息
 */
export async function getUserDetailInfo() {
    return apiFetch(`${API_BASE}/auth/user/info`);
}

/**
 * 用户登出
 * @returns {Promise<Object>} 登出结果
 */
export async function logout() {
    return apiFetch(`${API_BASE}/auth/logout`, {
        method: 'POST'
    });
}

/**
 * 修改密码
 * @param {Object} passwordData - 密码数据
 * @param {string} passwordData.old_password - 旧密码
 * @param {string} passwordData.new_password - 新密码
 * @returns {Promise<Object>} 修改结果
 */
export async function changePassword(passwordData) {
    return apiFetch(`${API_BASE}/auth/user/change-password`, {
        method: 'POST',
        body: JSON.stringify(passwordData)
    });
}

/**
 * 禁用MFA
 * @param {Object} mfaData - MFA数据
 * @param {string} mfaData.password - 用户密码
 * @returns {Promise<Object>} 禁用结果
 */
export async function disableMfa(mfaData) {
    return apiFetch(`${API_BASE}/auth/mfa/disable`, {
        method: 'POST',
        body: JSON.stringify(mfaData)
    });
}

/**
 * 启用MFA
 * @param {Object} mfaData - MFA数据
 * @param {string} mfaData.token - 验证令牌
 * @returns {Promise<Object>} 启用结果
 */
export async function enableMfa(mfaData) {
    return apiFetch(`${API_BASE}/auth/mfa/enable`, {
        method: 'POST',
        body: JSON.stringify(mfaData)
    });
}

/**
 * 获取MFA设置
 * @returns {Promise<Object>} MFA配置
 */
export async function getMfaSetup() {
    return apiFetch(`${API_BASE}/auth/mfa/setup`);
}
