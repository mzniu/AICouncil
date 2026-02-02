#!/usr/bin/env python
"""
历史workspace迁移脚本

功能：
1. 扫描workspaces/目录下的所有会话
2. 解析会话元数据（history.json, decomposition.json, final_session_data.json, report.html）
3. 导入到数据库，默认分配给user_id=1
4. 支持增量迁移（跳过已存在的会话）
5. 生成详细的迁移报告

使用方法：
    python scripts/migrate_workspaces_to_db.py --user-id 1 --dry-run
    python scripts/migrate_workspaces_to_db.py --user-id 1
"""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List

# 添加项目根目录到路径
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.models import db, User
from src.repositories import SessionRepository
from src.utils.path_manager import get_workspace_dir
from src.utils.logger import logger


class WorkspaceMigrator:
    """Workspace迁移器"""
    
    def __init__(self, target_user_id: int, dry_run: bool = False):
        self.target_user_id = target_user_id
        self.dry_run = dry_run
        self.stats = {
            'total': 0,
            'migrated': 0,
            'skipped': 0,
            'failed': 0,
            'errors': []
        }
    
    def parse_workspace(self, workspace_path: Path) -> Optional[Dict]:
        """
        解析workspace目录，提取元数据
        
        Returns:
            dict: 包含session_id, issue, backend, model, config, history等字段
            None: 解析失败
        """
        session_id = workspace_path.name
        metadata = {
            'session_id': session_id,
            'issue': '未知议题',
            'backend': 'deepseek',  # 默认值
            'model': 'deepseek-chat',  # 默认值
            'config': {},
            'status': 'completed',  # 历史会话默认为已完成
            'history': None,
            'decomposition': None,
            'final_session_data': None,
            'search_references': None,
            'report_html': None,
            'report_json': None,
            'created_at': None,
            'completed_at': None
        }
        
        try:
            # 1. 尝试从final_session_data.json获取完整信息
            final_data_path = workspace_path / 'final_session_data.json'
            if final_data_path.exists():
                with open(final_data_path, 'r', encoding='utf-8') as f:
                    final_data = json.load(f)
                    metadata['issue'] = final_data.get('issue', metadata['issue'])
                    metadata['final_session_data'] = final_data
                    
                    # 提取history
                    if 'history' in final_data:
                        metadata['history'] = final_data['history']
                    
                    # 提取decomposition
                    if 'decomposition' in final_data:
                        metadata['decomposition'] = final_data['decomposition']
            
            # 2. 如果没有final_session_data，尝试单独加载文件
            if not metadata['history']:
                history_path = workspace_path / 'history.json'
                if history_path.exists():
                    with open(history_path, 'r', encoding='utf-8') as f:
                        metadata['history'] = json.load(f)
            
            if not metadata['decomposition']:
                decomp_path = workspace_path / 'decomposition.json'
                if decomp_path.exists():
                    with open(decomp_path, 'r', encoding='utf-8') as f:
                        decomp_data = json.load(f)
                        metadata['decomposition'] = decomp_data
                        # 如果issue还是默认值，从decomposition提取
                        if metadata['issue'] == '未知议题':
                            metadata['issue'] = decomp_data.get('core_goal', metadata['issue'])
            
            # 3. 加载report.html
            report_path = workspace_path / 'report.html'
            if report_path.exists():
                with open(report_path, 'r', encoding='utf-8') as f:
                    metadata['report_html'] = f.read()
            
            # 4. 尝试从orchestration_result.json获取信息（议事编排官模式）
            orch_path = workspace_path / 'orchestration_result.json'
            if orch_path.exists():
                with open(orch_path, 'r', encoding='utf-8') as f:
                    orch_data = json.load(f)
                    metadata['issue'] = orch_data.get('user_requirement', metadata['issue'])
                    # 可以将整个orchestration_result存储为final_session_data的一部分
                    if not metadata['final_session_data']:
                        metadata['final_session_data'] = orch_data
            
            # 5. 尝试推断backend和model（从config或history中提取）
            if metadata['history'] and isinstance(metadata['history'], list):
                # 检查第一轮的配置
                for round_data in metadata['history']:
                    if isinstance(round_data, dict) and 'config' in round_data:
                        config = round_data['config']
                        metadata['backend'] = config.get('backend', metadata['backend'])
                        metadata['model'] = config.get('model', metadata['model'])
                        break
            
            # 6. 从session_id提取创建时间（格式：20260116_123456_uuid）
            parts = session_id.split('_')
            if len(parts) >= 2 and parts[0].isdigit() and len(parts[0]) == 8:
                try:
                    date_str = parts[0]
                    time_str = parts[1] if len(parts) > 1 and parts[1].isdigit() else '000000'
                    dt_str = f"{date_str}_{time_str}"
                    metadata['created_at'] = datetime.strptime(dt_str, '%Y%m%d_%H%M%S')
                    # 历史会话假设创建后立即完成
                    metadata['completed_at'] = metadata['created_at']
                except:
                    pass
            
            # 7. 构建config字段（用于存储配置信息）
            metadata['config'] = {
                'backend': metadata['backend'],
                'model': metadata['model'],
                'migrated': True,
                'migration_date': datetime.now().isoformat()
            }
            
            return metadata
        
        except Exception as e:
            logger.error(f"[Migrator] 解析workspace失败 {session_id}: {e}")
            self.stats['errors'].append({
                'session_id': session_id,
                'error': str(e)
            })
            return None
    
    def migrate_workspace(self, metadata: Dict) -> bool:
        """
        将单个workspace迁移到数据库
        
        Returns:
            bool: 成功返回True
        """
        session_id = metadata['session_id']
        
        try:
            # 检查是否已存在
            existing = SessionRepository.get_session_by_id(session_id)
            if existing:
                logger.info(f"[Migrator] 会话已存在，跳过: {session_id}")
                self.stats['skipped'] += 1
                return False
            
            if self.dry_run:
                logger.info(f"[Migrator] [DRY RUN] 将迁移: {session_id} -> 用户{self.target_user_id}")
                self.stats['migrated'] += 1
                return True
            
            # 创建会话记录
            session = SessionRepository.create_session(
                user_id=self.target_user_id,
                session_id=session_id,
                issue=metadata['issue'],
                config=metadata['config']
            )
            
            if not session:
                raise Exception("创建会话失败")
            
            # 设置backend和model
            session.backend = metadata['backend']
            session.model = metadata['model']
            session.status = metadata['status']
            
            # 设置创建和完成时间
            if metadata.get('created_at'):
                session.created_at = metadata['created_at']
            if metadata.get('completed_at'):
                session.completed_at = metadata['completed_at']
            
            db.session.commit()
            
            # 更新各项数据
            if metadata.get('history'):
                SessionRepository.update_history(session_id, metadata['history'])
            
            if metadata.get('decomposition'):
                SessionRepository.update_decomposition(session_id, metadata['decomposition'])
            
            if metadata.get('final_session_data'):
                SessionRepository.update_final_session_data(session_id, metadata['final_session_data'])
            
            if metadata.get('search_references'):
                SessionRepository.update_search_references(session_id, metadata['search_references'])
            
            if metadata.get('report_html'):
                # 只更新report_html，不改变状态（因为已经是completed）
                session_db = SessionRepository.get_session_by_id(session_id)
                if session_db:
                    session_db.report_html = metadata['report_html']
                    db.session.commit()
            
            logger.info(f"[Migrator] ✅ 迁移成功: {session_id} -> 用户{self.target_user_id}")
            self.stats['migrated'] += 1
            return True
        
        except Exception as e:
            logger.error(f"[Migrator] ❌ 迁移失败 {session_id}: {e}")
            self.stats['failed'] += 1
            self.stats['errors'].append({
                'session_id': session_id,
                'error': str(e)
            })
            return False
    
    def scan_and_migrate(self) -> Dict:
        """
        扫描workspaces目录并执行迁移
        
        Returns:
            dict: 迁移统计信息
        """
        workspace_root = get_workspace_dir()
        
        if not workspace_root.exists():
            logger.warning(f"[Migrator] Workspace目录不存在: {workspace_root}")
            return self.stats
        
        logger.info(f"[Migrator] 开始扫描: {workspace_root}")
        logger.info(f"[Migrator] 目标用户: {self.target_user_id}")
        logger.info(f"[Migrator] 模式: {'DRY RUN (不实际写入)' if self.dry_run else '实际迁移'}")
        
        # 扫描所有子目录
        workspaces = [d for d in workspace_root.iterdir() if d.is_dir()]
        self.stats['total'] = len(workspaces)
        
        logger.info(f"[Migrator] 发现 {self.stats['total']} 个workspace")
        
        for workspace_path in workspaces:
            session_id = workspace_path.name
            logger.info(f"[Migrator] 处理: {session_id}")
            
            # 解析metadata
            metadata = self.parse_workspace(workspace_path)
            if not metadata:
                self.stats['failed'] += 1
                continue
            
            # 执行迁移
            self.migrate_workspace(metadata)
        
        return self.stats
    
    def print_report(self):
        """打印迁移报告"""
        print("\n" + "="*60)
        print("📊 迁移报告")
        print("="*60)
        print(f"总计: {self.stats['total']}")
        print(f"✅ 成功迁移: {self.stats['migrated']}")
        print(f"⏭️  跳过（已存在）: {self.stats['skipped']}")
        print(f"❌ 失败: {self.stats['failed']}")
        
        if self.stats['errors']:
            print(f"\n错误详情:")
            for error in self.stats['errors'][:10]:  # 只显示前10个错误
                print(f"  - {error['session_id']}: {error['error']}")
            if len(self.stats['errors']) > 10:
                print(f"  ... 还有 {len(self.stats['errors']) - 10} 个错误")
        
        print("="*60)
        
        if self.dry_run:
            print("\n💡 这是DRY RUN模式，没有实际写入数据库")
            print("   移除 --dry-run 参数以执行实际迁移")


