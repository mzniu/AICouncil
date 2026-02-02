#!/usr/bin/env python
"""
创建管理员账号脚本
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.auth_config import User, db
from src.web.app import app

def create_admin_user(username='admin', password='Admin123456', email='admin@example.com'):
    """创建管理员用户"""
    with app.app_context():
        # 检查用户是否已存在
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            print(f'❌ 用户 "{username}" 已存在')
            print(f'   用户ID: {existing_user.id}')
            print(f'   邮箱: {existing_user.email}')
            print(f'   管理员: {"是" if existing_user.is_admin else "否"}')
            return False
        
        # 创建新用户
        user = User(
            username=username,
            email=email,
            is_admin=True,
            mfa_enabled=False
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        print('✅ 管理员账号创建成功！')
        print('─' * 40)
        print(f'用户名: {username}')
        print(f'密码:   {password}')
        print(f'邮箱:   {email}')
        print(f'管理员: 是')
        print('─' * 40)
        print('请访问 http://127.0.0.1:5000/login 登录')
        return True

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='创建AICouncil管理员账号')
    parser.add_argument('--username', default='admin', help='用户名（默认: admin）')
    parser.add_argument('--password', default='Admin123456', help='密码（默认: Admin123456）')
    parser.add_argument('--email', default='admin@example.com', help='邮箱（默认: admin@example.com）')
    
    args = parser.parse_args()
    
    create_admin_user(args.username, args.password, args.email)
