"""
Skills管理UI测试脚本
验证前端JavaScript调用的API端点可访问性
"""
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.web.app import app

def test_skills_page_route():
    """测试技能管理页面路由"""
    with app.test_client() as client:
        # 未登录应重定向到登录页
        response = client.get('/skills', follow_redirects=False)
        # Flask-Login会重定向到登录页或返回401
        assert response.status_code in [302, 401], f"Expected 302 or 401, got {response.status_code}"
        print("✅ /skills 路由正确要求登录")

def test_api_routes_available():
    """测试API端点是否注册"""
    routes = [r.rule for r in app.url_map.iter_rules()]
    
    required_routes = [
        '/api/skills',
        '/api/skills/<int:skill_id>',
        '/api/skills/<int:skill_id>/subscribe',
        '/api/skills/<int:skill_id>/unsubscribe',
        '/api/skills/subscriptions',
        '/api/skills/stats',
        '/api/skills/merged'
    ]
    
    for route in required_routes:
        # 检查路由是否存在（考虑URL变量）
        base_route = route.replace('<int:skill_id>', '1')
        found = any(route.replace('<int:skill_id>', '<skill_id>') in r or route in r for r in routes)
        assert found, f"Route {route} not found in app"
        print(f"✅ {route} 已注册")

def test_template_exists():
    """测试模板文件是否存在"""
    template_path = os.path.join(project_root, 'src', 'web', 'templates', 'skills.html')
    assert os.path.exists(template_path), f"Template not found: {template_path}"
    
    # 检查文件不为空
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
        assert len(content) > 10000, "Template file seems too small"
        assert '<title>技能管理' in content, "Missing expected title"
        assert 'function loadSkills' in content, "Missing loadSkills function"
        assert 'function handleCreateSkill' in content, "Missing handleCreateSkill function"
        print("✅ skills.html 模板存在且包含必要组件")

if __name__ == '__main__':
    print("🧪 开始测试Skills管理UI...")
    print()
    
    try:
        test_skills_page_route()
        test_api_routes_available()
        test_template_exists()
        print()
        print("🎉 所有测试通过！")
    except AssertionError as e:
        print()
        print(f"❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print()
        print(f"❌ 测试错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
