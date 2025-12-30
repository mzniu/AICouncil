"""
PDF导出工具 - 使用Playwright实现高质量PDF生成
支持超链接、避免内容截断、完整保留页面样式
"""
import os
import asyncio
import pathlib
import re
from typing import Optional
from src.utils import logger

# 延迟导入 Playwright，如果没安装则退回到旧方案
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
    logger.info("[pdf_exporter] Playwright available, using high-quality PDF export")
except ImportError:
    logger.warning("[pdf_exporter] Playwright not installed, PDF export will use legacy method")


def _inline_echarts_script(html_content: str) -> str:
    """
    将ECharts CDN链接替换为本地内嵌脚本，确保离线PDF中图表能正常渲染
    """
    try:
        # 查找ECharts的<script>标签
        echarts_pattern = r'<script[^>]*src=["\']([^"\']*echarts[^"\']*(\.min)?\.js)["\'][^>]*></script>'
        
        # 检查是否有ECharts引用
        if not re.search(echarts_pattern, html_content, re.IGNORECASE):
            logger.info("[pdf_exporter] No ECharts script found, skipping inline replacement")
            return html_content
        
        # 尝试读取本地ECharts文件
        echarts_local_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'src', 'web', 'static', 'vendor', 'echarts.min.js'
        )
        
        if os.path.exists(echarts_local_path):
            logger.info(f"[pdf_exporter] Reading local ECharts from: {echarts_local_path}")
            with open(echarts_local_path, 'r', encoding='utf-8') as f:
                echarts_code = f.read()
            
            # 替换为内嵌脚本
            inline_script = f'<script>/* ECharts Inline */\n{echarts_code}\n</script>'
            html_content = re.sub(echarts_pattern, inline_script, html_content, flags=re.IGNORECASE)
            logger.info("[pdf_exporter] ECharts script inlined successfully")
        else:
            logger.warning(f"[pdf_exporter] Local ECharts file not found: {echarts_local_path}")
            # 如果本地文件不存在，至少尝试使用可靠的CDN
            html_content = re.sub(
                echarts_pattern,
                '<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>',
                html_content,
                flags=re.IGNORECASE
            )
            logger.info("[pdf_exporter] Replaced with stable CDN link")
        
        return html_content
        
    except Exception as e:
        logger.error(f"[pdf_exporter] Error inlining ECharts: {e}")
        return html_content


