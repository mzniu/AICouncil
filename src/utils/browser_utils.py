import os
import platform
import shutil

def find_browser_path():
    """
    尝试自动寻找系统中安装的浏览器可执行文件路径。
    优先级：Chrome > Edge > Brave > Chromium
    """
    system = platform.system()
    if system == "Windows":
        paths = [
            # Chrome
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            # Edge
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            # Brave
            os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            os.path.expandvars(r"%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ]
        for path in paths:
            if os.path.exists(path):
                return path
                
    elif system == "Linux":
        executables = [
            "google-chrome",
            "google-chrome-stable",
            "microsoft-edge",
            "microsoft-edge-stable",
            "brave-browser",
            "chromium",
            "chromium-browser"
        ]
        for exe in executables:
            path = shutil.which(exe)
            if path:
                return path
                
    elif system == "Darwin":  # macOS
        paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        ]
        for path in paths:
            if os.path.exists(path):
                return path
                
    # 最后尝试使用 shutil.which 寻找通用的 chrome/chromium
    for exe in ["chrome", "chromium", "msedge"]:
        path = shutil.which(exe)
        if path:
            return path
            
    return None
