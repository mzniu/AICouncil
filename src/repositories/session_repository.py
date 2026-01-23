"""
SessionRepository - 议事会话数据访问层
提供discussion_sessions表的CRUD操作，确保多用户数据隔离
"""
from src.models import db, DiscussionSession
from src.utils.logger import logger
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError


class SessionRepository:
    """议事会话数据仓库，封装所有数据库操作"""
    
    @staticmethod
    def create_session(user_id: Optional[int], session_id: str, issue: str, config: dict, 
                      tenant_id: Optional[int] = None) -> Optional[DiscussionSession]:
        """
        创建新会话
        
        Args:
            user_id: 用户ID（None表示匿名用户）
            session_id: 会话ID（格式：20251224_183032_uuid）
            issue: 议题内容
            config: 配置字典 {backend, model, rounds, planners, auditors, reasoning, agent_configs}
            tenant_id: 租户ID（可选，用于多租户隔离）
            
        Returns:
            DiscussionSession对象，失败返回None
        """
        try:
            session = DiscussionSession(
                session_id=session_id,
                user_id=user_id,
                tenant_id=tenant_id,
                issue=issue,
                backend=config.get('backend'),
                model=config.get('model'),
                config=config,
                status='running',
                report_version=1
            )
            db.session.add(session)
            db.session.commit()
            logger.info(f"[SessionRepo] 创建会话成功: {session_id} (用户{user_id}, 租户{tenant_id})")
            return session
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"[SessionRepo] 创建会话失败: {e}")
            return None
    
    @staticmethod
    def update_history(session_id: str, history_data: list) -> bool:
        """
        更新讨论历史
        
        Args:
            session_id: 会话ID
            history_data: 历史数据列表（JSON格式）
            
        Returns:
            bool: 成功返回True，失败返回False
        """
        try:
            session = DiscussionSession.query.filter_by(session_id=session_id).first()
            if not session:
                logger.warning(f"[SessionRepo] 会话不存在: {session_id}")
                return False
            
            session.history = history_data
            db.session.commit()
            logger.debug(f"[SessionRepo] 更新history成功: {session_id}")
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"[SessionRepo] 更新history失败: {e}")
            return False
    
    @staticmethod
    def update_decomposition(session_id: str, decomposition_data: dict) -> bool:
        """
        更新议题分解数据
        
        Args:
            session_id: 会话ID
            decomposition_data: 分解数据字典
            
        Returns:
            bool: 成功返回True
        """
        try:
            session = DiscussionSession.query.filter_by(session_id=session_id).first()
            if not session:
                return False
            
            session.decomposition = decomposition_data
            db.session.commit()
            logger.debug(f"[SessionRepo] 更新decomposition成功: {session_id}")
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"[SessionRepo] 更新decomposition失败: {e}")
            return False
    
    @staticmethod
    def update_final_session_data(session_id: str, final_data: dict) -> bool:
        """
        更新最终会话数据
        
        Args:
            session_id: 会话ID
            final_data: 最终数据字典
            
        Returns:
            bool: 成功返回True
        """
        try:
            session = DiscussionSession.query.filter_by(session_id=session_id).first()
            if not session:
                return False
            
            session.final_session_data = final_data
            db.session.commit()
            logger.debug(f"[SessionRepo] 更新final_session_data成功: {session_id}")
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"[SessionRepo] 更新final_session_data失败: {e}")
            return False
    
    @staticmethod
    def update_search_references(session_id: str, search_data: dict) -> bool:
        """
        更新搜索引用数据
        
        Args:
            session_id: 会话ID
            search_data: 搜索引用字典
            
        Returns:
            bool: 成功返回True
        """
        try:
            session = DiscussionSession.query.filter_by(session_id=session_id).first()
            if not session:
                return False
            
            session.search_references = search_data
            db.session.commit()
            logger.debug(f"[SessionRepo] 更新search_references成功: {session_id}")
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"[SessionRepo] 更新search_references失败: {e}")
            return False
    
    @staticmethod
    def save_final_report(session_id: str, report_html: str, report_json: Optional[dict] = None) -> bool:
        """
        保存最终报告
        
        Args:
            session_id: 会话ID
            report_html: HTML报告内容
            report_json: 结构化报告数据（可选）
            
        Returns:
            bool: 成功返回True
        """
        try:
            session = DiscussionSession.query.filter_by(session_id=session_id).first()
            if not session:
                return False
            
            session.report_html = report_html
            if report_json:
                session.report_json = report_json
            session.status = 'completed'
            session.completed_at = datetime.utcnow()
            db.session.commit()
            logger.info(f"[SessionRepo] 保存报告成功: {session_id}")
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"[SessionRepo] 保存报告失败: {e}")
            return False
    
    @staticmethod
    def increment_report_version(session_id: str) -> int:
        """
        递增报告版本号（用于重新生成报告）
        
        Args:
            session_id: 会话ID
            
        Returns:
            int: 新的版本号，失败返回-1
        """
        try:
            session = DiscussionSession.query.filter_by(session_id=session_id).first()
            if not session:
                return -1
            
            session.report_version += 1
            db.session.commit()
            logger.info(f"[SessionRepo] 报告版本递增: {session_id} -> v{session.report_version}")
            return session.report_version
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"[SessionRepo] 递增版本失败: {e}")
            return -1
    
    @staticmethod
    def update_status(session_id: str, status: str) -> bool:
        """
        更新会话状态
        
        Args:
            session_id: 会话ID
            status: 状态值（running/completed/failed/stopped）
            
        Returns:
            bool: 成功返回True
        """
        try:
            session = DiscussionSession.query.filter_by(session_id=session_id).first()
            if not session:
                return False
            
            session.status = status
            if status in ['completed', 'failed', 'stopped'] and not session.completed_at:
                session.completed_at = datetime.utcnow()
            db.session.commit()
            logger.debug(f"[SessionRepo] 更新状态成功: {session_id} -> {status}")
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"[SessionRepo] 更新状态失败: {e}")
            return False
    
    @staticmethod
    def get_user_sessions(user_id: Optional[int], page: int = 1, per_page: int = 50, 
                         status_filter: Optional[str] = None, tenant_id: Optional[int] = None) -> List[DiscussionSession]:
        """
        获取用户会话列表（分页）
        
        Args:
            user_id: 用户ID（None表示匿名用户）
            page: 页码（从1开始）
            per_page: 每页数量
            status_filter: 状态过滤（可选：running/completed/failed/stopped）
            tenant_id: 租户ID（多租户隔离，None表示不过滤）
            
        Returns:
            List[DiscussionSession]: 会话列表
        """
        try:
            # 支持匿名用户查询（user_id为None时查询所有匿名会话）
            if user_id is None:
                query = DiscussionSession.query.filter(DiscussionSession.user_id.is_(None))
            else:
                query = DiscussionSession.query.filter_by(user_id=user_id)
            
            # 多租户隔离
            if tenant_id is not None:
                query = query.filter_by(tenant_id=tenant_id)
            
            if status_filter:
                query = query.filter_by(status=status_filter)
            
            sessions = query.order_by(DiscussionSession.created_at.desc())\
                           .paginate(page=page, per_page=per_page, error_out=False)
            
            logger.debug(f"[SessionRepo] 获取用户{user_id}会话列表: {len(sessions.items)}条")
            return sessions.items
        except SQLAlchemyError as e:
            logger.error(f"[SessionRepo] 获取会话列表失败: {e}")
            return []
    
    @staticmethod
    def get_session_by_id(session_id: str) -> Optional[DiscussionSession]:
        """
        根据session_id获取会话详情
        
        Args:
            session_id: 会话ID
            
        Returns:
            DiscussionSession对象，不存在返回None
        """
        try:
            session = DiscussionSession.query.filter_by(session_id=session_id).first()
            if session:
                logger.debug(f"[SessionRepo] 获取会话成功: {session_id}")
            else:
                logger.warning(f"[SessionRepo] 会话不存在: {session_id}")
            return session
        except SQLAlchemyError as e:
            logger.error(f"[SessionRepo] 获取会话失败: {e}")
            return None
    
    @staticmethod
    def get_session_count(user_id: Optional[int], status_filter: Optional[str] = None, tenant_id: Optional[int] = None) -> int:
        """
        获取用户会话总数
        
        Args:
            user_id: 用户ID（None表示匿名用户）
            status_filter: 状态过滤（可选）
            tenant_id: 租户ID（多租户隔离，None表示不过滤）
            
        Returns:
            int: 会话总数
        """
        try:
            # 支持匿名用户查询
            if user_id is None:
                query = DiscussionSession.query.filter(DiscussionSession.user_id.is_(None))
            else:
                query = DiscussionSession.query.filter_by(user_id=user_id)
            
            # 多租户隔离
            if tenant_id is not None:
                query = query.filter_by(tenant_id=tenant_id)
            
            if status_filter:
                query = query.filter_by(status=status_filter)
            return query.count()
        except SQLAlchemyError as e:
            logger.error(f"[SessionRepo] 获取会话计数失败: {e}")
            return 0
    
    @staticmethod
    def check_user_permission(user_id: int, session_id: str) -> bool:
        """
        检查用户是否有权访问指定会话
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            
        Returns:
            bool: 有权限返回True
        """
        try:
            session = DiscussionSession.query.filter_by(
                session_id=session_id, 
                user_id=user_id
            ).first()
            return session is not None
        except SQLAlchemyError as e:
            logger.error(f"[SessionRepo] 权限检查失败: {e}")
            return False    
    @staticmethod
    def get_sessions_by_tenant(tenant_id: int, page: int = 1, per_page: int = 50,
                               status_filter: Optional[str] = None) -> List[DiscussionSession]:
        """
        获取租户下所有会话（tenant-aware查询）
        
        Args:
            tenant_id: 租户ID
            page: 页码（从1开始）
            per_page: 每页数量
            status_filter: 状态过滤（可选）
            
        Returns:
            List[DiscussionSession]: 会话列表
        """
        try:
            query = DiscussionSession.query.filter_by(tenant_id=tenant_id)
            
            if status_filter:
                query = query.filter_by(status=status_filter)
            
            sessions = query.order_by(DiscussionSession.created_at.desc())\
                           .paginate(page=page, per_page=per_page, error_out=False)
            
            logger.debug(f"[SessionRepo] 获取租户{tenant_id}会话列表: {len(sessions.items)}条")
            return sessions.items
        except SQLAlchemyError as e:
            logger.error(f"[SessionRepo] 获取租户会话列表失败: {e}")
            return []
    
    @staticmethod
    def get_tenant_session_count(tenant_id: int, status_filter: Optional[str] = None) -> int:
        """
        获取租户会话总数
        
        Args:
            tenant_id: 租户ID
            status_filter: 状态过滤（可选）
            
        Returns:
            int: 会话总数
        """
        try:
            query = DiscussionSession.query.filter_by(tenant_id=tenant_id)
            if status_filter:
                query = query.filter_by(status=status_filter)
            return query.count()
        except SQLAlchemyError as e:
            logger.error(f"[SessionRepo] 获取租户会话计数失败: {e}")
            return 0