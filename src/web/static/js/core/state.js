/**
 * 状态管理模块 - 全局应用状态
 * @module state
 */

// ==================== 应用状态 ====================

/**
 * 讨论运行状态
 * @type {boolean}
 */
export let isRunning = false;

/**
 * 当前会话ID
 * @type {string|null}
 */
export let currentSessionId = null;

/**
 * Meta-Orchestrator模式标志
 * @type {boolean}
 */
export let isOrchestratorMode = false;

/**
 * 报告生成阶段标志
 * @type {boolean}
 */
export let isReportingPhase = false;

// ==================== 讨论进度状态 ====================

/**
 * 当前轮次
 * @type {number}
 */
export let currentRound = 1;

/**
 * 当前进度百分比 (0-100)
 * @type {number}
 */
export let currentProgress = 0;

/**
 * 最后获取的事件数量
 * @type {number}
 */
export let lastEventCount = 0;

/**
 * 最后获取的日志数量
 * @type {number}
 */
export let lastLogCount = 0;

// ==================== UI状态 ====================

/**
 * 缓存的报告HTML（避免重复替换导致闪烁）
 * @type {string|null}
 */
export let cachedReportHtml = null;

/**
 * OpenRouter模型是否已获取
 * @type {boolean}
 */
export let openRouterModelsFetched = false;

/**
 * 正在获取模型标志
 * @type {boolean}
 */
export let isFetchingModels = false;

// ==================== 语言设置 ====================

/**
 * 当前语言
 * @type {string}
 */
export let currentLang = 'zh-CN';

// ==================== 状态更新方法 ====================

/**
 * 设置讨论运行状态
 * @param {boolean} value - 运行状态
 */
export function setIsRunning(value) {
    isRunning = value;
}

/**
 * 设置当前会话ID
 * @param {string|null} value - 会话ID
 */
export function setCurrentSessionId(value) {
    currentSessionId = value;
}

/**
 * 设置Meta-Orchestrator模式
 * @param {boolean} value - 是否启用
 */
export function setIsOrchestratorMode(value) {
    isOrchestratorMode = value;
}

/**
 * 设置报告生成阶段
 * @param {boolean} value - 是否在报告阶段
 */
export function setIsReportingPhase(value) {
    isReportingPhase = value;
}

/**
 * 设置当前轮次
 * @param {number} value - 轮次数
 */
export function setCurrentRound(value) {
    currentRound = value;
}

/**
 * 设置当前进度
 * @param {number} value - 进度百分比
 */
export function setCurrentProgress(value) {
    currentProgress = value;
}

/**
 * 设置最后事件数量
 * @param {number} value - 事件数量
 */
export function setLastEventCount(value) {
    lastEventCount = value;
}

/**
 * 设置最后日志数量
 * @param {number} value - 日志数量
 */
export function setLastLogCount(value) {
    lastLogCount = value;
}

/**
 * 设置缓存的报告HTML
 * @param {string|null} value - HTML内容
 */
export function setCachedReportHtml(value) {
    cachedReportHtml = value;
}

/**
 * 设置OpenRouter模型获取状态
 * @param {boolean} value - 是否已获取
 */
export function setOpenRouterModelsFetched(value) {
    openRouterModelsFetched = value;
}

/**
 * 设置正在获取模型状态
 * @param {boolean} value - 是否正在获取
 */
export function setIsFetchingModels(value) {
    isFetchingModels = value;
}

/**
 * 获取当前语言
 * @returns {string} 语言代码 (zh-CN | en-US)
 */
export function getCurrentLang() {
    return currentLang;
}

/**
 * 设置当前语言
 * @param {string} value - 语言代码 (zh-CN | en-US)
 */
export function setCurrentLang(value) {
    currentLang = value;
    // 保存到localStorage
    try {
        localStorage.setItem('aicouncil_lang', value);
    } catch (e) {
        console.warn('无法保存语言设置到localStorage:', e);
    }
}

/**
 * 重置所有状态到初始值
 */
export function resetState() {
    isRunning = false;
    currentSessionId = null;
    isOrchestratorMode = false;
    isReportingPhase = false;
    currentRound = 1;
    currentProgress = 0;
    lastEventCount = 0;
    lastLogCount = 0;
    cachedReportHtml = null;
    // 不重置 openRouterModelsFetched 和 isFetchingModels（全局缓存）
    // 不重置 currentLang（用户偏好设置）
}

/**
 * 从localStorage初始化语言设置
 */
export function initLanguage() {
    try {
        const saved = localStorage.getItem('aicouncil_lang');
        if (saved && ['zh-CN', 'en-US'].includes(saved)) {
            currentLang = saved;
        }
    } catch (e) {
        console.warn('无法从localStorage读取语言设置:', e);
    }
}