def main():
    parser = argparse.ArgumentParser(
        description='迁移历史workspace到数据库',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 预览迁移（不实际写入）
  python scripts/migrate_workspaces_to_db.py --user-id 1 --dry-run
  
  # 执行迁移到用户1
  python scripts/migrate_workspaces_to_db.py --user-id 1
  
  # 执行迁移到用户2
  python scripts/migrate_workspaces_to_db.py --user-id 2
        """
    )
    
    parser.add_argument(
        '--user-id',
        type=int,
        required=True,
        help='目标用户ID（历史会话将分配给此用户）'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='预览模式（不实际写入数据库）'
    )
    
    args = parser.parse_args()
    
    # 初始化Flask应用上下文
    from src.web.app import app
    
    with app.app_context():
        # 验证用户是否存在
        user = User.query.get(args.user_id)
        if not user:
            print(f"❌ 错误: 用户ID {args.user_id} 不存在")
            print(f"   请先创建用户或使用已存在的用户ID")
            sys.exit(1)
        
        print(f"✅ 目标用户: {user.username} (ID: {user.id})")
        
        # 执行迁移
        migrator = WorkspaceMigrator(
            target_user_id=args.user_id,
            dry_run=args.dry_run
        )
        
        stats = migrator.scan_and_migrate()
        migrator.print_report()
        
        # 返回状态码
        if stats['failed'] > 0:
            sys.exit(1)
        sys.exit(0)


if __name__ == '__main__':
    main()
