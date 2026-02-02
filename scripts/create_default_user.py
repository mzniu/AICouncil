#!/usr/bin/env python
"""
创建测试用户脚本
用于创建默认的管理员用户或测试用户
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.models import db, User
from src.web.app import app

def create_default_user():
    """创建默认用户"""
    with app.app_context():
        # 检查用户1是否存在
        existing_user = User.query.filter_by(id=1).first()
        if existing_user:
            print(f"✅ 用户已存在: {existing_user.username} (ID: {existing_user.id})")
            return existing_user
        
        # 创建默认用户
        user = User(username='admin', email='admin@aicouncil.local')
        user.set_password('Admin123456!')
        
        db.session.add(user)
        db.session.commit()
        
        print(f"✅ 创建默认用户成功:")
        print(f"   用户名: {user.username}")
        print(f"   邮箱: {user.email}")
        print(f"   ID: {user.id}")
        print(f"   密码: Admin123456!")
        
        return user

if __name__ == '__main__':
    create_default_user()
