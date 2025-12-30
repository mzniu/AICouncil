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
            "WAIT": "⏳"
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
                    # Session ID 会通过事件流发送，等待获取
                    time.sleep(3)  # 给后端一点时间初始化
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
        self.log(f"等待讨论完成（最长 {timeout} 秒）...", "WAIT")
        
        start_time = time.time()
        last_status = None
        session_id_found = False
        
        while time.time() - start_time < timeout:
            try:
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
                    
                    # 打印状态变化
                    if current_status != last_status:
                        self.log(f"状态: {current_status}")
                        last_status = current_status
                    
                    # 如果讨论完成
                    if not is_running:
                        if session_id_found:
                            self.log("讨论已完成", "SUCCESS")
                            return True
                        else:
                            # 讨论完成但未找到session_id，可能是立即完成或出错
                            self.log("讨论已结束但未获取到Session ID，检查事件...", "WARN")
                            # 再尝试一次获取
                            if events:
                                for event in events:
                                    if "session_id" in event or event.get("type") == "session_start":
                                        self.session_id = event.get("session_id", events[0].get("session_id"))
                                        if self.session_id:
                                            self.log(f"从事件中获取到Session ID: {self.session_id}", "SUCCESS")
                                            return True
                            self.log("警告：未能获取Session ID，但讨论已完成", "WARN")
                            return True
                
                time.sleep(2)  # 每2秒检查一次
                
            except Exception as e:
                self.log(f"状态检查失败: {e}", "ERROR")
                time.sleep(2)
        
        self.log(f"超时！讨论未在 {timeout} 秒内完成", "ERROR")
        return False
    
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
        
        # 3. 验证 history.json 内容
        try:
            with open(workspace_path / "history.json", "r", encoding="utf-8") as f:
                history = json.load(f)
            
            if not isinstance(history, list):
                self.log("history.json 格式错误（应为列表）", "ERROR")
                return False
            
            self.log(f"历史记录包含 {len(history)} 条事件", "SUCCESS")
            
            # 检查关键角色是否出现
            roles = set(event.get("role") for event in history if "role" in event)
            expected_roles = {"leader", "planner", "auditor", "reporter"}
            missing_roles = expected_roles - roles
            
            if missing_roles:
                self.log(f"缺失角色: {', '.join(missing_roles)}", "ERROR")
                return False
            
            self.log(f"所有角色都已出现: {', '.join(roles)}", "SUCCESS")
            
        except Exception as e:
            self.log(f"验证 history.json 失败: {e}", "ERROR")
            return False
        
        # 4. 检查报告生成
        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=2)
            if response.status_code == 200:
                data = response.json()
                report = data.get("report", "")
                
                if len(report) > 100:  # 报告应该有一定长度
                    self.log(f"报告已生成（长度: {len(report)} 字符）", "SUCCESS")
                    
                    # 检查报告是否包含关键元素
                    if "ECharts" in report or "<!DOCTYPE html>" in report:
                        self.log("报告格式正确（包含 HTML）", "SUCCESS")
                        return True
                    else:
                        self.log("报告格式异常（非 HTML）", "ERROR")
                        return False
                else:
                    self.log("报告内容过短或为空", "ERROR")
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
        if not self.wait_for_completion(timeout=300):
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
