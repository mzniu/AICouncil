"""
AICouncil UI测试报告生成器
生成与主项目风格一致的精美HTML测试报告
"""
import json
import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


class TestReportGenerator:
    """测试报告生成器"""
    
    def __init__(self, output_dir: Path = None):
        """
        初始化报告生成器
        
        Args:
            output_dir: 报告输出目录，默认为 tests/ui/reports
        """
        self.output_dir = output_dir or Path(__file__).parent / "reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 测试数据收集
        self.test_results = []
        self.start_time = None
        self.end_time = None
        self.summary = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "error": 0,
            "duration": 0.0
        }
    
    def add_test_result(self, result: Dict[str, Any]):
        """
        添加单个测试结果
        
        Args:
            result: 测试结果字典，包含以下字段：
                - name: 测试名称
                - status: 测试状态 (passed/failed/skipped/error)
                - duration: 执行时长（秒）
                - message: 错误消息（可选）
                - traceback: 堆栈信息（可选）
                - screenshot: 截图路径（可选）
                - video: 视频路径（可选）
                - markers: 测试标记列表（可选）
        """
        self.test_results.append(result)
        self.summary["total"] += 1
        self.summary[result["status"]] = self.summary.get(result["status"], 0) + 1
        self.summary["duration"] += result.get("duration", 0)
    
    def set_session_info(self, start_time: datetime, end_time: datetime):
        """设置测试会话时间信息"""
        self.start_time = start_time
        self.end_time = end_time
        self.summary["duration"] = (end_time - start_time).total_seconds()
    
    def embed_file(self, file_path: Path) -> str:
        """
        将文件嵌入为 base64 数据 URI
        
        Args:
            file_path: 文件路径
            
        Returns:
            base64 编码的数据 URI
        """
        if not file_path or not file_path.exists():
            return ""
        
        with open(file_path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        
        mime_type = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webm": "video/webm",
            ".mp4": "video/mp4"
        }.get(file_path.suffix.lower(), "application/octet-stream")
        
        return f"data:{mime_type};base64,{data}"
    
    def generate_chart_data(self) -> Dict[str, Any]:
        """生成图表所需的数据"""
        # 状态分布饼图数据
        status_data = []
        status_colors = {
            "passed": "#10b981",
            "failed": "#ef4444",
            "skipped": "#f59e0b",
            "error": "#8b5cf6"
        }
        
        for status in ["passed", "failed", "skipped", "error"]:
            count = self.summary.get(status, 0)
            if count > 0:
                status_data.append({
                    "name": status.capitalize(),
                    "value": count,
                    "itemStyle": {"color": status_colors[status]}
                })
        
        # 测试用例执行时长柱状图数据
        duration_data = []
        for result in self.test_results:
            duration_data.append({
                "name": result["name"].split("::")[-1][:30],  # 简化测试名
                "value": round(result.get("duration", 0), 2),
                "status": result["status"]
            })
        
        # 按时长排序，取前15个
        duration_data.sort(key=lambda x: x["value"], reverse=True)
        duration_data = duration_data[:15]
        
        return {
            "status_distribution": status_data,
            "duration_ranking": duration_data
        }
    
    def generate_html(self) -> str:
        """
        生成完整的 HTML 报告
        
        Returns:
            生成的报告文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.output_dir / f"test_report_{timestamp}.html"
        
        # 处理截图和视频
        for result in self.test_results:
            if "screenshot" in result and result["screenshot"]:
                screenshot_path = Path(result["screenshot"])
                if screenshot_path.exists():
                    result["screenshot_data"] = self.embed_file(screenshot_path)
            
            if "video" in result and result["video"]:
                video_path = Path(result["video"])
                if video_path.exists():
                    result["video_data"] = self.embed_file(video_path)
        
        # 生成图表数据
        chart_data = self.generate_chart_data()
        
        # 加载模板并渲染
        template_path = Path(__file__).parent / "templates" / "report_template.html"
        if not template_path.exists():
            raise FileNotFoundError(f"Report template not found: {template_path}")
        
        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()
        
        # 准备模板变量
        template_vars = {
            "report_title": "AICouncil UI Test Report",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S") if self.start_time else "N/A",
            "end_time": self.end_time.strftime("%Y-%m-%d %H:%M:%S") if self.end_time else "N/A",
            "duration": f"{self.summary['duration']:.2f}s",
            "summary_json": json.dumps(self.summary),
            "test_results_json": json.dumps(self.test_results, ensure_ascii=False),
            "chart_data_json": json.dumps(chart_data, ensure_ascii=False),
            "pass_rate": f"{(self.summary['passed'] / max(self.summary['total'], 1) * 100):.1f}%"
        }
        
        # 简单的模板替换（实际项目中可使用 Jinja2）
        html_content = template
        for key, value in template_vars.items():
            html_content = html_content.replace(f"{{{{ {key} }}}}", str(value))
        
        # 写入文件
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # 同时生成 latest.html 符号链接/副本
        latest_path = self.output_dir / "latest.html"
        with open(latest_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"\n✅ 测试报告已生成: {report_path}")
        print(f"📊 最新报告: {latest_path}")
        
        return str(report_path)
