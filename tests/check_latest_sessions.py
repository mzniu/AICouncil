#!/usr/bin/env python3
"""检查数据库中最新会话的状态"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 从web.app导入Flask应用
from src.web.app import app
from src.auth_config import db
from src.models import DiscussionSession

with app.app_context():
    # 查询最新5个会话
    sessions = DiscussionSession.query.order_by(
        DiscussionSession.created_at.desc()
    ).limit(5).all()
    
    print("\n" + "="*80)
    print("数据库中最新5个会话:")
    print("="*80)
    
    for i, s in enumerate(sessions, 1):
        print(f"\n{i}. Session ID: {s.session_id}")
        print(f"   议题: {s.issue[:60]}...")
        print(f"   状态: {s.status}")
        print(f"   创建时间: {s.created_at}")
        print(f"   后端: {s.backend} / {s.model}")
        print(f"   历史轮次: {len(s.history or [])}")
        print(f"   有报告: {'是' if s.report_html else '否'} ({len(s.report_html or '')} 字符)")
        print(f"   搜索结果: {len(s.search_references or [])} 条")
        
        # 检查对应的workspace目录
        workspace_dir = f"workspaces/{s.session_id}"
        if os.path.exists(workspace_dir):
            files = os.listdir(workspace_dir)
            if files:
                print(f"   ⚠️  Workspace有文件: {len(files)} 个 - {', '.join(files[:3])}")
            else:
                print(f"   ✅ Workspace为空")
        else:
            print(f"   ❌ Workspace目录不存在")
    
    print("\n" + "="*80)
    print(f"数据库总会话数: {DiscussionSession.query.count()}")
    print("="*80)
