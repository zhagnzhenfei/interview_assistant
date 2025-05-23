"""create pre_charges table

Revision ID: create_pre_charges_table
Revises: 
Create Date: 2024-03-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'create_pre_charges_table'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # 创建预扣费表
    op.create_table(
        'pre_charges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('task_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('refunded_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['accounts.user_id'], ),
        sa.UniqueConstraint('task_id')
    )
    
    # 创建索引
    op.create_index('idx_pre_charges_user_id', 'pre_charges', ['user_id'])
    op.create_index('idx_pre_charges_task_id', 'pre_charges', ['task_id'])
    op.create_index('idx_pre_charges_status', 'pre_charges', ['status'])

def downgrade():
    # 删除索引
    op.drop_index('idx_pre_charges_status')
    op.drop_index('idx_pre_charges_task_id')
    op.drop_index('idx_pre_charges_user_id')
    
    # 删除表
    op.drop_table('pre_charges') 