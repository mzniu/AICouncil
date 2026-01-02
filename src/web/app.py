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

from src.agents.langchain_agents import generate_report_from_workspace, run_full_cycle
from src import config_manager as config
from src.utils import pdf_exporter
from src.utils import md_exporter
from src.utils.path_manager import get_workspace_dir, get_config_path, is_frozen
from src.utils.logger import logger
import logging

# 动态检测Playwright是否可用（支持打包环境）
def check_playwright_available():
    """检查Playwright是否可用"""
    try:
        logger.info("[app] Attempting to import playwright...")
        from playwright.async_api import async_playwright
        logger.info("[app] ✅ Playwright imported successfully")
        
        # 检查环境变量
        if 'PLAYWRIGHT_BROWSERS_PATH' in os.environ:
            logger.info(f"[app] PLAYWRIGHT_BROWSERS_PATH: {os.environ['PLAYWRIGHT_BROWSERS_PATH']}")
        if 'PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH' in os.environ:
            logger.info(f"[app] PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH: {os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH']}")
        
        return True
    except ImportError as e:
        logger.error(f"[app] ❌ Playwright import failed: {e}")
        return False
    except Exception as e:
        logger.error(f"[app] ❌ Unexpected error checking Playwright: {e}")
        return False

PLAYWRIGHT_AVAILABLE = check_playwright_available()
logger.info(f"[app] Playwright available: {PLAYWRIGHT_AVAILABLE}")

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
PRESETS_FILE = os.path.join(ROOT, "council_presets.json")