async def _generate_pdf_with_playwright(html_content: str, output_path: str, timeout: int = 60000) -> bool:
    """使用Playwright生成高质量PDF（保留超链接、避免截断）"""
    try:
        # 预处理：内嵌ECharts脚本
        html_content = _inline_echarts_script(html_content)
        
        async with async_playwright() as p:
            # 优先使用Chromium（更轻量），回退到Chrome
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                device_scale_factor=2  # 提高清晰度
            )
            
            page = await context.new_page()
            
            # 注入CSS确保图表容器不被分页截断
            await page.add_style_tag(content="""
                [_echarts_instance_], 
                .chart-container, 
                .module-card:has([_echarts_instance_]) {
                    page-break-inside: avoid !important;
                    break-inside: avoid !important;
                    margin-bottom: 30px !important;
                }
                
                /* 确保图表有足够的空间 */
                [_echarts_instance_] {
                    min-height: 400px !important;
                    margin: 20px 0 !important;
                }
            """)
            
            # 设置内容并等待渲染完成
            await page.set_content(html_content, wait_until='networkidle', timeout=timeout)
            
            # 等待ECharts加载
            try:
                await page.wait_for_function(
                    "typeof echarts !== 'undefined'",
                    timeout=10000
                )
                logger.info("[pdf_exporter] ECharts library loaded")
            except:
                logger.warning("[pdf_exporter] ECharts library not found, charts may not render")
            
            # 等待所有ECharts实例渲染完成
            try:
                # 先检查是否有echarts实例
                has_echarts = await page.evaluate("""
                    () => {
                        const instances = document.querySelectorAll('[_echarts_instance_]');
                        return instances.length > 0;
                    }
                """)
                
                if has_echarts:
                    logger.info("[pdf_exporter] Found ECharts instances, waiting for rendering...")
                    
                    # 等待所有实例完成渲染（最多等待15秒）
                    await page.wait_for_function(
                        """
                        () => {
                            if (typeof echarts === 'undefined') return true;
                            
                            const instances = document.querySelectorAll('[_echarts_instance_]');
                            if (instances.length === 0) return true;
                            
                            // 检查每个实例是否已渲染
                            for (let elem of instances) {
                                const instance = echarts.getInstanceByDom(elem);
                                if (!instance) continue;
                                
                                // 检查是否有canvas或svg内容
                                const canvas = elem.querySelector('canvas');
                                const svg = elem.querySelector('svg');
                                if (!canvas && !svg) return false;
                            }
                            
                            return true;
                        }
                        """,
                        timeout=15000
                    )
                    logger.info("[pdf_exporter] All ECharts instances rendered successfully")
                    
                    # 强制所有图表resize以确保尺寸正确
                    await page.evaluate("""
                        () => {
                            if (typeof echarts === 'undefined') return;
                            
                            const instances = document.querySelectorAll('[_echarts_instance_]');
                            instances.forEach(elem => {
                                const instance = echarts.getInstanceByDom(elem);
                                if (instance) {
                                    // 强制resize确保尺寸正确
                                    instance.resize();
                                    
                                    // 设置容器CSS确保不被分页截断
                                    elem.style.pageBreakInside = 'avoid';
                                    elem.style.breakInside = 'avoid';
                                    
                                    // 确保父容器也有正确的样式
                                    if (elem.parentElement) {
                                        elem.parentElement.style.pageBreakInside = 'avoid';
                                        elem.parentElement.style.breakInside = 'avoid';
                                    }
                                }
                            });
                            
                            console.log('✅ ECharts instances resized and styled for PDF export');
                        }
                    """)
                    logger.info("[pdf_exporter] Forced resize on all ECharts instances")
                    
                    # 等待resize后的布局稳定
                    await page.wait_for_timeout(2000)
                else:
                    logger.info("[pdf_exporter] No ECharts instances found")
            except Exception as e:
                logger.warning(f"[pdf_exporter] ECharts rendering check failed: {e}, proceeding anyway")
            
            # 额外等待确保DOM完全稳定
            await page.wait_for_timeout(1000)
            
            # 生成PDF配置
            pdf_options = {
                'path': output_path,
                'format': 'A4',
                'print_background': True,  # 打印背景色和图片
                'prefer_css_page_size': False,
                'margin': {
                    'top': '20px',
                    'right': '20px',
                    'bottom': '20px',
                    'left': '20px'
                },
                'display_header_footer': False,
            }
            
            await page.pdf(**pdf_options)
            await browser.close()
            
            logger.info(f"[pdf_exporter] PDF generated successfully: {output_path}")
            return True
            
    except Exception as e:
        logger.error(f"[pdf_exporter] Playwright PDF generation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def generate_pdf_from_html(html_content: str, output_path: str, timeout: int = 60000) -> bool:
    """
    从HTML内容生成PDF文件
    
    Args:
        html_content: HTML源码
        output_path: 输出PDF文件路径
        timeout: 超时时间（毫秒）
        
    Returns:
        bool: 是否生成成功
    """
    if not PLAYWRIGHT_AVAILABLE:
        logger.error("[pdf_exporter] Playwright not available, cannot generate PDF")
        return False
    
    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 运行异步生成
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            _generate_pdf_with_playwright(html_content, output_path, timeout)
        )
        loop.close()
        
        return result
        
    except Exception as e:
        logger.error(f"[pdf_exporter] PDF generation error: {e}")
        return False


def generate_pdf_from_file(html_file_path: str, output_path: Optional[str] = None, timeout: int = 60000) -> bool:
    """
    从HTML文件生成PDF
    
    Args:
        html_file_path: HTML文件路径
        output_path: 输出PDF路径（默认为同目录同名.pdf）
        timeout: 超时时间（毫秒）
        
    Returns:
        bool: 是否生成成功
    """
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        if output_path is None:
            output_path = str(pathlib.Path(html_file_path).with_suffix('.pdf'))
        
        return generate_pdf_from_html(html_content, output_path, timeout)
        
    except Exception as e:
        logger.error(f"[pdf_exporter] Error reading HTML file: {e}")
        return False


if __name__ == "__main__":
    # 测试代码
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Test Report</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            h1 { color: #2563eb; }
            a { color: #0ea5e9; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <h1>测试报告</h1>
        <p>这是一个测试报告，包含<a href="https://example.com">可点击的超链接</a>。</p>
        <p>Playwright生成的PDF将保留所有超链接和样式。</p>
    </body>
    </html>
    """
    
    result = generate_pdf_from_html(test_html, "test_report.pdf")
    print(f"PDF generation {'succeeded' if result else 'failed'}")
