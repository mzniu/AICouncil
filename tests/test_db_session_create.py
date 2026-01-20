#!/usr/bin/env python3
"""测试数据库会话创建功能"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.web.app import app
from src.repositories.session_repository import SessionRepository
from datetime import datetime
import uuid

print("\n=== 测试数据库会话创建 ===\n")

# 测试1: 在应用上下文内创建
test_session_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]
test_user_id = 1  # 假设用户ID为1

print(f"测试Session ID: {test_session_id}")
print(f"测试User ID: {test_user_id}")

try:
    with app.app_context():
        print("\n✅ 应用上下文已创建")
        
        result = SessionRepository.create_session(
            user_id=test_user_id,
            session_id=test_session_id,
            issue="测试议题：验证数据库保存功能",
            config={"backend": "deepseek", "model": "deepseek-chat", "test": True}
        )
        
        if result:
            print(f"✅ 会话创建成功！")
            print(f"   ID: {result.id}")
            print(f"   Session ID: {result.session_id}")
            print(f"   User ID: {result.user_id}")
            print(f"   议题: {result.issue}")
            
            # 验证查询
            check = SessionRepository.get_session_by_id(test_session_id)
            if check:
                print(f"\n✅ 查询验证成功！")
                print(f"   创建时间: {check.created_at}")
            else:
                print(f"\n❌ 查询验证失败：会话不存在")
        else:
            print(f"❌ 会话创建返回None")
            
except Exception as e:
    print(f"\n❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n=== 测试完成 ===\n")
