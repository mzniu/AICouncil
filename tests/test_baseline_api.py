"""
AICouncil Baseline Test - REST API 级别测试
验证阶段1改动后基本议事流程是否正常运行

测试配置：
- 1轮讨论
- 1个策论家
- 1个监察官
- 使用 deepseek-chat 模型

要求：
1. Flask 应用需要在 http://127.0.0.1:5000 运行
2. 需要配置好 DEEPSEEK_API_KEY

使用方法：
  python tests/test_baseline_api.py
"""

import requests
import time
import json
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.utils.path_manager import get_workspace_dir


class BaselineAPITest:
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url
        self.session_id = None
        self.test_issue = "如何提高团队协作效率"
        
    def log(self, message, level="INFO"):
        """打印日志"""
        timestamp = time.strftime("%H:%M:%S")
        symbols = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "ERROR": "❌",
            "WAIT": "⏳",
            "WARN": "⚠️"
        }
        print(f"[{timestamp}] {symbols.get(level, 'ℹ️')} {message}")
    
    def check_server(self):
        """检查服务器是否运行"""
        self.log("检查 Flask 服务器状态...")
        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=2)
            if response.status_code == 200:
                self.log("服务器运行正常", "SUCCESS")
                return True
        except requests.exceptions.ConnectionError:
            self.log("服务器未运行！请先启动: python src/web/app.py", "ERROR")
            return False
        except Exception as e:
            self.log(f"服务器检查失败: {e}", "ERROR")
            return False
    
    def start_discussion(self):
        """启动讨论"""
        # 检查是否有正在运行的讨论
        try:
            status_resp = requests.get(f"{self.base_url}/api/status", timeout=2)
            if status_resp.status_code == 200:
                status_data = status_resp.json()
                if status_data.get("is_running"):
                    self.log("检测到正在运行的讨论，尝试停止...", "WARN")
                    stop_resp = requests.post(f"{self.base_url}/api/stop", timeout=5)
                    if stop_resp.status_code == 200:
                        self.log("已停止现有讨论", "SUCCESS")
                        time.sleep(2)  # 等待清理
                    else:
                        self.log("停止现有讨论失败，继续尝试启动", "WARN")
        except Exception as e:
            self.log(f"检查现有讨论失败: {e}，继续尝试启动", "WARN")
        
        self.log(f"启动讨论：{self.test_issue}")
        
        payload = {
            "issue": self.test_issue,
            "backend": "deepseek",
            "model": "deepseek-chat",
            "rounds": 1,
            "planners": 1,
            "auditors": 1
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/start",
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    self.log(f"讨论已启动", "SUCCESS")
                    
                    # 尝试从API获取Session ID（多次尝试）
                    for attempt in range(5):
                        time.sleep(1)
                        try:
                            status_resp = requests.get(f"{self.base_url}/api/status", timeout=2)
                            if status_resp.status_code == 200:
                                status_data = status_resp.json()
                                events = status_data.get("discussion_events", [])
                                for event in events:
                                    if event.get("type") == "session_start" and event.get("session_id"):
                                        self.session_id = event.get("session_id")
                                        self.log(f"Session ID: {self.session_id}", "SUCCESS")
                                        return True
                        except:
                            pass
                    
                    self.log("暂未获取到Session ID，将在等待过程中继续尝试", "INFO")
                    return True
                else:
                    self.log(f"启动返回异常状态: {data}", "ERROR")
                    return False
            else:
                self.log(f"启动失败 (HTTP {response.status_code}): {response.text}", "ERROR")
                return False
            
        except Exception as e:
            self.log(f"启动请求失败: {e}", "ERROR")
            return False
    
    def wait_for_completion(self, timeout=600):
        """等待讨论完成（默认10分钟超时）"""
        self.log(f"等待讨论完成（最长 {timeout} 秒，约 {timeout // 60} 分钟）...", "WAIT")
        
        start_time = time.time()
        last_status = None
        session_id_found = False
        check_count = 0
        
        try:
            while time.time() - start_time < timeout:
                try:
                    elapsed = int(time.time() - start_time)
                    progress_pct = int((elapsed / timeout) * 100)
                    check_count += 1
                    
                    response = requests.get(f"{self.base_url}/api/status", timeout=2)
                    if response.status_code == 200:
                        data = response.json()
                        is_running = data.get("is_running", False)
                        current_status = data.get("status", "unknown")
                        events = data.get("discussion_events", [])
                        
                        # 从事件中获取 session_id
                        if not session_id_found and events:
                            for event in events:
                                if event.get("type") == "session_start":
                                    self.session_id = event.get("session_id")
                                    if self.session_id:
                                        self.log(f"Session ID: {self.session_id}", "SUCCESS")
                                        session_id_found = True
                                        break
                        
                        # 打印状态变化（每10次检查也显示一次进度）
                        if current_status != last_status:
                            self.log(f"状态: {current_status} (已运行 {elapsed}s / {timeout}s, {progress_pct}%)")
                            last_status = current_status
                        elif check_count % 15 == 0:  # 每30秒显示一次进度
                            self.log(f"运行中... {elapsed}s / {timeout}s ({progress_pct}%)", "WAIT")
                        
                        # 如果讨论完成
                        if not is_running:
                            if session_id_found:
                                self.log(f"讨论已完成（总耗时 {elapsed}秒）", "SUCCESS")
                                return True
                            else:
                                # 讨论完成但未找到session_id，尝试从workspace目录获取
                                self.log("讨论已结束但未从API获取到Session ID", "WARN")
                                
                                # 再检查一次事件
                                if events:
                                    for event in events:
                                        if "session_id" in event or event.get("type") == "session_start":
                                            self.session_id = event.get("session_id", events[0].get("session_id"))
                                            if self.session_id:
                                                self.log(f"从事件中获取到Session ID: {self.session_id}", "SUCCESS")
                                                return True
                                
                                # 从最新的workspace目录获取
                                self.log("尝试从最新workspace目录获取Session ID...", "INFO")
                                try:
                                    workspace_dir = get_workspace_dir()
                                    if workspace_dir.exists():
                                        # 获取最新的workspace目录
                                        workspaces = sorted(
                                            [d for d in workspace_dir.iterdir() if d.is_dir() and not d.name.startswith('.')],
                                            key=lambda x: x.stat().st_mtime,
                                            reverse=True
                                        )
                                        if workspaces:
                                            latest_workspace = workspaces[0]
                                            self.session_id = latest_workspace.name
                                            self.log(f"从目录名获取到Session ID: {self.session_id}", "SUCCESS")
                                            return True
                                except Exception as e:
                                    self.log(f"从目录获取Session ID失败: {e}", "ERROR")
                                
                                self.log("警告：未能获取Session ID，测试可能失败", "WARN")
                                return True
                    
                    time.sleep(2)  # 每2秒检查一次
                    
                except KeyboardInterrupt:
                    self.log("检测到中断信号，正在安全退出...", "WARN")
                    raise
                except requests.exceptions.RequestException as e:
                    self.log(f"状态检查失败: {e}，2秒后重试...", "ERROR")
                    time.sleep(2)
                except Exception as e:
                    self.log(f"意外错误: {e}，2秒后重试...", "ERROR")
                    time.sleep(2)
            
            self.log(f"超时！讨论未在 {timeout} 秒内完成", "ERROR")
            return False
            
        except KeyboardInterrupt:
            self.log("测试被用户中断", "WARN")
            raise
    
    def verify_results(self):
        """验证结果"""
        self.log("验证讨论结果...")
        
        if not self.session_id:
            self.log("Session ID 不存在", "ERROR")
            return False
        
        # 1. 检查 workspace 目录是否创建
        workspace_path = get_workspace_dir() / self.session_id
        if not workspace_path.exists():
            self.log(f"工作空间目录不存在: {workspace_path}", "ERROR")
            return False
        self.log(f"工作空间目录存在: {workspace_path}", "SUCCESS")
        
        # 2. 检查必要文件
        required_files = [
            "history.json",
            "decomposition.json",
            "round_1_data.json",
            "final_session_data.json"
        ]
        
        missing_files = []
        for filename in required_files:
            file_path = workspace_path / filename
            if not file_path.exists():
                missing_files.append(filename)
            else:
                self.log(f"文件存在: {filename}", "SUCCESS")
        
        if missing_files:
            self.log(f"缺失文件: {', '.join(missing_files)}", "ERROR")
            return False
        
        # 3. 验证 round_1_data.json 内容（history.json存储的是轮次级别数据）
        try:
            with open(workspace_path / "round_1_data.json", "r", encoding="utf-8") as f:
                round_data = json.load(f)
            
            # 检查是否包含必要的结构
            has_plans = "plans" in round_data and len(round_data["plans"]) > 0
            has_audits = "audits" in round_data and len(round_data["audits"]) > 0
            
            if has_plans:
                self.log(f"策论家方案: {len(round_data['plans'])} 个", "SUCCESS")
            else:
                self.log("缺少策论家方案", "ERROR")
                return False
            
            if has_audits:
                self.log(f"监察官评审: {len(round_data['audits'])} 个", "SUCCESS")
            else:
                self.log("缺少监察官评审", "ERROR")
                return False
            
            self.log("轮次数据结构正确", "SUCCESS")
            
        except Exception as e:
            self.log(f"验证 round_1_data.json 失败: {e}", "ERROR")
            return False
        
        # 4. 检查报告文件（report.html应该在workspace目录中）
        try:
            report_path = workspace_path / "report.html"
            if report_path.exists():
                report_content = report_path.read_text(encoding="utf-8")
                if len(report_content) > 100 and "<!DOCTYPE html>" in report_content:
                    self.log(f"报告已生成: report.html ({len(report_content)} 字符)", "SUCCESS")
                    return True
                else:
                    self.log("报告格式异常或内容过短", "ERROR")
                    return False
            else:
                self.log("report.html 文件不存在", "ERROR")
                return False
        except Exception as e:
            self.log(f"验证报告失败: {e}", "ERROR")
            return False
        
        return True
    
    def cleanup(self):
        """清理测试数据（可选）"""
        if self.session_id:
            self.log(f"保留测试数据: {self.session_id}")
            self.log(f"如需删除，请访问 Web UI 或手动删除工作空间目录")
    
    def run(self):
        """运行完整测试"""
        print("=" * 60)
        print("  AICouncil Baseline Test - REST API")
        print("=" * 60)
        print()
        
        # 1. 检查服务器
        if not self.check_server():
            return False
        
        print()
        
        # 2. 启动讨论
        if not self.start_discussion():
            return False
        
        print()
        
        # 3. 等待完成
        if not self.wait_for_completion(timeout=600):
            return False
        
        print()
        
        # 4. 验证结果
        if not self.verify_results():
            return False
        
        print()
        print("=" * 60)
        self.log("🎉 Baseline 测试通过！", "SUCCESS")
        print("=" * 60)
        print()
        
        # 5. 清理
        self.cleanup()
        
        return True


def main():
    """主函数"""
    test = BaselineAPITest()
    
    try:
        success = test.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
