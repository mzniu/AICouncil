"""
初始化认证系统数据库并创建测试用户

使用方法:
    python init_auth_db.py

或者指定用户名和密码:
    python init_auth_db.py --username admin --password Admin123!
"""
import sys
import pathlib

# 添加项目根目录到sys.path
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import argparse
from src.models import db, User
from src.web.app import app

def init_database():
    """初始化数据库表"""
    with app.app_context():
        # 创建所有表
        db.create_all()
        print("✅ 数据库表创建成功")

def create_test_user(username="testuser", password="Test123!", email="test@example.com"):
    """创建测试用户"""
    with app.app_context():
        # 检查用户是否已存在
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            print(f"⚠️  用户 '{username}' 已存在，跳过创建")
            return existing_user
        
        # 创建新用户
        user = User(username=username, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        print(f"✅ 测试用户创建成功:")
        print(f"   用户名: {username}")
        print(f"   密码: {password}")
        print(f"   邮箱: {email}")
        return user

def main():
    parser = argparse.ArgumentParser(description="初始化认证系统数据库")
    parser.add_argument("--username", default="testuser", help="测试用户名（默认: testuser）")
    parser.add_argument("--password", default="Test123!", help="测试密码（默认: Test123!）")
    parser.add_argument("--email", default="test@example.com", help="测试邮箱（默认: test@example.com）")
    parser.add_argument("--skip-user", action="store_true", help="跳过创建测试用户")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("初始化 AICouncil 认证系统")
    print("=" * 60)
    
    # 初始化数据库
    print("\n[1/2] 初始化数据库...")
    try:
        init_database()
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        return 1
    
    # 创建测试用户
    if not args.skip_user:
        print("\n[2/2] 创建测试用户...")
        try:
            create_test_user(args.username, args.password, args.email)
        except Exception as e:
            print(f"❌ 用户创建失败: {e}")
            import traceback
            traceback.print_exc()
            return 1
    else:
        print("\n[2/2] 跳过创建测试用户")
    
    print("\n" + "=" * 60)
    print("✅ 初始化完成！")
    print("=" * 60)
    print("\n接下来您可以:")
    print("1. 启动应用: python src/web/app.py")
    print("2. 访问 http://127.0.0.1:5000/login")
    if not args.skip_user:
        print(f"3. 使用账号登录: {args.username} / {args.password}")
    print("4. 或者注册新账号（需要在.env中设置 ALLOW_PUBLIC_REGISTRATION=true）")
    print("\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
