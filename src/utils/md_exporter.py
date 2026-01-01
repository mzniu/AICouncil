"""
Markdown导出工具 - 将HTML报告转换为Markdown格式
支持标题、段落、列表、表格、链接、代码块
特殊处理ECharts图表和Mermaid流程图
"""
import re
from typing import Optional
from bs4 import BeautifulSoup, Tag, NavigableString
from src.utils.logger import logger


class MarkdownExporter:
    """HTML到Markdown的转换器"""
    
    def __init__(self):
        self.output = []
        self.in_list = False
        self.list_depth = 0
        
    def html_to_markdown(self, html_content: str) -> str:
        """
        将HTML内容转换为Markdown格式
        
        Args:
            html_content: 完整的HTML字符串
            
        Returns:
            Markdown格式的字符串
        """
        try:
            logger.info("[md_exporter] Starting HTML to Markdown conversion...")
            
            # 解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取body内容（如果存在）
            body = soup.find('body')
            if body:
                content = body
            else:
                content = soup
            
            # 清空输出
            self.output = []
            
            # 递归处理所有元素
            self._process_element(content)
            
            # 合并输出，清理多余空行
            markdown = '\n'.join(self.output)
            markdown = self._clean_output(markdown)
            
            logger.info(f"[md_exporter] Conversion complete, output length: {len(markdown)} chars")
            return markdown
            
        except Exception as e:
            logger.error(f"[md_exporter] Conversion failed: {e}")
            return f"# 导出失败\n\n转换过程中发生错误: {str(e)}"
    
    def _process_element(self, element, parent_tag=None):
        """递归处理HTML元素"""
        if isinstance(element, NavigableString):
            # 处理文本节点
            text = str(element).strip()
            if text and parent_tag not in ['script', 'style']:
                self.output.append(text)
            return
        
        if not isinstance(element, Tag):
            return
        
        tag_name = element.name.lower()
        
        # 跳过script、style、head等标签
        if tag_name in ['script', 'style', 'head', 'meta', 'link']:
            return
        
        # 处理标题
        if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = int(tag_name[1])
            text = self._get_text(element)
            self.output.append(f"\n{'#' * level} {text}\n")
            return
        
        # 处理段落
        if tag_name == 'p':
            text = self._get_text(element)
            if text:
                self.output.append(f"\n{text}\n")
            return
        
        # 处理无序列表
        if tag_name == 'ul':
            self.output.append('')
            for li in element.find_all('li', recursive=False):
                text = self._get_text(li)
                self.output.append(f"- {text}")
            self.output.append('')
            return
        
        # 处理有序列表
        if tag_name == 'ol':
            self.output.append('')
            for idx, li in enumerate(element.find_all('li', recursive=False), 1):
                text = self._get_text(li)
                self.output.append(f"{idx}. {text}")
            self.output.append('')
            return
        
        # 处理表格
        if tag_name == 'table':
            self._process_table(element)
            return
        
        # 处理链接
        if tag_name == 'a':
            text = self._get_text(element)
            href = element.get('href', '')
            if href and text:
                self.output.append(f"[{text}]({href})")
            elif text:
                self.output.append(text)
            return
        
        # 处理粗体
        if tag_name in ['strong', 'b']:
            text = self._get_text(element)
            if text:
                self.output.append(f"**{text}**")
            return
        
        # 处理斜体
        if tag_name in ['em', 'i']:
            text = self._get_text(element)
            if text:
                self.output.append(f"*{text}*")
            return
        
        # 处理行内代码
        if tag_name == 'code' and element.parent.name != 'pre':
            text = self._get_text(element)
            if text:
                self.output.append(f"`{text}`")
            return
        
        # 处理代码块
        if tag_name == 'pre':
            code_element = element.find('code')
            if code_element:
                code_text = code_element.get_text()
                # 检测语言（如果有class属性）
                lang = ''
                if code_element.get('class'):
                    classes = code_element.get('class')
                    for cls in classes:
                        if cls.startswith('language-'):
                            lang = cls.replace('language-', '')
                            break
                self.output.append(f"\n```{lang}")
                self.output.append(code_text.rstrip())
                self.output.append("```\n")
            else:
                text = element.get_text()
                self.output.append(f"\n```")
                self.output.append(text.rstrip())
                self.output.append("```\n")
            return
        
        # 处理Mermaid图表
        if 'mermaid' in element.get('class', []):
            mermaid_code = element.get_text().strip()
            self.output.append("\n```mermaid")
            self.output.append(mermaid_code)
            self.output.append("```\n")
            return
        
        # 处理ECharts图表容器
        if element.get('_echarts_instance_') or 'echarts' in element.get('class', []):
            self._process_echarts(element)
            return
        
        # 处理分割线
        if tag_name == 'hr':
            self.output.append("\n---\n")
            return
        
        # 处理换行
        if tag_name == 'br':
            self.output.append("  ")  # Markdown中的换行
            return
        
        # 处理块引用
        if tag_name == 'blockquote':
            text = self._get_text(element)
            lines = text.split('\n')
            for line in lines:
                if line.strip():
                    self.output.append(f"> {line.strip()}")
            self.output.append('')
            return
        
        # 递归处理子元素
        for child in element.children:
            self._process_element(child, tag_name)
    
    def _get_text(self, element) -> str:
        """获取元素的文本内容，处理特殊元素"""
        if isinstance(element, NavigableString):
            return str(element).strip()
        
        # 处理链接
        if element.name == 'a':
            text = element.get_text().strip()
            href = element.get('href', '')
            if href:
                return f"[{text}]({href})"
            return text
        
        # 处理粗体
        if element.name in ['strong', 'b']:
            return f"**{element.get_text().strip()}**"
        
        # 处理斜体
        if element.name in ['em', 'i']:
            return f"*{element.get_text().strip()}*"
        
        # 处理行内代码
        if element.name == 'code':
            return f"`{element.get_text().strip()}`"
        
        return element.get_text().strip()
    
    def _process_table(self, table: Tag):
        """处理HTML表格，转换为Markdown表格"""
        try:
            self.output.append('')
            
            # 提取表头
            headers = []
            thead = table.find('thead')
            if thead:
                header_row = thead.find('tr')
                if header_row:
                    headers = [self._get_text(th) for th in header_row.find_all(['th', 'td'])]
            
            # 如果没有thead，尝试从第一行提取
            if not headers:
                tbody = table.find('tbody')
                if tbody:
                    first_row = tbody.find('tr')
                else:
                    first_row = table.find('tr')
                
                if first_row:
                    # 检查第一行是否全是th
                    ths = first_row.find_all('th')
                    if ths:
                        headers = [self._get_text(th) for th in ths]
            
            # 提取表格数据
            rows = []
            tbody = table.find('tbody')
            if tbody:
                data_rows = tbody.find_all('tr')
            else:
                data_rows = table.find_all('tr')
                # 如果已经提取了表头，跳过第一行
                if headers and data_rows:
                    data_rows = data_rows[1:]
            
            for tr in data_rows:
                row_data = [self._get_text(td) for td in tr.find_all(['td', 'th'])]
                if row_data:  # 只添加非空行
                    rows.append(row_data)
            
            # 如果没有数据，返回
            if not headers and not rows:
                return
            
            # 如果没有表头，使用第一行作为表头
            if not headers and rows:
                headers = rows[0]
                rows = rows[1:]
            
            # 生成Markdown表格
            if headers:
                # 表头
                self.output.append('| ' + ' | '.join(headers) + ' |')
                # 分隔线
                self.output.append('| ' + ' | '.join(['---'] * len(headers)) + ' |')
            
            # 数据行
            for row in rows:
                # 确保每行的列数与表头一致
                while len(row) < len(headers):
                    row.append('')
                self.output.append('| ' + ' | '.join(row[:len(headers)]) + ' |')
            
            self.output.append('')
            
        except Exception as e:
            logger.warning(f"[md_exporter] Table processing failed: {e}")
            self.output.append("\n> 📊 **表格内容**（转换失败）\n")
    
    def _process_echarts(self, element: Tag):
        """处理ECharts图表，转换为文字描述"""
        try:
            # 尝试从元素中提取图表信息
            chart_id = element.get('id', 'chart')
            
            # 查找包含图表配置的script标签（在父元素或后续兄弟节点中）
            chart_title = "数据可视化图表"
            
            # 尝试从元素属性或周围文本提取标题
            parent = element.parent
            if parent:
                # 查找前一个兄弟节点中的标题
                prev_sibling = element.find_previous_sibling(['h3', 'h4', 'h5'])
                if prev_sibling:
                    chart_title = self._get_text(prev_sibling)
            
            # 添加图表占位符
            self.output.append(f"\n> 📊 **{chart_title}**")
            self.output.append("> ")
            self.output.append("> *注：此处原为ECharts交互图表，Markdown格式无法完整呈现。*")
            self.output.append("> *请查看HTML或PDF版本以获得完整的数据可视化效果。*\n")
            
        except Exception as e:
            logger.warning(f"[md_exporter] ECharts processing failed: {e}")
            self.output.append("\n> 📊 **数据图表**（需查看HTML版本）\n")
    
    def _clean_output(self, markdown: str) -> str:
        """清理输出，移除多余空行"""
        # 移除连续的空行（保留最多2个连续换行）
        markdown = re.sub(r'\n{4,}', '\n\n\n', markdown)
        
        # 移除行首尾空格
        lines = markdown.split('\n')
        lines = [line.rstrip() for line in lines]
        
        # 重新组合
        markdown = '\n'.join(lines)
        
        # 确保文档以单个换行符结尾
        markdown = markdown.strip() + '\n'
        
        return markdown


