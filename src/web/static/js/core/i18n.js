/**
 * i18n.js - 国际化（Internationalization）模块
 * 
 * 功能：
 * - 管理多语言翻译（中文/英文）
 * - 自动更新 DOM 元素的文本内容
 * - 支持 data-i18n, data-i18n-placeholder, data-i18n-title 属性
 * - 处理图标 emoji 前缀
 * - 持久化语言设置到 localStorage
 * 
 * 导出接口：
 * - t(key): 翻译函数，根据当前语言返回对应文本
 * - setLanguage(lang): 切换语言，更新所有 i18n 元素
 * - initLanguage(): 初始化语言（从 localStorage 读取并应用）
 * - getCurrentLang(): 获取当前语言代码
 * 
 * @module i18n
 */

/**
 * 翻译字典
 * @type {Object.<string, Object.<string, string>>}
 * @private
 */
const translations = {
    zh: {
        nav_title: "AI Council",
        nav_subtitle: "元老院议事厅",
        nav_toggle_logs: "切换日志显示",
        nav_orchestrator_mode: "智能编排",
        nav_settings: "系统设置",
        nav_roles: "角色管理",
        nav_presets: "元老院编制",
        input_issue_label: "议题内容",
        input_issue_placeholder: "请输入您想要讨论的议题（支持多行输入，Enter 发送，Shift+Enter 换行）...",
        input_backend_label: "后端",
        input_model_label: "全局模型 (可选)",
        input_model_placeholder: "默认模型",
        input_reasoning_label: "推理强度",
        reasoning_off: "关闭",
        reasoning_low: "推理: Low",
        reasoning_medium: "推理: Medium",
        reasoning_high: "推理: High",
        input_rounds_label: "轮数",
        input_planners_label: "策论家",
        input_auditors_label: "监察官",
        btn_start: "开始议事",
        btn_advanced: "高级配置",
        advanced_config_title: "高级配置",
        tab_basic_config: "基础配置",
        tab_agent_config: "席位专家配置",
        tab_presets: "元老院编制",
        tab_settings: "系统设置",
        agent_config_desc: "为不同席位的专家指定特定的模型后端和参数",
        presets_name_placeholder: "输入编制名称 (例如: 3人-DeepSeek-高强度)",
        btn_load: "加载",
        btn_delete: "删除",
        btn_apply: "应用",
        btn_load_preset: "加载编制",
        btn_save_current: "保存当前配置",
        btn_history: "历史",
        btn_stop: "停止",
        advanced_title: "席位专家配置",
        advanced_reset: "重置为默认",
        role_leader: "议长 (Leader)",
        role_reporter: "记录员 (Reporter)",
        role_planner: "策论家 (Planner)",
        role_auditor: "监察官 (Auditor)",
        backend_default: "默认后端",
        agent_model_placeholder: "模型名称 (可选)",
        discussion_flow_title: "议事过程",
        intervention_placeholder: "输入干预指令（例如：请更多关注成本问题）...",
        btn_send_intervention: "发送干预",
        final_report_title: "最终议事报告",
        btn_re_report: "重新生成报告",
        btn_copy: "复制",
        btn_download: "下载报告",
        btn_download_html: "HTML 格式",
        btn_download_pdf: "PDF 格式",
        btn_download_image: "图片格式",
        btn_download_md: "Markdown 格式",
        btn_maximize: "最大化",
        btn_restore: "还原",
        loader_text: "正在进行议事讨论...",
        loader_subtext: "元老们正在激烈辩论中",
        log_title: "系统执行日志",
        btn_clear: "清除",
        presets_title: "元老院编制管理",
        presets_save_new: "保存当前配置为新编制",
        presets_list: "已保存的编制",
        btn_save: "保存",
        btn_close: "关闭",
        msg_preset_saved: "编制已保存",
        msg_preset_deleted: "编制已删除",
        msg_preset_loaded: "编制已加载",
        msg_preset_name_empty: "请输入编制名称",
        confirm_delete_preset: "确定要删除该编制吗？",
        history_modal_title: "议事历史记录",
        history_loading: "正在加载历史记录...",
        confirm_title: "确认",
        btn_cancel: "取消",
        btn_confirm: "确认",
        alert_title: "提示",
        btn_ok: "确定",
        settings_modal_title: "系统全局设置",
        roles_title: "角色管理",
        role_tag_core: "核心角色",
        role_tag_advanced: "高级角色",
        role_version: "版本",
        role_stages: "阶段",
        role_parameters: "参数",
        role_btn_detail: "查看详情",
        role_btn_reload: "重新加载",
        role_reload_success: "角色配置已重新加载",
        role_reload_failed: "重新加载失败",
        role_prompt_preview: "提示词预览",
        settings_api_keys: "API 密钥配置",
        settings_search_engines: "搜索增强引擎 (可多选)",
        settings_browser_path: "浏览器可执行文件路径 (Baidu/Bing 搜索)",
        settings_browser_path_placeholder: "例如: C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        search_stable: "不稳定",
        search_stable_good: "稳定",
        search_chinese: "中文",
        search_english: "英文",
        btn_save_apply: "保存并应用",
        status_processing: "正在议事...",
        empty_discussion_hint: "请输入议题并开始议事",
        empty_report_hint: "议事完成后将在此生成报告",
        msg_input_issue: "请输入议题内容",
        msg_stop_confirm: "停止后，当前的讨论进度将会丢失，且无法生成最终报告。",
        msg_stop_title: "确认停止议事？",
        msg_save_success: "设置已保存并应用",
        msg_save_failed: "保存失败",
        msg_copy_success: "报告已复制到剪贴板",
        msg_copy_failed: "复制失败",
        msg_download_failed: "下载失败",
        msg_pdf_failed: "PDF 导出失败，请尝试下载 HTML 或图片",
        msg_history_empty: "暂无历史记录",
        msg_intervention_sent: "干预指令已发送",
        msg_intervention_failed: "发送失败",
        msg_start_failed: "启动失败",
        msg_request_failed: "请求发送失败",
        msg_report_not_ready: "报告尚未生成，无法下载",
        msg_image_failed: "图片转换失败，请尝试下载 HTML 格式",
        msg_delete_success: "历史记录已成功删除",
        msg_delete_failed: "删除失败",
        msg_load_success: "历史记录加载成功，正在同步讨论流...",
        msg_load_failed: "加载失败",
        msg_confirm_delete: "确定要删除这条历史记录及其相关文件吗？此操作不可撤销。",
        msg_confirm_load: "加载历史记录将清除当前讨论内容，是否继续？",
        title_success: "成功",
        title_error: "错误",
        title_hint: "提示",
        title_confirm_delete: "确认删除",
        title_confirm_load: "确认加载",
        msg_initializing_hall: "正在初始化议事厅...",
        msg_connecting_backend: "正在连接后端引擎...",
        status_running: "正在讨论",
        status_ready: "就绪",
        msg_restoring_progress: "正在恢复议事进度...",
        msg_consensus_reached: "📜 议事达成共识，正在生成最终报告...",
        msg_writing_report: "正在撰写最终议事报告...",
        msg_thinking_process: "思考过程",
        msg_search_progress: "搜索进度",
        msg_details: "详情",
        msg_auditor_review: "审计总结",
        msg_target: "针对",
        msg_issues: "⚠️ 质疑点",
        msg_suggestions: "💡 改进建议",
        msg_audit_summary: "📝 审计总结",
        msg_core_goal: "🎯 核心目标",
        msg_key_questions: "❓ 关键问题",
        msg_boundaries: "🚧 讨论边界",
        msg_report_outline: "📋 报告大纲设计",
        msg_instructions: "📢 本轮指令",
        msg_core_idea: "💡 核心思路",
        msg_execution_steps: "🚀 执行步骤",
        msg_advantages: "✅ 优势",
        msg_resource_requirements: "🛠️ 资源需求",
        msg_converting: "转换中...",
        msg_re_reporting: "正在重新生成报告...",
        msg_re_reporting_sub: "正在使用 {backend} 重新撰写报告",
        msg_writing_report_sub: "请耐心等待元老院达成共识",
        msg_consensus_reached_sub: "请稍候，正在整理元老们的智慧结晶",
        msg_untitled_issue: "未命名议题",
        btn_delete_record: "删除记录",
        msg_unknown_plan: "未知方案",
        msg_unrated: "未评级",
        msg_undefined: "未定义",
        msg_none: "无",
        msg_browser_missing: "未找到浏览器可执行文件，联网搜索（Baidu/Bing）可能无法使用。请在设置中手动配置浏览器路径。"
    },
    en: {
        nav_title: "AI Council",
        nav_subtitle: "Senate Discussion Hall",
        nav_toggle_logs: "Toggle Logs",
        nav_orchestrator_mode: "Orchestrator",
        nav_settings: "System Settings",
        nav_roles: "Role Management",
        nav_presets: "Council Formations",
        input_issue_label: "Issue Content",
        input_issue_placeholder: "Enter the issue you want to discuss (supports multi-line, Enter to send, Shift+Enter for new line)...",
        input_backend_label: "Backend",
        input_model_label: "Global Model (Optional)",
        input_model_placeholder: "Default Model",
        input_reasoning_label: "Reasoning",
        reasoning_off: "Off",
        reasoning_low: "Reasoning: Low",
        reasoning_medium: "Reasoning: Medium",
        reasoning_high: "Reasoning: High",
        input_rounds_label: "Rounds",
        input_planners_label: "Planners",
        input_auditors_label: "Auditors",
        btn_start: "Start Discussion",
        btn_advanced: "Advanced",
        advanced_config_title: "Advanced Configuration",
        tab_basic_config: "Basic Configuration",
        tab_agent_config: "Seat Expert Configuration",
        tab_presets: "Council Presets",
        tab_settings: "System Settings",
        agent_config_desc: "Specify specific model backends and parameters for different seat experts",
        presets_name_placeholder: "Enter preset name (e.g., 3-member-DeepSeek-high)",
        btn_load: "Load",
        btn_delete: "Delete",
        btn_apply: "Apply",
        btn_load_preset: "Load Formation",
        btn_save_current: "Save Current",
        btn_history: "History",
        btn_stop: "Stop",
        advanced_title: "Seat Expert Configuration",
        advanced_reset: "Reset to Default",
        role_leader: "Leader",
        role_reporter: "Reporter",
        role_planner: "Planner",
        role_auditor: "Auditor",
        backend_default: "Default Backend",
        agent_model_placeholder: "Model Name (Optional)",
        discussion_flow_title: "Discussion Process",
        intervention_placeholder: "Enter intervention (e.g., focus more on costs)...",
        btn_send_intervention: "Send",
        final_report_title: "Final Report",
        btn_re_report: "Regenerate",
        btn_copy: "Copy",
        btn_download: "Download",
        btn_download_html: "HTML Format",
        btn_download_pdf: "PDF Format",
        btn_download_image: "Image Format",
        btn_download_md: "Markdown Format",
        btn_maximize: "Maximize",
        btn_restore: "Restore",
        loader_text: "Discussion in progress...",
        loader_subtext: "The elders are debating fiercely",
        log_title: "System Logs",
        btn_clear: "Clear",
        presets_title: "Council Formations",
        presets_save_new: "Save Current as New Formation",
        presets_list: "Saved Formations",
        btn_save: "Save",
        btn_close: "Close",
        msg_preset_saved: "Formation saved",
        msg_preset_deleted: "Formation deleted",
        msg_preset_loaded: "Formation loaded",
        msg_preset_name_empty: "Please enter a formation name",
        confirm_delete_preset: "Are you sure you want to delete this formation?",
        history_modal_title: "Discussion History",
        history_loading: "Loading history...",
        confirm_title: "Confirm",
        btn_cancel: "Cancel",
        btn_confirm: "Confirm",
        alert_title: "Alert",
        btn_ok: "OK",
        settings_modal_title: "Global Settings",
        roles_title: "Role Management",
        role_tag_core: "Core Role",
        role_tag_advanced: "Advanced Role",
        role_version: "Version",
        role_stages: "Stages",
        role_parameters: "Parameters",
        role_btn_detail: "View Details",
        role_btn_reload: "Reload",
        role_reload_success: "Role configuration reloaded",
        role_reload_failed: "Reload failed",
        role_prompt_preview: "Prompt Preview",
        settings_api_keys: "API Key Configuration",
        settings_search_engines: "Search Engines (Multi-select)",
        settings_browser_path: "Browser Executable Path (Baidu/Bing Search)",
        settings_browser_path_placeholder: "e.g., C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        search_stable: "Not Stable",
        search_stable_good: "Stable",
        search_chinese: "Chinese",
        search_english: "English",
        btn_save_apply: "Save & Apply",
        status_processing: "Processing...",
        empty_discussion_hint: "Enter an issue to start the discussion",
        empty_report_hint: "Report will be generated here after discussion",
        msg_input_issue: "Please enter the issue content",
        msg_stop_confirm: "Stopping will lose current progress and no report will be generated.",
        msg_stop_title: "Confirm Stop?",
        msg_save_success: "Settings saved and applied",
        msg_save_failed: "Save failed",
        msg_copy_success: "Report copied to clipboard",
        msg_copy_failed: "Copy failed",
        msg_download_failed: "Download failed",
        msg_pdf_failed: "PDF export failed, please try HTML or Image",
        msg_history_empty: "No history records",
        msg_intervention_sent: "Intervention sent",
        msg_intervention_failed: "Send failed",
        msg_start_failed: "Start failed",
        msg_request_failed: "Request failed",
        msg_report_not_ready: "Report not ready, cannot download",
        msg_image_failed: "Image conversion failed, please try HTML",
        msg_delete_success: "History deleted successfully",
        msg_delete_failed: "Delete failed",
        msg_load_success: "History loaded successfully, syncing flow...",
        msg_load_failed: "Load failed",
        msg_confirm_delete: "Are you sure you want to delete this record? This cannot be undone.",
        msg_confirm_load: "Loading history will clear current discussion. Continue?",
        title_success: "Success",
        title_error: "Error",
        title_hint: "Hint",
        title_confirm_delete: "Confirm Delete",
        title_confirm_load: "Confirm Load",
        msg_initializing_hall: "Initializing discussion hall...",
        msg_connecting_backend: "Connecting to backend engine...",
        status_running: "Running",
        status_ready: "Ready",
        msg_restoring_progress: "Restoring progress...",
        msg_consensus_reached: "📜 Consensus reached, generating final report...",
        msg_writing_report: "Writing final report...",
        msg_thinking_process: "Thinking Process",
        msg_search_progress: "SEARCH PROGRESS",
        msg_details: "Details",
        msg_auditor_review: "Auditor Review",
        msg_target: "Target",
        msg_issues: "⚠️ Issues",
        msg_suggestions: "💡 Suggestions",
        msg_audit_summary: "📝 Audit Summary",
        msg_core_goal: "🎯 Core Goal",
        msg_key_questions: "❓ Key Questions",
        msg_boundaries: "🚧 Boundaries",
        msg_report_outline: "📋 Report Outline",
        msg_instructions: "📢 Instructions",
        msg_core_idea: "💡 Core Idea",
        msg_execution_steps: "🚀 Execution Steps",
        msg_advantages: "✅ Advantages",
        msg_resource_requirements: "🛠️ Requirements",
        msg_converting: "Converting...",
        msg_re_reporting: "Regenerating report...",
        msg_re_reporting_sub: "Rewriting report using {backend}",
        msg_writing_report_sub: "Please wait for the Senate to reach a consensus",
        msg_consensus_reached_sub: "Please wait, gathering the wisdom of the elders",
        msg_untitled_issue: "Untitled Issue",
        btn_delete_record: "Delete Record",
        msg_unknown_plan: "Unknown Plan",
        msg_unrated: "Unrated",
        msg_undefined: "Undefined",
        msg_none: "None",
        msg_browser_missing: "Browser executable not found. Web search (Baidu/Bing) may not work. Please configure the browser path in settings."
    }
};

