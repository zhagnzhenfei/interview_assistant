"""add invite code to orders

Revision ID: add_invite_code_to_orders
Revises: 
Create Date: 2024-03-31 11:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_invite_code_to_orders'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # 添加invite_code字段
    op.add_column('orders', sa.Column('invite_code', sa.String(50), nullable=True))
    # 添加original_amount字段
    op.add_column('orders', sa.Column('original_amount', sa.Float(), nullable=True))

def downgrade():
    # 删除invite_code字段
    op.drop_column('orders', 'invite_code')
    # 删除original_amount字段
    op.drop_column('orders', 'original_amount') 