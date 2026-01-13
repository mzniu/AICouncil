"""测试认证相关路由是否正确注册"""
import sys
import pathlib

# 添加项目根目录到路径
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.web.app import app

with app.test_request_context():
    print("\n✅ 已注册的认证相关路由:")
    routes = [r for r in app.url_map.iter_rules() if any(x in r.rule for x in ['/login', '/mfa', '/auth', '/register'])]
    for r in sorted(routes, key=lambda x: x.rule):
        methods = ', '.join(r.methods - {"HEAD", "OPTIONS"})
        print(f"  {r.rule:40} ({methods})")
    
    print(f"\n总计: {len(routes)} 个认证相关路由")
