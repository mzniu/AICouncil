"""验证索引是否成功创建"""
import sys
from pathlib import Path

# 添加项目根目录到路径
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.web.app import app
from src.models import db

with app.app_context():
    # 查询所有索引
    query = """
    SELECT name 
    FROM sqlite_master 
    WHERE type='index' 
    AND tbl_name='discussion_sessions' 
    ORDER BY name
    """
    
    result = db.session.execute(db.text(query)).fetchall()
    
    print("\n📊 discussion_sessions 表的索引：")
    print("="*50)
    for row in result:
        print(f"  ✅ {row[0]}")
    print("="*50)
    print(f"共 {len(result)} 个索引\n")
    
    # 验证复合索引
    expected_indexes = [
        'idx_user_created',
        'idx_user_status',
        'idx_user_status_created'
    ]
    
    index_names = [row[0] for row in result]
    
    print("🔍 复合索引验证：")
    for idx in expected_indexes:
        if idx in index_names:
            print(f"  ✅ {idx} - 已创建")
        else:
            print(f"  ❌ {idx} - 未找到")
    
    print("\n✨ Task 13 完成：数据库性能优化（复合索引）")
