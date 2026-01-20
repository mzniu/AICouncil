"""Add discussion_sessions table for workspace storage

Revision ID: 001
Revises: 
Create Date: 2026-01-15 21:56:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """创建discussion_sessions表"""
    op.create_table('discussion_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('issue', sa.Text(), nullable=False),
        sa.Column('backend', sa.String(length=50), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('history', sa.JSON(), nullable=True),
        sa.Column('decomposition', sa.JSON(), nullable=True),
        sa.Column('final_session_data', sa.JSON(), nullable=True),
        sa.Column('search_references', sa.JSON(), nullable=True),
        sa.Column('report_html', sa.Text(), nullable=True),
        sa.Column('report_json', sa.JSON(), nullable=True),
        sa.Column('report_version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建索引
    op.create_index('ix_discussion_sessions_session_id', 'discussion_sessions', ['session_id'], unique=True)
    op.create_index('ix_discussion_sessions_user_id', 'discussion_sessions', ['user_id'], unique=False)
    op.create_index('ix_discussion_sessions_status', 'discussion_sessions', ['status'], unique=False)
    op.create_index('ix_discussion_sessions_created_at', 'discussion_sessions', ['created_at'], unique=False)
    op.create_index('ix_discussion_sessions_user_created', 'discussion_sessions', ['user_id', 'created_at'], unique=False)


def downgrade():
    """删除discussion_sessions表"""
    op.drop_index('ix_discussion_sessions_user_created', table_name='discussion_sessions')
    op.drop_index('ix_discussion_sessions_created_at', table_name='discussion_sessions')
    op.drop_index('ix_discussion_sessions_status', table_name='discussion_sessions')
    op.drop_index('ix_discussion_sessions_user_id', table_name='discussion_sessions')
    op.drop_index('ix_discussion_sessions_session_id', table_name='discussion_sessions')
    op.drop_table('discussion_sessions')