def export_html_to_markdown(html_content: str) -> str:
    """
    导出HTML到Markdown格式（便捷函数）
    
    Args:
        html_content: HTML字符串
        
    Returns:
        Markdown字符串
    """
    exporter = MarkdownExporter()
    return exporter.html_to_markdown(html_content)


# 测试代码
if __name__ == "__main__":
    # 简单测试
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>测试报告</title>
    </head>
    <body>
        <h1>最终议事报告</h1>
        <p>这是一个<strong>测试</strong>报告，包含<em>多种</em>元素。</p>
        
        <h2>核心目标</h2>
        <ul>
            <li>目标1：实现功能A</li>
            <li>目标2：优化性能B</li>
        </ul>
        
        <h2>实施步骤</h2>
        <ol>
            <li>第一步：准备工作</li>
            <li>第二步：开发实施</li>
            <li>第三步：测试验证</li>
        </ol>
        
        <h2>数据对比</h2>
        <table>
            <thead>
                <tr>
                    <th>方案</th>
                    <th>成本</th>
                    <th>周期</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>方案A</td>
                    <td>低</td>
                    <td>3个月</td>
                </tr>
                <tr>
                    <td>方案B</td>
                    <td>中</td>
                    <td>6个月</td>
                </tr>
            </tbody>
        </table>
        
        <h2>流程图</h2>
        <div class="mermaid">
flowchart TD
    A[开始] --> B{决策}
    B -->|是| C[执行]
    B -->|否| D[终止]
        </div>
        
        <h2>参考资料</h2>
        <p>详见<a href="https://example.com">官方文档</a>。</p>
        
        <hr>
        <p><code>生成时间</code>: 2026-01-01</p>
    </body>
    </html>
    """
    
    result = export_html_to_markdown(test_html)
    print(result)
    print("\n" + "="*50)
    print(f"输出长度: {len(result)} 字符")
