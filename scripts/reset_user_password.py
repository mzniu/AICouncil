#!/usr/bin/env python
"""
用户密码重置脚本
支持验证密码或重置密码
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.models import db, User
from src.web.app import app

def reset_password(username: str, new_password: str = None, verify_only: bool = False):
    """重置或验证用户密码"""
    with app.app_context():
        # 查找用户
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"❌ 用户不存在: {username}")
            return False
        
        print(f"📋 找到用户: {user.username} (ID: {user.id}, 邮箱: {user.email})")
        
        if verify_only:
            # 验证模式
            test_password = input("请输入要验证的密码: ")
            if user.check_password(test_password):
                print(f"✅ 密码正确！")
                return True
            else:
                print(f"❌ 密码错误！")
                return False
        else:
            # 重置模式
            if not new_password:
                new_password = input("请输入新密码: ")
                confirm = input("请再次确认新密码: ")
                if new_password != confirm:
                    print("❌ 两次输入的密码不一致！")
                    return False
            
            # 设置新密码
            user.set_password(new_password)
            db.session.commit()
            
            print(f"✅ 密码重置成功！")
            print(f"   用户名: {user.username}")
            print(f"   新密码: {new_password}")
            return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="用户密码管理工具")
    parser.add_argument("username", help="用户名")
    parser.add_argument("--verify", action="store_true", help="验证密码（不修改）")
    parser.add_argument("--password", help="新密码（非交互模式）")
    
    args = parser.parse_args()
    
    try:
        success = reset_password(args.username, args.password, args.verify)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)
