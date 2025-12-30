@echo off
REM AICouncil Baseline Test 运行脚本
REM 自动启动 Flask 服务器并运行测试

echo ========================================
echo   AICouncil Baseline Test Runner
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 未安装或未在 PATH 中
    pause
    exit /b 1
)

REM 检查 Flask 服务器是否已运行
echo [1/3] 检查 Flask 服务器...
curl -s http://127.0.0.1:5000/api/status >nul 2>&1
if errorlevel 1 (
    echo [WARN] Flask 服务器未运行
    echo [INFO] 正在启动 Flask 服务器...
    start "AICouncil Flask Server" cmd /k "python src\web\app.py"
    
    REM 等待服务器启动
    timeout /t 5 /nobreak >nul
    echo.
) else (
    echo [OK] Flask 服务器已运行
    echo.
)

REM 运行测试
echo [2/3] 运行 Baseline 测试...
echo.
python tests\test_baseline_api.py
set TEST_RESULT=%errorlevel%

echo.
echo [3/3] 测试完成
echo.

if %TEST_RESULT% equ 0 (
    echo ========================================
    echo   测试结果: 通过 ^(PASSED^)
    echo ========================================
) else (
    echo ========================================
    echo   测试结果: 失败 ^(FAILED^)
    echo ========================================
)

echo.
pause
