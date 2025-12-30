"""
测试Playwright PDF导出功能
运行前确保已安装: pip install playwright && playwright install chromium
"""
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils.pdf_exporter import generate_pdf_from_html, PLAYWRIGHT_AVAILABLE

def test_pdf_export():
    print("="*60)
    print("测试 Playwright PDF 导出功能")
    print("="*60)
    
    # 检查Playwright是否可用
    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright 未安装")
        print("\n安装命令:")
        print("  pip install playwright")
        print("  playwright install chromium")
        return False
    
    print("✅ Playwright 已安装\n")
    
    # 创建测试HTML
    test_html = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AICouncil 测试报告</title>
        <style>
            body {
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                padding: 40px;
                line-height: 1.6;
            }
            h1 {
                color: #2563eb;
                border-bottom: 3px solid #2563eb;
                padding-bottom: 10px;
            }
            h2 {
                color: #0ea5e9;
                margin-top: 30px;
            }
            a {
                color: #0ea5e9;
                text-decoration: none;
            }
            a:hover {
                text-decoration: underline;
            }
            .section {
                background: #f0f9ff;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
            }
            .highlight {
                background: #fef3c7;
                padding: 2px 6px;
                border-radius: 3px;
            }
        </style>
    </head>
    <body>
        <h1>🏛️ AI 元老院测试报告</h1>
        
        <div class="section">
            <h2>1. PDF导出功能测试</h2>
            <p>本文档用于测试基于 <span class="highlight">Playwright</span> 的高质量PDF导出功能。</p>
            <p>主要测试点：</p>
            <ul>
                <li>✅ 中文字体渲染</li>
                <li>✅ 超链接保留（可点击）</li>
                <li>✅ CSS样式完整性</li>
                <li>✅ 分页无内容截断</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>2. 超链接测试</h2>
            <p>以下链接在PDF中应该可以直接点击：</p>
            <ul>
                <li>GitHub项目地址: <a href="https://github.com/mzniu/AICouncil">AICouncil</a></li>
                <li>项目文档: <a href="https://github.com/mzniu/AICouncil/blob/main/README.md">README.md</a></li>
                <li>技术架构: <a href="https://github.com/mzniu/AICouncil/blob/main/docs/architecture.md">架构说明</a></li>
            </ul>
        </div>
        
        <div class="section">
            <h2>3. 样式渲染测试</h2>
            <p>这段文字包含<strong>粗体</strong>、<em>斜体</em>、<span class="highlight">高亮</span>等样式。</p>
            <p style="color: #dc2626;">红色文字测试</p>
            <p style="color: #059669;">绿色文字测试</p>
        </div>
        
        <div class="section">
            <h2>4. 长文本分页测试</h2>
            <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>
            <p>这是一段中文长文本，用于测试PDF分页时是否会出现内容截断。在传统的jsPDF方案中，这类文本可能在页面边界被切断。</p>
            <p>但使用Playwright后端渲染，系统会智能处理分页，确保内容完整。</p>
        </div>
        
        <hr style="margin: 40px 0; border: 1px solid #e5e7eb;">
        
        <footer style="text-align: center; color: #6b7280; font-size: 14px;">
            <p>本报告由 AI 元老院系统生成</p>
            <p>生成时间: 2025-12-30 | 技术栈: Python + Flask + Playwright</p>
        </footer>
    </body>
    </html>
    """
    
    # 生成PDF
    output_path = "test_playwright_export.pdf"
    print(f"正在生成PDF: {output_path}")
    print("请稍候...\n")
    
    try:
        success = generate_pdf_from_html(test_html, output_path, timeout=30000)
        
        if success:
            print("✅ PDF生成成功!")
            print(f"\n文件位置: {pathlib.Path(output_path).absolute()}")
            print("\n请打开PDF文件检查:")
            print("  1. 所有超链接是否可以点击")
            print("  2. 中文是否正常显示")
            print("  3. 样式是否完整保留")
            print("  4. 内容是否有截断")
            return True
        else:
            print("❌ PDF生成失败，请查看日志")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_pdf_export()
