"""测试认证端点是否可访问"""
import requests
import json

base_url = "http://127.0.0.1:5000"

print("=" * 60)
print("测试认证API端点")
print("=" * 60)

# 测试 /api/auth/status
print("\n[1] 测试 GET /api/auth/status")
try:
    response = requests.get(f"{base_url}/api/auth/status")
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"   响应: {response.json()}")
        print("   ✅ 端点可访问")
    else:
        print(f"   响应: {response.text[:200]}")
        print("   ❌ 端点返回错误状态码")
except requests.exceptions.ConnectionError:
    print("   ❌ 无法连接到服务器，请确保应用已启动")
    print("   提示：运行 'python src/web/app.py'")
except Exception as e:
    print(f"   ❌ 请求失败: {e}")

# 测试 /api/auth/login
print("\n[2] 测试 POST /api/auth/login (空数据)")
try:
    response = requests.post(f"{base_url}/api/auth/login", json={})
    print(f"   状态码: {response.status_code}")
    print(f"   响应: {response.json()}")
    print("   ✅ 端点可访问")
except requests.exceptions.ConnectionError:
    print("   ❌ 无法连接到服务器")
except Exception as e:
    print(f"   ❌ 请求失败: {e}")

print("\n" + "=" * 60)
print("提示：")
print("1. 如果看到 ConnectionError，请先启动应用:")
print("   python src/web/app.py")
print("2. 如果状态码为 404，说明路由未注册，需要检查代码")
print("3. 如果状态码为 200/400/401，说明端点正常工作")
print("=" * 60)