def load_presets_data():
    if not os.path.exists(PRESETS_FILE):
        return {}
    try:
        with open(PRESETS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_presets_data(data):
    with open(PRESETS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

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
        # 确保参数为整数（前端传递的可能是字符串）
        rounds = int(rounds)
        planners = int(planners)
        auditors = int(auditors)
        
        # 打包环境：直接调用函数（避免启动新的 EXE 实例）
        if is_frozen():
            logger.info("[app] 打包环境：直接调用 run_full_cycle")
            
            # 确定模型名称
            if not model:
                if backend == 'deepseek':
                    model = config.DEEPSEEK_MODEL
                elif backend == 'openrouter':
                    model = config.OPENROUTER_MODEL
                elif backend == 'openai':
                    model = config.OPENAI_MODEL
                else:
                    model = config.MODEL_NAME
            
            # 构建模型配置
            model_cfg = {"type": backend, "model": model}
            if reasoning:
                model_cfg["reasoning"] = reasoning
            
            logger.info(f"[app] 使用模型配置: {model_cfg}, 轮数: {rounds}, 策论家: {planners}, 监察官: {auditors}")
            
            # 直接调用核心函数
            result = run_full_cycle(
                issue, 
                model_config=model_cfg, 
                max_rounds=rounds,
                num_planners=planners,
                num_auditors=auditors,
                agent_configs=agent_configs
            )
            
            logger.info(f"[app] 完成 {rounds} 轮流程")
            
        else:
            # 开发环境：启动子进程（保持原有行为）
            logger.info("[app] 开发环境：启动 demo_runner.py 子进程")
            
            python_exe = sys.executable
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
            
            current_process = subprocess.Popen(
                cmd,
                text=True,
                encoding='utf-8'
            )
            
            current_process.wait()
            
    except Exception as e:
        logger.error(f"[app] 启动后端失败: {e}")
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
    
    workspace_path = get_workspace_dir() / current_session_id
    if not workspace_path.exists():
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
    global is_running, current_session_id, current_config, final_report
    if is_running:
        return jsonify({"status": "error", "message": "讨论正在进行中，请稍后再试"}), 400
    
    if not current_session_id:
        return jsonify({"status": "error", "message": "未找到当前会话 ID"}), 400
    
    # 清空旧报告，确保前端显示加载状态
    final_report = ""
    
    data = request.json or {}
    selected_backend = data.get('backend') or current_config.get('backend', 'deepseek')
    
    workspace_path = get_workspace_dir() / current_session_id
    if not workspace_path.exists():
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
    workspace_root = get_workspace_dir()
    if not workspace_root.exists():
        return jsonify([])
    
    workspaces = []
    for d in workspace_root.iterdir():
        if d.is_dir():
            # 尝试获取议题内容
            issue = "未知议题"
            try:
                # 从 final_session_data.json 或 decomposition.json 获取
                data_path = d / "final_session_data.json"
                if data_path.exists():
                    with open(str(data_path), "r", encoding="utf-8") as f:
                        issue = json.load(f).get("issue", issue)
                else:
                    decomp_path = d / "decomposition.json"
                    if decomp_path.exists():
                        with open(str(decomp_path), "r", encoding="utf-8") as f:
                            issue = json.load(f).get("core_goal", issue)
            except:
                pass
            
            workspaces.append({
                "id": d.name,
                "issue": issue,
                "timestamp": d.name.split('_')[0] if '_' in d.name else ""
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
    
    workspace_path = get_workspace_dir() / session_id
    if not workspace_path.exists():
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
        
        # 如果存在最终报告，添加一个事件以更新进度条到 100%
        if final_report:
            discussion_events.append({
                "type": "final_report",
                "content": "" 
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
    config_path = str(get_config_path())
    
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
                "GOOGLE_API_KEY": config.GOOGLE_API_KEY,
                "GOOGLE_SEARCH_ENGINE_ID": config.GOOGLE_SEARCH_ENGINE_ID,
                "SEARCH_PROVIDER": config.SEARCH_PROVIDER,
                "BROWSER_PATH": getattr(config, 'BROWSER_PATH', '')
            }
        })
    
    if request.method == 'POST':
        new_keys = request.json
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            import re
            def escape_for_quote(s, quote):
                # Escape backslashes and the quote character so the resulting Python string literal is safe
                return s.replace('\\', '\\\\').replace(quote, '\\' + quote)

            for key, value in new_keys.items():
                # Normalize value to string
                if value is None:
                    value = ''
                value = str(value)

                # 匹配如 DEEPSEEK_API_KEY = os.getenv('...', '...') 或 DEEPSEEK_API_KEY = '...'
                # 构造安全的正则，转义 key，修复括号不平衡问题
                pattern = rf"({re.escape(key)}\s*=\s*os\.getenv\([^,]+,\s*['\"])([^'\"]*)(['\"])"
                m = re.search(pattern, content)
                if m:
                    quote = m.group(1)[-1]
                    # Use a callable replacement to avoid backreference/template parsing in replacement string
                    content = re.sub(pattern, lambda mo, v=value, q=quote: mo.group(1) + escape_for_quote(v, q) + mo.group(3), content)
                else:
                    # 如果没匹配到 os.getenv 格式，尝试匹配直接赋值格式 KEY = 'VALUE'
                    pattern_direct = rf"({re.escape(key)}\s*=\s*['\"])([^'\"]*)(['\"])"
                    m2 = re.search(pattern_direct, content)
                    if m2:
                        quote = m2.group(1)[-1]
                        content = re.sub(pattern_direct, lambda mo, v=value, q=quote: mo.group(1) + escape_for_quote(v, q) + mo.group(3), content)
                    else:
                        # 如果文件中不存在该 key，则追加一行（使用单引号），并对 value 做转义
                        esc = escape_for_quote(value, "'")
                        content += f"\n{key} = '{esc}'\n"

                # 同时更新当前运行环境中的配置
                setattr(config, key, value)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return jsonify({"status": "success"})
        except Exception as e:
            traceback.print_exc()
            return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/presets', methods=['GET', 'POST'])
def handle_presets():
    if request.method == 'GET':
        return jsonify({"status": "success", "presets": load_presets_data()})
    
    if request.method == 'POST':
        data = request.json
        name = data.get('name')
        config_data = data.get('config')
        
        if not name or not config_data:
            return jsonify({"status": "error", "message": "名称和配置不能为空"}), 400
            
        presets = load_presets_data()
        presets[name] = config_data
        save_presets_data(presets)
        return jsonify({"status": "success"})

@app.route('/api/presets/<name>', methods=['DELETE'])
def delete_preset(name):
    presets = load_presets_data()
    if name in presets:
        del presets[name]
        save_presets_data(presets)
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "未找到该配置"}), 404

@app.route('/api/delete_workspace/<session_id>', methods=['DELETE'])
def delete_workspace(session_id):
    workspace_path = get_workspace_dir() / session_id
    if not workspace_path.exists():
        return jsonify({"status": "error", "message": "工作区不存在"}), 404
    
    try:
        shutil.rmtree(str(workspace_path))
        return jsonify({"status": "success", "message": "工作区已删除"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"删除失败: {str(e)}"}), 500

@app.route('/api/playwright/status', methods=['GET'])
def playwright_status():
    """检查Playwright安装状态"""
    try:
        from src.utils.pdf_exporter import PLAYWRIGHT_AVAILABLE, PLAYWRIGHT_AUTO_INSTALL
        
        status_info = {
            "installed": PLAYWRIGHT_AVAILABLE,
            "auto_install_supported": PLAYWRIGHT_AUTO_INSTALL
        }
        
        if PLAYWRIGHT_AVAILABLE:
            # 检查浏览器是否已下载
            try:
                from src.utils.playwright_installer import is_playwright_installed
                status_info["browser_installed"] = is_playwright_installed()
            except:
                status_info["browser_installed"] = True  # 假设已安装
        
        return jsonify({"status": "success", "data": status_info})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/playwright/install', methods=['POST'])
def install_playwright():
    """安装Playwright + Chromium"""
    try:
        from src.utils.playwright_installer import install_playwright as do_install
        
        # 在后台线程中安装，实时返回进度
        def install_with_progress():
            messages = []
            
            def callback(msg):
                messages.append(msg)
                # 发送进度到前端（可以通过 WebSocket 或 SSE，这里简化为日志）
                logger.info(f"[playwright_install] {msg}")
            
            success = do_install(callback=callback)
            return success, messages
        
        # 同步执行（简化实现，实际可用异步）
        success, messages = install_with_progress()
        
        if success:
            # 重新加载 Playwright
            global PLAYWRIGHT_AVAILABLE
            try:
                from playwright.async_api import async_playwright
                from src.utils import pdf_exporter
                pdf_exporter.PLAYWRIGHT_AVAILABLE = True
                PLAYWRIGHT_AVAILABLE = True
            except:
                pass
            
            return jsonify({
                "status": "success",
                "message": "Playwright 安装成功！",
                "logs": messages
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Playwright 安装失败",
                "logs": messages
            }), 500
        
    except Exception as e:
        logger.error(f"[playwright_install] 安装失败: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/export_pdf', methods=['POST'])
def export_pdf():
    """使用Playwright导出高质量PDF（保留超链接、避免截断）"""
    # 动态检测Playwright（支持热重载）
    playwright_ok = check_playwright_available()
    
    if not playwright_ok:
        return jsonify({
            "status": "error", 
            "message": "Playwright未安装。请点击【安装Playwright】按钮或运行: pip install playwright && playwright install chromium"
        }), 400
    
    try:
        data = request.json
        html_content = data.get('html')
        filename = data.get('filename', 'report.pdf')
        
        if not html_content:
            return jsonify({"status": "error", "message": "HTML内容不能为空"}), 400
        
        # 生成临时PDF文件
        temp_dir = os.path.join(os.getcwd(), "temp_pdfs")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
        import time
        timestamp = int(time.time() * 1000)
        temp_pdf = os.path.join(temp_dir, f"{timestamp}_{filename}")
        
        # 生成PDF
        success = pdf_exporter.generate_pdf_from_html(html_content, temp_pdf, timeout=60000)
        
        if success and os.path.exists(temp_pdf):
            # 读取PDF文件并返回
            with open(temp_pdf, 'rb') as f:
                pdf_data = f.read()
            
            # 清理临时文件
            try:
                os.remove(temp_pdf)
            except:
                pass
            
            # 返回PDF文件
            from flask import send_file
            import io
            return send_file(
                io.BytesIO(pdf_data),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=filename
            )
        else:
            return jsonify({
                "status": "error", 
                "message": "PDF生成失败，请查看日志"
            }), 500
            
    except Exception as e:
        logger.error(f"[api] PDF export error: {e}")
        traceback.print_exc()
        return jsonify({
            "status": "error", 
            "message": f"导出失败: {str(e)}"
        }), 500

@app.route('/api/pdf_available', methods=['GET'])
def check_pdf_available():
    """检查Playwright PDF导出功能是否可用"""
    return jsonify({
        "available": PLAYWRIGHT_AVAILABLE,
        "message": "Playwright已安装" if PLAYWRIGHT_AVAILABLE else "需要安装Playwright: pip install playwright && playwright install chromium"
    })

@app.route('/api/export_md', methods=['POST'])
def export_md():
    """导出Markdown格式报告"""
    try:
        data = request.json
        html_content = data.get('html')
        filename = data.get('filename', 'report.md')
        
        if not html_content:
            return jsonify({"status": "error", "message": "HTML内容不能为空"}), 400
        
        logger.info("[api] Converting HTML to Markdown...")
        
        # 转换为Markdown
        markdown_content = md_exporter.export_html_to_markdown(html_content)
        
        if not markdown_content:
            return jsonify({
                "status": "error",
                "message": "Markdown转换失败"
            }), 500
        
        logger.info(f"[api] Markdown conversion successful, length: {len(markdown_content)} chars")
        
        # 返回Markdown文件
        from flask import send_file
        import io
        return send_file(
            io.BytesIO(markdown_content.encode('utf-8')),
            mimetype='text/markdown',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"[api] Markdown export error: {e}")
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"导出失败: {str(e)}"
        }), 500