/**
 * 当前语言代码
 * @type {string}
 * @private
 */
let currentLang = localStorage.getItem('language') || 'zh';

/**
 * 翻译函数 - 根据当前语言返回对应的翻译文本
 * 
 * @param {string} key - 翻译键
 * @returns {string} 翻译后的文本，如果找不到对应翻译则返回键本身
 * 
 * @example
 * t('btn_start') // => "开始议事" (zh) 或 "Start Discussion" (en)
 */
export function t(key) {
    return translations[currentLang][key] || key;
}

/**
 * 获取当前语言代码
 * 
 * @returns {string} 当前语言代码（'zh' 或 'en'）
 * 
 * @example
 * getCurrentLang() // => "zh"
 */
export function getCurrentLang() {
    return currentLang;
}

/**
 * 切换语言并更新所有国际化元素
 * 
 * 功能：
 * 1. 更新 currentLang 变量
 * 2. 保存到 localStorage
 * 3. 更新文档标题
 * 4. 更新语言切换按钮状态
 * 5. 更新所有 data-i18n 元素的文本内容（保留图标 emoji）
 * 6. 更新所有 data-i18n-placeholder 元素的 placeholder 属性
 * 7. 更新所有 data-i18n-title 元素的 title 属性
 * 8. 触发 UI 更新（重新渲染 Agent 配置）
 * 
 * @param {string} lang - 语言代码（'zh' 或 'en'）
 * 
 * @example
 * setLanguage('en') // 切换到英文
 */
