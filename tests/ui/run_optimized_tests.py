"""
运行优化后的UI测试套件

优化说明：
- 旧方案：7个测试各自独立启动讨论，总耗时 35-70 分钟
- 新方案：使用class级别fixture共享一次讨论，总耗时 10-15 分钟
- 时间节省：约 70-80%

使用方法：
1. 只运行优化测试：
   python tests/ui/run_optimized_tests.py

2. 运行所有P0测试（包括优化和原始）：
   pytest tests/ui/ -v -m p0

3. 只运行优化的讨论测试：
   pytest tests/ui/test_discussion_optimized.py::TestDiscussionOptimized -v

4. 生成HTML测试报告：
   pytest tests/ui/test_discussion_optimized.py::TestDiscussionOptimized -v --html=test_report.html
"""
import subprocess
import sys
from pathlib import Path


def run_optimized_tests():
    """运行优化后的讨论测试"""
    print("=" * 80)
    print("🚀 运行优化后的讨论流程测试")
    print("=" * 80)
    print("\n📋 测试范围：")
    print("  - TestDiscussionOptimized (6个测试用例)")
    print("  - 共享一次完整讨论会话")
    print("  - 预计执行时间：10-15分钟")
    print("\n" + "=" * 80 + "\n")
    
    # 构建pytest命令
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/ui/test_discussion_optimized.py::TestDiscussionOptimized",
        "-v",
        "-m", "p0",
        "--tb=short"
    ]
    
    print(f"💻 执行命令: {' '.join(cmd)}\n")
    
    # 运行测试
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent.parent)
    
    print("\n" + "=" * 80)
    if result.returncode == 0:
        print("✅ 测试执行完成")
    else:
        print(f"❌ 测试失败，退出代码: {result.returncode}")
    print("=" * 80)
    
    return result.returncode


def run_comparison_test():
    """运行对比测试（优化前后）"""
    print("=" * 80)
    print("📊 性能对比测试")
    print("=" * 80)
    print("\n⚠️ 警告：此测试会运行旧测试和新测试，总耗时 45-85 分钟")
    print("建议只运行优化测试（run_optimized_tests）\n")
    
    response = input("是否继续？(y/N): ")
    if response.lower() != 'y':
        print("已取消")
        return 0
    
    print("\n1️⃣ 运行旧测试（每个用例独立启动讨论）...")
    old_cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/ui/test_discussion.py::TestDiscussion::test_agent_output_display_leader",
        "tests/ui/test_discussion.py::TestDiscussion::test_agent_output_display_planner",
        "tests/ui/test_discussion.py::TestDiscussion::test_agent_output_display_auditor",
        "-v",
        "--tb=line"
    ]
    
    print(f"💻 {' '.join(old_cmd)}\n")
    old_result = subprocess.run(old_cmd, cwd=Path(__file__).parent.parent.parent)
    
    print("\n2️⃣ 运行新测试（共享一次讨论会话）...")
    new_result = run_optimized_tests()
    
    print("\n" + "=" * 80)
    print("📈 对比结果:")
    print(f"  旧测试: {'通过' if old_result.returncode == 0 else '失败'}")
    print(f"  新测试: {'通过' if new_result.returncode == 0 else '失败'}")
    print("=" * 80)
    
    return 0 if old_result.returncode == 0 and new_result.returncode == 0 else 1


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="运行优化后的UI测试")
    parser.add_argument(
        "--compare",
        action="store_true",
        help="运行性能对比测试（警告：耗时很长）"
    )
    
    args = parser.parse_args()
    
    if args.compare:
        exit_code = run_comparison_test()
    else:
        exit_code = run_optimized_tests()
    
    sys.exit(exit_code)
