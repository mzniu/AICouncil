from flask import Flask, render_template, request, jsonify
import json
import subprocess
import threading
import sys
import os
import traceback
import atexit
import signal
import pathlib
import shutil
from datetime import datetime

# 确保项目根目录在 sys.path 中，以便能够导入 src 模块
ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agents.langchain_agents import generate_report_from_workspace
from src import config
import logging

# 禁用 Werkzeug 默认的访问日志（减少 /api/update 等高频请求的输出）
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

# 存储讨论过程的全局变量
discussion_events = []
backend_logs = []
final_report = ""
is_running = False
current_process = None
current_config = {}
current_session_id = None

def cleanup():
    global current_process
    if current_process:
        print("正在关闭后台议事进程...")
        try:
            # Windows 下使用 taskkill 确保杀掉整个进程树
            if os.name == 'nt':
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(current_process.pid)], capture_output=True)
            else:
                current_process.terminate()
        except Exception as e:
            print(f"关闭进程失败: {e}")

atexit.register(cleanup)

# 处理信号以确保清理
def signal_handler(sig, frame):
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/start', methods=['POST'])
def start_discussion():
    global is_running, discussion_events, backend_logs, final_report, current_config
    if is_running:
        return jsonify({"status": "error", "message": "讨论正在进行中"}), 400
    
    # 清空旧数据，确保新讨论从零开始
    discussion_events = []
    backend_logs = []
    final_report = ""
    
    data = request.json
    issue = data.get('issue')
    backend = data.get('backend', 'deepseek')
    model = data.get('model') # 获取全局模型覆盖
    reasoning = data.get('reasoning') # 获取推理配置
    rounds = data.get('rounds', 3)
    planners = data.get('planners', 2)
    auditors = data.get('auditors', 2)
    agent_configs = data.get('agent_configs') # 获取 agent_configs

    if not issue:
        return jsonify({"status": "error", "message": "议题不能为空"}), 400

    current_config = {
        "issue": issue,
        "backend": backend,
        "model": model,
        "reasoning": reasoning,
        "rounds": rounds,
        "planners": planners,
        "auditors": auditors,
        "agent_configs": agent_configs
    }

    is_running = True
    # 在后台线程启动 demo_runner.py，设置为 daemon 确保主进程退出时线程也退出
    thread = threading.Thread(target=run_backend, args=(issue, backend, model, rounds, planners, auditors, agent_configs, reasoning))
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "ok"})

def run_backend(issue, backend, model, rounds, planners, auditors, agent_configs=None, reasoning=None):
    global is_running, current_process
    try:
        # 获取当前 python 解释器路径
        python_exe = sys.executable
        # 构造命令
        cmd = [
            python_exe, 
            "src/agents/demo_runner.py", 
            "--issue", issue, 
            "--backend", backend, 
            "--rounds", str(rounds),
            "--planners", str(planners),
            "--auditors", str(auditors)
        ]
        
        if model:
            cmd.extend(["--model", model])
        
        if reasoning:
            cmd.extend(["--reasoning", json.dumps(reasoning)])
        
        if agent_configs:
            cmd.extend(["--agent_configs", json.dumps(agent_configs)])
        
        # 运行子进程，不捕获 stdout 以免缓冲区满导致挂起
        # 所有的日志和事件都通过 API 异步发送回 Flask
        current_process = subprocess.Popen(
            cmd,
            text=True,
            encoding='utf-8'
        )
        
        # 等待进程结束
        current_process.wait()
    except Exception as e:
        print(f"启动后端失败: {e}")
        traceback.print_exc()
    finally:
        is_running = False
        current_process = None

@app.route('/api/stop', methods=['POST'])
def stop_discussion():
    global current_process, is_running
    if current_process:
        try:
            cleanup()
            is_running = False
            return jsonify({"status": "ok", "message": "已强制停止后台进程"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "error", "message": "没有正在运行的讨论"}), 400

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        "is_running": is_running,
        "config": current_config,
        "browser_found": bool(config.BROWSER_PATH and os.path.exists(config.BROWSER_PATH))
    })

@app.route('/api/events', methods=['GET'])
def get_events():
    return jsonify({
        "events": discussion_events,
        "logs": backend_logs,
        "final_report": final_report
    })

@app.route('/api/update', methods=['POST'])
def update_event():
    global final_report, current_session_id
    data = request.json
    etype = data.get('type')
    chunk_id = data.get('chunk_id')
    
    if etype == 'system_start':
        current_session_id = data.get('session_id')
    
    if etype == 'final_report':
        final_report = data.get('content')
    elif etype == 'log':
        backend_logs.append(data.get('content'))
        # 移除硬编码的 200 条限制，允许记录完整的议事日志
        # 只有在极端情况下（超过 5000 条）才进行清理
        if len(backend_logs) > 5000:
            backend_logs.pop(0)
    else:
        discussion_events.append(data)
    return jsonify({"status": "ok"})

