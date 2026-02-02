"""Allow anonymous users (nullable user_id)

Revision ID: 003
Revises: 227f973e36f0
Create Date: 2025-01-01 00:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '227f973e36f0'
branch_labels = None
depends_on = None


def upgrade():
    """Allow NULL values for user_id to support anonymous users"""
    # 修改 discussion_sessions 表的 user_id 列为可空
    with op.batch_alter_table('discussion_sessions', schema=None) as batch_op:
        batch_op.alter_column('user_id',
                              existing_type=sa.Integer(),
                              nullable=True)


def downgrade():
    """Revert user_id to NOT NULL"""
    with op.batch_alter_table('discussion_sessions', schema=None) as batch_op:
        batch_op.alter_column('user_id',
                              existing_type=sa.Integer(),
                              nullable=False)