# ==================== 报告查看路由 ====================

@app.route('/report/<workspace_id>')
def view_report(workspace_id):
    """通过Flask服务器查看报告（正确识别workspace_id）"""
    try:
        workspace_path = pathlib.Path(get_workspace_dir()) / workspace_id
        report_path = workspace_path / "report.html"
        
        if not report_path.exists():
            return f"<h1>报告不存在</h1><p>工作区 {workspace_id} 中未找到 report.html</p>", 404
        
        with open(report_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 确保workspace-id元数据存在（防止旧报告缺失）
        if 'name="workspace-id"' not in html_content:
            # 在<head>中注入workspace-id
            if '<head>' in html_content:
                html_content = html_content.replace(
                    '<head>',
                    f'<head>\n    <meta name="workspace-id" content="{workspace_id}">'
                )
                logger.info(f"[view_report] 已动态注入 workspace-id: {workspace_id}")
        
        from flask import Response
        return Response(html_content, mimetype='text/html')
        
    except Exception as e:
        logger.error(f"[view_report] Error: {e}")
        traceback.print_exc()
        return f"<h1>加载失败</h1><p>{str(e)}</p>", 500

# ==================== 报告编辑器 API 端点 ====================

@app.route('/api/report/edit/<workspace_id>', methods=['POST'])
def save_report_edit(workspace_id):
    """保存报告编辑内容并创建版本快照"""
    try:
        data = request.json
        workspace_path = pathlib.Path(get_workspace_dir()) / workspace_id
        
        if not workspace_path.exists():
            return jsonify({"status": "error", "message": "工作区不存在"}), 404
        
        # 创建版本目录
        versions_dir = workspace_path / "versions"
        versions_dir.mkdir(exist_ok=True)
        
        # 读取或初始化元数据
        metadata_path = workspace_path / "report_edits.json"
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        else:
            # 首次编辑，初始化元数据并保存原始报告为v0
            metadata = {"current_version": "v0", "versions": []}
            report_path = workspace_path / "report.html"
            if report_path.exists():
                # 保存原始报告为v0
                v0_path = versions_dir / "v0_original.html"
                shutil.copy(report_path, v0_path)
                metadata["versions"].append({
                    "id": "v0",
                    "timestamp": datetime.fromtimestamp(report_path.stat().st_mtime).isoformat(),
                    "changes_summary": "初始生成的报告（AI生成）",
                    "file_path": str(v0_path.relative_to(workspace_path))
                })
                logger.info(f"[editor] 已将原始报告保存为 v0: {workspace_id}")
        
        # 生成新版本信息
        now = datetime.now()
        timestamp_str = now.strftime('%Y%m%d_%H%M%S')
        timestamp_iso = now.isoformat()
        # 版本号基于已有版本数量（包括v0）
        version_num = len(metadata["versions"]) + 1
        version_id = f"v{version_num}"
        version_path = versions_dir / f"{version_id}_{timestamp_str}.html"
        
        # 保存新版本的HTML到版本目录
        html_content = data.get('html_content', '')
        version_path.write_text(html_content, encoding='utf-8')
        
        # 同时更新当前报告文件（这样打开报告时看到的就是最新版本）
        report_path = workspace_path / "report.html"
        report_path.write_text(html_content, encoding='utf-8')
        
        # 更新元数据
        metadata["current_version"] = version_id
        metadata["versions"].append({
            "id": version_id,
            "timestamp": timestamp_iso,
            "changes_summary": data.get('metadata', {}).get('edit_summary', '用户编辑'),
            "file_path": str(version_path.relative_to(workspace_path))
        })
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"[editor] Report edited and saved: {workspace_id}, version: {version_id}")
        
        return jsonify({
            "status": "success",
            "version": version_id,
            "message": "保存成功"
        })
        
    except Exception as e:
        logger.error(f"[editor] Save report error: {e}")
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"保存失败: {str(e)}"
        }), 500