@app.route('/api/intervene', methods=['POST'])
def intervene():
    global current_session_id
    if not current_session_id:
        return jsonify({"status": "error", "message": "没有正在进行的讨论"}), 400
    
    data = request.json
    content = data.get('content')
    if not content:
        return jsonify({"status": "error", "message": "干预内容不能为空"}), 400
    
    workspace_path = os.path.join(os.getcwd(), "workspaces", current_session_id)
    if not os.path.exists(workspace_path):
        return jsonify({"status": "error", "message": "工作区不存在"}), 400
    
    intervention_file = os.path.join(workspace_path, "user_intervention.json")
    
    # 如果已经存在干预，则追加
    existing_content = ""
    if os.path.exists(intervention_file):
        try:
            with open(intervention_file, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                existing_content = existing_data.get("content", "") + "\n"
        except:
            pass
            
    with open(intervention_file, "w", encoding="utf-8") as f:
        json.dump({"content": existing_content + content}, f, ensure_ascii=False, indent=4)
    
    # 同时作为一个事件记录到讨论流中，方便前端展示
    intervention_event = {
        "type": "user_intervention",
        "content": content,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    discussion_events.append(intervention_event)
    
    return jsonify({"status": "ok"})

@app.route('/api/rereport', methods=['POST'])
def rereport():
    global is_running, current_session_id, current_config
    if is_running:
        return jsonify({"status": "error", "message": "讨论正在进行中，请稍后再试"}), 400
    
    if not current_session_id:
        return jsonify({"status": "error", "message": "未找到当前会话 ID"}), 400
    
    data = request.json or {}
    selected_backend = data.get('backend') or current_config.get('backend', 'deepseek')
    
    workspace_path = os.path.join(os.getcwd(), "workspaces", current_session_id)
    if not os.path.exists(workspace_path):
        return jsonify({"status": "error", "message": f"工作区不存在: {current_session_id}"}), 404

    # 在后台线程运行，避免阻塞
    def run_rereport():
        global is_running
        is_running = True
        try:
            # 根据选择的后端确定模型
            if selected_backend == 'deepseek':
                model_name = config.DEEPSEEK_MODEL
            elif selected_backend == 'openrouter':
                model_name = config.OPENROUTER_MODEL
            elif selected_backend == 'openai':
                model_name = config.OPENAI_MODEL
            elif selected_backend == 'aliyun':
                model_name = config.ALIYUN_MODEL
            else:
                model_name = config.MODEL_NAME

            model_cfg = {
                "type": selected_backend,
                "model": model_name
            }
            generate_report_from_workspace(workspace_path, model_cfg)
        except Exception as e:
            print(f"重新生成报告失败: {e}")
            traceback.print_exc()
        finally:
            is_running = False

    thread = threading.Thread(target=run_rereport)
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "ok"})

@app.route('/api/workspaces', methods=['GET'])
def list_workspaces():
    workspace_root = os.path.join(os.getcwd(), "workspaces")
    if not os.path.exists(workspace_root):
        return jsonify([])
    
    workspaces = []
    for d in os.listdir(workspace_root):
        path = os.path.join(workspace_root, d)
        if os.path.isdir(path):
            # 尝试获取议题内容
            issue = "未知议题"
            try:
                # 从 final_session_data.json 或 decomposition.json 获取
                data_path = os.path.join(path, "final_session_data.json")
                if os.path.exists(data_path):
                    with open(data_path, "r", encoding="utf-8") as f:
                        issue = json.load(f).get("issue", issue)
                else:
                    decomp_path = os.path.join(path, "decomposition.json")
                    if os.path.exists(decomp_path):
                        with open(decomp_path, "r", encoding="utf-8") as f:
                            issue = json.load(f).get("core_goal", issue)
            except:
                pass
            
            workspaces.append({
                "id": d,
                "issue": issue,
                "timestamp": d.split('_')[0] if '_' in d else ""
            })
    
    # 按时间倒序排列
    workspaces.sort(key=lambda x: x['id'], reverse=True)
    return jsonify({
        "status": "success",
        "workspaces": workspaces
    })