export function setLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('language', lang);
    
    // 更新文档标题
    document.title = lang === 'zh' ? 'AI Council - 实时讨论视图' : 'AI Council - Real-time Discussion';

    // 更新语言切换按钮状态
    const zhBtn = document.getElementById('lang-zh');
    const enBtn = document.getElementById('lang-en');
    if (zhBtn && enBtn) {
        zhBtn.className = lang === 'zh' 
            ? 'px-3 py-1 text-xs font-bold bg-blue-600 text-white rounded-md shadow-sm transition-all'
            : 'px-3 py-1 text-xs font-medium text-slate-400 hover:text-slate-200 transition-all';
        enBtn.className = lang === 'en'
            ? 'px-3 py-1 text-xs font-bold bg-blue-600 text-white rounded-md shadow-sm transition-all'
            : 'px-3 py-1 text-xs font-medium text-slate-400 hover:text-slate-200 transition-all';
    }

    // 更新所有带有 data-i18n 的元素
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (translations[lang][key]) {
            // 如果元素包含图标（如 ⚙️），保留图标
            const iconMatch = el.innerHTML.match(/^([\uD800-\uDBFF][\uDC00-\uDFFF]|[\u2600-\u27BF]|💬|📜|⚙️|⚠️|💡|📝|🎯|❓|🚧|📋|📢|🚀|✅|🛠️)\s*/);
            if (iconMatch) {
                const translatedText = translations[lang][key];
                // 如果翻译后的文本已经包含了相同的图标，则不再重复添加
                if (translatedText.startsWith(iconMatch[0].trim())) {
                    el.innerHTML = translatedText;
                } else {
                    el.innerHTML = iconMatch[0] + translatedText;
                }
            } else {
                el.innerText = translations[lang][key];
            }
        }
    });

    // 更新所有带有 data-i18n-placeholder 的元素
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (translations[lang][key]) {
            el.placeholder = translations[lang][key];
        }
    });

    // 更新所有带有 data-i18n-title 的元素
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
        const key = el.getAttribute('data-i18n-title');
        if (translations[lang][key]) {
            el.title = translations[lang][key];
        }
    });

    // 触发外部 UI 更新（需要由调用方处理）
    // 例如：重新渲染 Agent 配置 UI
    if (window.updateAgentConfigsUI) {
        window.updateAgentConfigsUI();
    }
}

/**
 * 初始化语言设置
 * 
 * 从 localStorage 读取保存的语言设置并应用到页面。
 * 如果没有保存的设置，则使用默认语言 'zh'。
 * 
 * 应在页面加载完成后调用。
 * 
 * @example
 * // 在页面加载时初始化语言
 * document.addEventListener('DOMContentLoaded', () => {
 *     initLanguage();
 * });
 */
export function initLanguage() {
    const savedLang = localStorage.getItem('language') || 'zh';
    setLanguage(savedLang);
}
