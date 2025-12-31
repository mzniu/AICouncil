#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AICouncil 启动器
用于 PyInstaller 打包后的程序入口，提供友好的启动体验
"""
import os
import sys
import time
import webbrowser
import subprocess
from pathlib import Path

# 添加项目路径到 sys.path
if getattr(sys, 'frozen', False):
    # 打包后的环境
    application_path = Path(sys._MEIPASS)
    base_path = Path(sys.executable).parent
    
    # 设置 Playwright 浏览器路径（打包后）
    playwright_browsers = application_path / "playwright" / "browsers"
    if playwright_browsers.exists():
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(playwright_browsers)
        print(f"✅ Playwright 浏览器路径: {playwright_browsers}")
    
    # 设置 Playwright 驱动路径
    playwright_driver = application_path / "playwright" / "driver"
    if playwright_driver.exists():
        os.environ['PLAYWRIGHT_DRIVER_PATH'] = str(playwright_driver)
else:
    # 开发环境
    application_path = Path(__file__).parent
    base_path = application_path

# 确保能导入项目模块
sys.path.insert(0, str(application_path))


def check_first_run():
    """检查是否首次运行，如需要则执行首次设置"""
    try:
        from src.first_run_setup import is_first_run, setup_first_run, get_config_info
        
        if is_first_run():
            print("=" * 60)
            print("  🏛️ 欢迎使用 AICouncil（AI 元老院）")
            print("=" * 60)
            print()
            print("检测到首次运行，正在初始化配置...")
            print()
            
            success = setup_first_run()
            if success:
                print("✅ 配置初始化成功！")
                config_info = get_config_info()
                print()
                print(f"配置文件位置: {config_info['config_path']}")
                print()
                print("💡 提示：")
                print("   1. 请编辑配置文件填入您的 API 密钥")
                print("   2. 或在 Web 界面右上角「设置」中配置")
                print()
                input("按回车键继续启动...")
            else:
                print("⚠️ 配置初始化失败，将使用默认配置")
                print("   您仍可以在 Web 界面中配置 API 密钥")
                print()
                input("按回车键继续...")
    except Exception as e:
        print(f"⚠️ 首次运行检查失败: {e}")
        print("   程序将正常启动")


def find_free_port(start_port=5000, max_attempts=10):
    """查找可用端口"""
    import socket
    
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    return None


def start_flask_server(port=5000):
    """启动 Flask 服务器"""
    try:
        from src.web import app as flask_app
        from src.utils import logger
        
        # 设置环境变量（禁用 Flask 重载器避免打包后问题）
        os.environ['FLASK_ENV'] = 'production'
        os.environ['FLASK_DEBUG'] = '0'
        
        logger.info(f"[Launcher] Starting Flask server on port {port}...")
        
        # 在独立线程中启动 Flask
        import threading
        
        def run_flask():
            flask_app.app.run(
                host='127.0.0.1',
                port=port,
                debug=False,
                use_reloader=False,
                threaded=True
            )
        
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        
        # 等待服务器启动
        time.sleep(2)
        
        return True
        
    except Exception as e:
        print(f"❌ Flask 服务器启动失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def open_browser(url, delay=1):
    """打开浏览器"""
    time.sleep(delay)
    try:
        webbrowser.open(url)
        print(f"✅ 已在浏览器中打开: {url}")
    except Exception as e:
        print(f"⚠️ 无法自动打开浏览器: {e}")
        print(f"   请手动访问: {url}")


def main():
    """主函数"""
    print()
    print("=" * 60)
    print("  🏛️ AICouncil（AI 元老院）启动中...")
    print("=" * 60)
    print()
    
    # 1. 检查首次运行
    check_first_run()
    
    # 2. 查找可用端口
    port = find_free_port(start_port=5000)
    if not port:
        print("❌ 无法找到可用端口（5000-5009 都被占用）")
        print("   请关闭占用端口的程序后重试")
        input("按回车键退出...")
        sys.exit(1)
    
    if port != 5000:
        print(f"ℹ️ 端口 5000 被占用，使用端口 {port}")
    
    # 3. 启动 Flask 服务器
    print(f"🚀 正在启动服务器（端口 {port}）...")
    if not start_flask_server(port):
        print()
        print("❌ 服务器启动失败")
        print("   请检查日志文件或联系技术支持")
        input("按回车键退出...")
        sys.exit(1)
    
    # 4. 打开浏览器
    url = f"http://127.0.0.1:{port}"
    print()
    print("✅ 服务器启动成功！")
    print(f"📱 访问地址: {url}")
    print()
    print("💡 提示：")
    print("   - 保持此窗口打开以继续运行服务器")
    print("   - 按 Ctrl+C 停止服务器")
    print()
    
    # 延迟打开浏览器（给服务器更多启动时间）
    import threading
    browser_thread = threading.Thread(target=open_browser, args=(url, 1))
    browser_thread.start()
    
    # 5. 保持运行
    try:
        print("=" * 60)
        print()
        
        # 主线程保持运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print()
        print()
        print("=" * 60)
        print("  👋 正在关闭 AICouncil...")
        print("=" * 60)
        print()
        sys.exit(0)


if __name__ == "__main__":
    main()