@app.route('/api/load_workspace/<session_id>', methods=['GET'])
def load_workspace(session_id):
    global discussion_events, backend_logs, final_report, current_session_id, current_config
    
    workspace_path = os.path.join(os.getcwd(), "workspaces", session_id)
    if not os.path.exists(workspace_path):
        return jsonify({"status": "error", "message": "工作区不存在"}), 404
    
    try:
        # 重置当前状态
        discussion_events = []
        backend_logs = []
        final_report = ""
        current_session_id = session_id
        
        # 1. 加载最终报告
        report_path = os.path.join(workspace_path, "report.html")
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                final_report = f.read()
        
        # 2. 加载历史记录并重建事件流
        history_path = os.path.join(workspace_path, "history.json")
        final_data_path = os.path.join(workspace_path, "final_session_data.json")
        
        issue_text = "已加载的议题"
        max_rounds = 3
        if os.path.exists(final_data_path):
            with open(final_data_path, "r", encoding="utf-8") as f:
                fd = json.load(f)
                issue_text = fd.get("issue", issue_text)
                # 尝试从 history 长度获取轮数
                history_data = fd.get("history", [])
                if history_data:
                    max_rounds = len(history_data)
                current_config = {"issue": issue_text, "rounds": max_rounds}
        
        # 添加系统启动事件
        discussion_events.append({
            "type": "system_start",
            "issue": issue_text,
            "session_id": session_id
        })
        
        if os.path.exists(history_path):
            with open(history_path, "r", encoding="utf-8") as f:
                history = json.load(f)
                if not history_data: # 如果 final_data 没拿到，从 history.json 拿
                    max_rounds = len(history)
                for h in history:
                    round_num = h.get("round")
                    discussion_events.append({"type": "round_start", "round": round_num})
                    
                    # 为每个 Planner 和 Auditor 创建一个合成的 agent_action 事件
                    for i, p in enumerate(h.get("plans", []), 1):
                        discussion_events.append({
                            "type": "agent_action",
                            "agent_name": f"策论家 {i}",
                            "role_type": "Planner",
                            "content": json.dumps(p, ensure_ascii=False),
                            "chunk_id": f"load_{session_id}_r{round_num}_p{i}"
                        })
                    
                    for j, a in enumerate(h.get("audits", []), 1):
                        discussion_events.append({
                            "type": "agent_action",
                            "agent_name": f"监察官 {j}",
                            "role_type": "Auditor",
                            "content": json.dumps(a, ensure_ascii=False),
                            "chunk_id": f"load_{session_id}_r{round_num}_a{j}"
                        })
                    
                    if h.get("summary"):
                        discussion_events.append({
                            "type": "agent_action",
                            "agent_name": "议长",
                            "role_type": "Leader",
                            "content": json.dumps(h["summary"], ensure_ascii=False),
                            "chunk_id": f"load_{session_id}_r{round_num}_l"
                        })
        
        backend_logs.append(f"成功从工作区加载会话: {session_id}")
        return jsonify({
            "status": "success", 
            "issue": issue_text,
            "rounds": max_rounds
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/reset', methods=['POST'])
def reset():
    global discussion_events, final_report, backend_logs, current_config
    discussion_events = []
    backend_logs = []
    final_report = ""
    current_config = {}
    return jsonify({"status": "success"})

@app.route('/api/openrouter/models', methods=['GET'])
def openrouter_models():
    from src.agents.model_adapter import get_openrouter_models
    return jsonify(get_openrouter_models())


@app.route('/api/deepseek/models', methods=['GET'])
def deepseek_models():
    from src.agents.model_adapter import get_deepseek_models
    return jsonify(get_deepseek_models())


@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    config_path = os.path.join(os.getcwd(), "src", "config.py")
    
    if request.method == 'GET':
        # 返回当前配置中的 Key (脱敏处理或直接返回，本地工具通常直接返回)
        return jsonify({
            "status": "success",
            "config": {
                "DEEPSEEK_API_KEY": config.DEEPSEEK_API_KEY,
                "OPENAI_API_KEY": config.OPENAI_API_KEY,
                "OPENROUTER_API_KEY": config.OPENROUTER_API_KEY,
                "ALIYUN_API_KEY": config.ALIYUN_API_KEY,
                "TAVILY_API_KEY": config.TAVILY_API_KEY,
                "SEARCH_PROVIDER": config.SEARCH_PROVIDER,
                "BROWSER_PATH": getattr(config, 'BROWSER_PATH', '')
            }
        })
    
    if request.method == 'POST':
        new_keys = request.json
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 替换文件中的 Key 定义
            import re
            for key, value in new_keys.items():
                # 匹配如 DEEPSEEK_API_KEY = os.getenv('...', '...') 或 DEEPSEEK_API_KEY = '...'
                # 这里的正则比较简单，假设格式是 KEY = os.getenv(..., 'VALUE')
                pattern = rf"({key}\s*=\s*os\.getenv\([^,]+,\s*['\"])([^'\"]*)(['\"]\))"
                if re.search(pattern, content):
                    content = re.sub(pattern, rf"\1{value}\3", content)
                else:
                    # 如果没匹配到 os.getenv 格式，尝试匹配直接赋值格式 KEY = 'VALUE'
                    pattern_direct = rf"({key}\s*=\s*['\"])([^'\"]*)(['\"])"
                    content = re.sub(pattern_direct, rf"\1{value}\3", content)
                
                # 同时更新当前运行环境中的配置
                setattr(config, key, value)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return jsonify({"status": "success"})
        except Exception as e:
            traceback.print_exc()
            return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/delete_workspace/<session_id>', methods=['DELETE'])
def delete_workspace(session_id):
    workspace_path = os.path.join(os.getcwd(), "workspaces", session_id)
    if not os.path.exists(workspace_path):
        return jsonify({"status": "error", "message": "工作区不存在"}), 404
    
    try:
        shutil.rmtree(workspace_path)
        return jsonify({"status": "success", "message": "工作区已删除"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"删除失败: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