@app.route('/api/report/draft/<workspace_id>', methods=['POST'])
def save_report_draft(workspace_id):
    """保存报告草稿（自动保存）"""
    try:
        data = request.json
        workspace_path = pathlib.Path(get_workspace_dir()) / workspace_id
        
        if not workspace_path.exists():
            return jsonify({"status": "error", "message": "工作区不存在"}), 404
        
        # 保存草稿
        draft_path = workspace_path / "report_draft.html"
        html_content = data.get('html_content', '')
        draft_path.write_text(html_content, encoding='utf-8')
        
        # 保存草稿元数据
        draft_meta_path = workspace_path / "draft_meta.json"
        draft_meta_path.write_text(json.dumps({
            "last_saved": datetime.now().isoformat(),
            "is_draft": True
        }, ensure_ascii=False, indent=2), encoding='utf-8')
        
        return jsonify({"status": "success", "message": "草稿已保存"})
        
    except Exception as e:
        logger.error(f"[editor] Save draft error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/report/versions/<workspace_id>', methods=['GET'])
def get_report_versions(workspace_id):
    """获取报告版本历史列表"""
    try:
        workspace_path = pathlib.Path(get_workspace_dir()) / workspace_id
        metadata_path = workspace_path / "report_edits.json"
        
        if not metadata_path.exists():
            # 如果没有编辑历史，返回原始报告信息
            report_path = workspace_path / "report.html"
            if report_path.exists():
                file_time = datetime.fromtimestamp(report_path.stat().st_mtime).isoformat()
            else:
                file_time = datetime.now().isoformat()
            
            return jsonify([{
                "id": "v0",
                "timestamp": file_time,
                "changes_summary": "初始生成的报告（AI生成）",
                "file_path": "report.html",
                "is_current": True
            }])
        
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # 获取版本列表（倒序显示，最新的在前）
        versions = metadata.get("versions", [])
        current_version_id = metadata.get("current_version", "v0")
        
        # 标记当前版本
        for v in versions:
            v["is_current"] = (v["id"] == current_version_id)
        
        # 倒序返回（最新版本在最前）
        return jsonify(list(reversed(versions)))
        
    except Exception as e:
        logger.error(f"[editor] Get versions error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/report/version/<workspace_id>/<version_id>', methods=['GET'])
def get_report_version_content(workspace_id, version_id):
    """获取指定版本的报告内容"""
    try:
        workspace_path = pathlib.Path(get_workspace_dir()) / workspace_id
        
        if version_id == "current":
            report_path = workspace_path / "report.html"
        else:
            # 从元数据中查找版本路径
            metadata_path = workspace_path / "report_edits.json"
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            version_info = next((v for v in metadata["versions"] if v["id"] == version_id), None)
            if not version_info:
                return "版本不存在", 404
            
            report_path = workspace_path / version_info["file_path"]
        
        if not report_path.exists():
            return "报告文件不存在", 404
        
        content = report_path.read_text(encoding='utf-8')
        return content, 200, {'Content-Type': 'text/html; charset=utf-8'}
        
    except Exception as e:
        logger.error(f"[editor] Get version content error: {e}")
        return f"获取失败: {str(e)}", 500

@app.route('/api/report/restore/<workspace_id>/<version_id>', methods=['POST'])
def restore_report_version(workspace_id, version_id):
    """恢复到指定版本（作为新的当前版本）"""
    try:
        workspace_path = pathlib.Path(get_workspace_dir()) / workspace_id
        metadata_path = workspace_path / "report_edits.json"
        
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        version_info = next((v for v in metadata["versions"] if v["id"] == version_id), None)
        if not version_info:
            return jsonify({"status": "error", "message": "版本不存在"}), 404
        
        version_path = workspace_path / version_info["file_path"]
        report_path = workspace_path / "report.html"
        
        # 恢复版本到当前报告
        shutil.copy(version_path, report_path)
        
        # 更新当前版本标记
        metadata["current_version"] = version_id
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"[editor] Restored version {version_id} for workspace {workspace_id}")
        
        return jsonify({
            "status": "success",
            "message": f"已恢复到版本 {version_id}"
        })
        
    except Exception as e:
        logger.error(f"[editor] Restore version error: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/report/history/<workspace_id>', methods=['GET'])
def get_report_edit_history(workspace_id):
    """获取报告编辑历史（用于编辑器初始化）"""
    try:
        workspace_path = pathlib.Path(get_workspace_dir()) / workspace_id
        metadata_path = workspace_path / "report_edits.json"
        
        if not metadata_path.exists():
            return jsonify({"status": "success", "history": []})
        
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        return jsonify({
            "status": "success",
            "history": metadata.get("versions", []),
            "current_version": metadata.get("current_version", "initial")
        })
        
    except Exception as e:
        logger.error(f"[editor] Get edit history error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ============================================================

if __name__ == '__main__':
    app.run(port=5000, debug=True)
