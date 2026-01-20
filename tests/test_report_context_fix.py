#!/usr/bin/env python3
"""测试generate_report_from_workspace的应用上下文修复"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.web.app import app
from src.auth_config import db
from src.models import DiscussionSession
from src.agents.langchain_agents import generate_report_from_workspace

with app.app_context():
    # 查找一个有数据的会话
    session = DiscussionSession.query.filter(
        DiscussionSession.report_html.isnot(None)
    ).order_by(DiscussionSession.created_at.desc()).first()
    
    if not session:
        print("❌ 数据库中没有包含报告的会话")
        sys.exit(1)
    
    print(f"\n测试会话: {session.session_id}")
    print(f"议题: {session.issue[:60]}...")
    print(f"原报告长度: {len(session.report_html)} 字符")
    
    # 构造最小配置
    model_config = {
        "type": session.backend or "deepseek",
        "model": session.model or "deepseek-chat"
    }
    
    print("\n🔄 正在重新生成报告...")
    try:
        # 测试报告生成（这会在内部创建app_context）
        new_report = generate_report_from_workspace(
            workspace_path=f"workspaces/{session.session_id}",
            model_config=model_config,
            session_id=session.session_id
        )
        
        print(f"✅ 报告生成成功！")
        print(f"   新报告长度: {len(new_report)} 字符")
        print(f"   包含HTML标签: {'<html>' in new_report}")
        
    except Exception as e:
        print(f"❌ 报告生成失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

print("\n✅ 应用上下文修复验证通过！")
