/**
 * AICouncil - Core Utility Functions
 * 通用工具函数模块
 */

/**
 * HTML转义函数，防止XSS攻击
 * @param {string} text - 需要转义的文本
 * @returns {string} 转义后的HTML字符串
 */
export function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * 显示通知消息模态框
 * @param {string} message - 消息内容
 * @param {string} [title=''] - 消息标题
 * @param {string} [type='info'] - 消息类型: 'info', 'warning', 'error'
 */
export function showAlert(message, title = '', type = 'info') {
    const modal = document.getElementById('alert-modal');
    const titleEl = document.getElementById('alert-title');
    const messageEl = document.getElementById('alert-message');
    const iconEl = document.getElementById('alert-icon');
    
    titleEl.innerText = title || '提示';
    messageEl.innerText = message;
    
    if (type === 'error') {
        iconEl.className = 'w-16 h-16 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto mb-4';
        iconEl.innerHTML = '<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>';
    } else if (type === 'warning') {
        iconEl.className = 'w-16 h-16 bg-amber-100 text-amber-600 rounded-full flex items-center justify-center mx-auto mb-4';
        iconEl.innerHTML = '<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>';
    } else {
        iconEl.className = 'w-16 h-16 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center mx-auto mb-4';
        iconEl.innerHTML = '<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>';
    }
    
    modal.classList.remove('hidden');
}

/**
 * 显示确认对话框
 * @param {string} message - 确认消息内容
 * @param {string} [title=''] - 确认框标题
 * @returns {Promise<boolean>} 用户点击确定返回true，取消返回false
 */
export function showConfirm(message, title = '') {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirm-modal');
        const titleEl = document.getElementById('confirm-title');
        const messageEl = document.getElementById('confirm-message');
        const okBtn = document.getElementById('confirm-ok-btn');
        const cancelBtn = document.getElementById('confirm-cancel-btn');
        
        titleEl.innerText = title || '确认';
        messageEl.innerText = message;
        
        const handleOk = () => {
            modal.classList.add('hidden');
            cleanup();
            resolve(true);
        };
        
        const handleCancel = () => {
            modal.classList.add('hidden');
            cleanup();
            resolve(false);
        };
        
        const cleanup = () => {
            okBtn.removeEventListener('click', handleOk);
            cancelBtn.removeEventListener('click', handleCancel);
        };
        
        okBtn.addEventListener('click', handleOk);
        cancelBtn.addEventListener('click', handleCancel);
        
        modal.classList.remove('hidden');
    });
}

/**
 * 显示密码输入框
 * @param {string} message - 输入框提示消息
 * @param {string} [title='安全验证'] - 输入框标题
 * @returns {Promise<string|null>} 用户确认返回密码，取消返回null
 */
export function showPasswordInput(message, title = '安全验证') {
    return new Promise((resolve) => {
        const modal = document.getElementById('password-input-modal');
        const titleEl = document.getElementById('password-input-title');
        const messageEl = document.getElementById('password-input-message');
        const inputField = document.getElementById('password-input-field');
        const okBtn = document.getElementById('password-input-ok-btn');
        const cancelBtn = document.getElementById('password-input-cancel-btn');
        
        titleEl.innerText = title;
        messageEl.innerText = message;
        inputField.value = '';
        
        const handleOk = () => {
            const password = inputField.value;
            if (!password) {
                inputField.focus();
                return;
            }
            modal.classList.add('hidden');
            cleanup();
            resolve(password);
        };
        
        const handleCancel = () => {
            modal.classList.add('hidden');
            cleanup();
            resolve(null);
        };
        
        const handleEnter = (e) => {
            if (e.key === 'Enter') {
                handleOk();
            }
        };
        
        const cleanup = () => {
            okBtn.removeEventListener('click', handleOk);
            cancelBtn.removeEventListener('click', handleCancel);
            inputField.removeEventListener('keypress', handleEnter);
        };
        
        okBtn.addEventListener('click', handleOk);
        cancelBtn.addEventListener('click', handleCancel);
        inputField.addEventListener('keypress', handleEnter);
        
        modal.classList.remove('hidden');
        setTimeout(() => inputField.focus(), 100);
    });
}

/**
 * 复制文本到剪贴板
 * @param {string} text - 要复制的文本内容
 * @returns {Promise<boolean>} 复制成功返回true，失败返回false
 */
export async function copyToClipboard(text) {
    try {
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(text);
            return true;
        } else {
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            textArea.style.top = '-999999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            const result = document.execCommand('copy');
            textArea.remove();
            return result;
        }
    } catch (err) {
        console.error('复制失败:', err);
        return false;
    }
}

/**
 * 格式化日期时间
 * @param {Date|string|number} date - 日期对象、字符串或时间戳
 * @param {string} [format='YYYY-MM-DD HH:mm:ss'] - 日期格式
 * @returns {string} 格式化后的日期字符串
 */
export function formatDate(date, format = 'YYYY-MM-DD HH:mm:ss') {
    const d = date instanceof Date ? date : new Date(date);
    
    if (isNaN(d.getTime())) {
        return 'Invalid Date';
    }
    
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    const seconds = String(d.getSeconds()).padStart(2, '0');
    
    return format
        .replace('YYYY', year)
        .replace('MM', month)
        .replace('DD', day)
        .replace('HH', hours)
        .replace('mm', minutes)
        .replace('ss', seconds);
}
