/**
 * @fileoverview 报告导出模块
 * @module modules/export
 * @description 负责报告的各种格式导出（HTML, PDF, PNG, Markdown）
 */

import { exportMarkdown, exportPdf } from '../core/api.js';
import { showAlert } from '../core/utils.js';

// 使用全局t()函数（定义在index.html中）
const t = window.t || ((key) => key);

// 全局DOM引用（由主应用初始化）
let reportIframe = null;

/**
 * 初始化导出模块
 * @param {HTMLIFrameElement} iframe - 报告iframe元素
 * @returns {void}
 */
export function initExportModule(iframe) {
    reportIframe = iframe || document.getElementById('report-iframe');
}

/**
 * 切换下载下拉菜单的显示状态
 * @returns {void}
 */
export function toggleDownloadDropdown() {
    const dropdown = document.getElementById('download-dropdown');
    dropdown.classList.toggle('show');
}

/**
 * 导出报告为HTML文件
 * @returns {void}
 */
export function exportAsHTML() {
    if (reportIframe && reportIframe.srcdoc) {
        const blob = new Blob([reportIframe.srcdoc], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
        downloadFile(blob, `议事报告_${timestamp}.html`);
        URL.revokeObjectURL(url);
    } else {
        showAlert(t('msg_report_not_ready'), t('title_hint'));
    }
}

/**
 * 导出报告为Markdown文件（服务器端转换）
 * @async
 * @param {Event} e - 点击事件对象
 * @returns {Promise<void>}
 */
export async function exportAsMarkdown(e) {
    if (!(reportIframe && reportIframe.srcdoc)) {
        showAlert(t('msg_report_not_ready'), t('title_hint'));
        return;
    }
    
    const btn = e ? e.target.closest('button') : null;
    const originalText = btn ? btn.innerText : '';
    
    try {
        if (btn) {
            btn.disabled = true;
            btn.innerText = '🔄 转换中...';
        }
        
        console.log('开始Markdown导出...');
        
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
        const filename = `议事报告_${timestamp}.md`;
        
        // 调用API导出Markdown
        const blob = await exportMarkdown({
            html: reportIframe.srcdoc,
            filename: filename
        });
        
        downloadFile(blob, filename);
        
        console.log('✅ Markdown导出成功');
        showAlert('Markdown格式导出成功！', t('title_success'));
        
    } catch (error) {
        console.error('Markdown导出失败:', error);
        showAlert('Markdown导出失败: ' + error.message, t('title_error'), 'error');
    } finally {
        if (btn) {
            btn.innerText = originalText;
            btn.disabled = false;
        }
    }
}

/**
 * 展开所有折叠元素（用于导出）
 * @private
 * @param {Document} doc - iframe文档对象
 * @returns {Array<Object>} 折叠元素数组，用于恢复
 */
function expandCollapsedElements(doc) {
    const collapsedElements = [];
    
    try {
        // 查找所有带 'collapsed' 类的元素
        const collapsedItems = doc.querySelectorAll('.collapsed');
        collapsedItems.forEach(elem => {
            collapsedElements.push(elem);
            elem.classList.remove('collapsed');
        });
        
        // 查找所有 details 元素并展开
        const detailsElements = doc.querySelectorAll('details:not([open])');
        detailsElements.forEach(elem => {
            collapsedElements.push({ elem, type: 'details' });
            elem.setAttribute('open', '');
        });
        
        // 查找所有隐藏元素（hidden类）
        const hiddenElements = doc.querySelectorAll('.hidden:not(script):not(style)');
        hiddenElements.forEach(elem => {
            // 只展开有实际内容的元素
            if (elem.textContent.trim() || elem.querySelector('img, svg, canvas')) {
                collapsedElements.push({ elem, type: 'hidden' });
                elem.classList.remove('hidden');
            }
        });
        
        console.log(`展开了 ${collapsedElements.length} 个折叠元素`);
    } catch (err) {
        console.warn('展开折叠内容时出错:', err);
    }
    
    return collapsedElements;
}

/**
 * 恢复折叠元素的原始状态
 * @private
 * @param {Array<Object>} collapsedElements - 折叠元素数组
 * @returns {void}
 */
function restoreCollapsedElements(collapsedElements) {
    try {
        collapsedElements.forEach(item => {
            if (item.type === 'details') {
                item.elem.removeAttribute('open');
            } else if (item.type === 'hidden') {
                item.elem.classList.add('hidden');
            } else if (item.classList) {
                item.classList.add('collapsed');
            }
        });
        console.log('已恢复折叠状态');
    } catch (err) {
        console.warn('恢复折叠状态时出错:', err);
    }
}

/**
 * 导出报告为PDF文件（优先使用Playwright服务器端渲染）
 * @async
 * @param {Event} e - 点击事件对象
 * @returns {Promise<void>}
 */
export async function exportAsPDF(e) {
    if (!(reportIframe && reportIframe.contentDocument && reportIframe.contentDocument.body)) {
        showAlert(t('msg_report_not_ready'), t('title_hint'));
        return;
    }

    const btn = e?.currentTarget;
    const originalText = btn ? btn.innerText : '';
    if (btn) {
        btn.innerText = '生成中...';
        btn.disabled = true;
    }

    // 保存折叠状态并全部展开
    const collapsedElements = expandCollapsedElements(reportIframe.contentDocument);

    try {
        // 优先尝试使用Playwright（高质量PDF导出）
        try {
            let htmlContent = reportIframe.contentDocument.documentElement.outerHTML;
            
            // 替换CDN链接为本地路径（确保ECharts图表能正确渲染）
            htmlContent = htmlContent.replace(
                /https?:\/\/[^"']+echarts[^"']*(\.min)?\.js/gi,
                '/static/vendor/echarts.min.js'
            );
            
            // 如果使用了相对路径，转换为完整URL
            htmlContent = htmlContent.replace(
                /src="\/static\//g,
                `src="http://127.0.0.1:5000/static/`
            );
            htmlContent = htmlContent.replace(
                /href="\/static\//g,
                `href="http://127.0.0.1:5000/static/`
            );
            
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
            const filename = `Council_Report_${timestamp}.pdf`;
            
            // 调用API导出PDF
            const blob = await exportPdf({
                html: htmlContent,
                filename: filename
            });
            
            downloadFile(blob, filename);
            
            showAlert(
                '✅ PDF已导出（高质量版本，保留超链接）',
                '成功',
                'success'
            );
        } catch (playwrightError) {
            // Playwright导出失败，降级到传统方式
            console.warn('Playwright PDF导出失败，降级到传统方式:', playwrightError);
            await exportAsPDFLegacy();
        }
    } catch (error) {
        console.error('PDF export error:', error);
        showAlert(
            error.message || t('msg_pdf_failed'),
            t('title_error'),
            'error'
        );
    } finally {
        // 恢复折叠状态
        restoreCollapsedElements(collapsedElements);
        
        if (btn) {
            btn.innerText = originalText;
            btn.disabled = false;
        }
    }
}

/**
 * 旧版PDF导出（使用html2canvas + jsPDF，作为后备方案）
 * @async
 * @private
 * @returns {Promise<void>}
 * @throws {Error} 当报告未就绪或依赖库未加载时抛出错误
 */
async function exportAsPDFLegacy() {
    if (!(reportIframe && reportIframe.contentDocument && reportIframe.contentDocument.body)) {
        throw new Error(t('msg_report_not_ready'));
    }

    if (!window.jspdf || !window.jspdf.jsPDF) {
        throw new Error('jsPDF not loaded');
    }

    const { jsPDF } = window.jspdf;
    const canvas = await html2canvas(reportIframe.contentDocument.body, {
        useCORS: true,
        allowTaint: true,
        backgroundColor: '#ffffff',
        scale: 2
    });

    const imgData = canvas.toDataURL('image/png');
    const pdf = new jsPDF('p', 'pt', 'a4');
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    const imgWidth = pageWidth;
    const imgHeight = canvas.height * (imgWidth / canvas.width);

    let heightLeft = imgHeight;
    let position = 0;

    pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
    heightLeft -= pageHeight;

    while (heightLeft > 0) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
        heightLeft -= pageHeight;
    }

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    pdf.save(`Council_Report_${timestamp}.pdf`);
    
    showAlert(
        'PDF已导出（传统方式，超链接渲染为纯文本）',
        '成功',
        'success'
    );
}

/**
 * 导出报告为PNG截图（长图）
 * @async
 * @param {Event} e - 点击事件对象
 * @returns {Promise<void>}
 */
export async function exportAsScreenshot(e) {
    if (!(reportIframe && reportIframe.contentDocument && reportIframe.contentDocument.body)) {
        showAlert(t('msg_report_not_ready'), t('title_hint'));
        return;
    }
    
    const btn = e.currentTarget;
    const originalText = btn.innerText;
    btn.innerText = '转换中...';
    btn.disabled = true;

    // 保存折叠状态并全部展开
    const collapsedElements = expandCollapsedElements(reportIframe.contentDocument);
    
    // 给DOM一点时间重新渲染
    await new Promise(resolve => setTimeout(resolve, 300));

    try {
        // 使用 html2canvas 渲染 iframe 内容
        const canvas = await html2canvas(reportIframe.contentDocument.body, {
            useCORS: true,
            allowTaint: true,
            backgroundColor: '#ffffff',
            scale: 2 // 提高清晰度
        });
        
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
        const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
        downloadFile(blob, `Council_Report_${timestamp}.png`);
        
        showAlert('截图导出成功！', t('title_success'));
    } catch (error) {
        console.error('Image conversion error:', error);
        showAlert(t('msg_image_failed'), t('title_error'), 'error');
    } finally {
        // 恢复折叠状态
        restoreCollapsedElements(collapsedElements);
        
        btn.innerText = originalText;
        btn.disabled = false;
    }
}

/**
 * 通用文件下载辅助函数
 * @param {Blob} blob - 文件Blob对象
 * @param {string} filename - 文件名
 * @returns {void}
 */
export function downloadFile(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// 兼容旧版函数名
export const downloadReport = exportAsHTML;
export const downloadMarkdown = exportAsMarkdown;
export const downloadPDF = exportAsPDF;
export const downloadImage = exportAsScreenshot;

// 导出所有函数作为命名空间
export default {
    initExportModule,
    toggleDownloadDropdown,
    exportAsHTML,
    exportAsMarkdown,
    exportAsPDF,
    exportAsScreenshot,
    downloadFile,
    openReportInNewTab,
    // 兼容旧版
    downloadReport,
    downloadMarkdown,
    downloadPDF,
    downloadImage
};

/**
 * 在新标签页打开报告（支持编辑）
 */
export function openReportInNewTab() {
    const sessionId = window.State?.currentSessionId;
    if (!sessionId) {
        showAlert('报告尚未生成，无法打开编辑器', '提示');
        return;
    }
    
    const reportUrl = `/report/${sessionId}`;
    window.open(reportUrl, '_blank');
    showAlert('已在新标签页中打开报告（支持编辑功能）', '成功');
}
