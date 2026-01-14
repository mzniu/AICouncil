"""测试MFA设置端点"""
import requests

base_url = "http://127.0.0.1:5000"

print("=" * 60)
print("测试 MFA 设置端点")
print("=" * 60)

# 第一步：登录获取session
print("\n[Step 1] 登录测试账户...")
login_response = requests.post(
    f"{base_url}/api/auth/login",
    json={
        "username": "testuser",
        "password": "Test123!",
        "remember_me": False
    }
)

if login_response.status_code == 200:
    print(f"✅ 登录成功")
    session_cookie = login_response.cookies
else:
    print(f"❌ 登录失败: {login_response.status_code}")
    print(f"   响应: {login_response.text}")
    exit(1)

# 第二步：访问MFA设置端点
print("\n[Step 2] 访问 MFA 设置端点...")
mfa_response = requests.post(
    f"{base_url}/api/auth/mfa/setup",
    cookies=session_cookie
)

print(f"状态码: {mfa_response.status_code}")
print(f"响应头: {dict(mfa_response.headers)}")

if mfa_response.status_code == 200:
    data = mfa_response.json()
    print(f"✅ MFA 设置成功")
    print(f"   Secret: {data.get('secret', 'N/A')}")
    print(f"   QR Code: {'存在' if data.get('qr_code') else '缺失'}")
else:
    print(f"❌ MFA 设置失败")
    print(f"   内容类型: {mfa_response.headers.get('Content-Type')}")
    print(f"   响应前100字符: {mfa_response.text[:100]}")

print("\n" + "=" * 60)
