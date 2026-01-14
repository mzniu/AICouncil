"""检查Flask路由注册情况"""
import sys
import pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.web.app import app

print("=" * 60)
print("已注册的认证相关路由:")
print("=" * 60)

auth_routes = [rule for rule in app.url_map.iter_rules() if 'auth' in rule.rule]

if auth_routes:
    for rule in auth_routes:
        print(f"{rule.methods} {rule.rule}")
else:
    print("⚠️ 没有找到认证路由！")

print("\n" + "=" * 60)
print(f"总共注册了 {len(list(app.url_map.iter_rules()))} 个路由")
print("=" * 60)
