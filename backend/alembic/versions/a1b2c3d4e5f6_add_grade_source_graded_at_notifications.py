"""Add grade_source, graded_at to picks and notifications table

Revision ID: a1b2c3d4e5f6
Revises: 83af7504fdf4
Create Date: 2026-03-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '83af7504fdf4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('picks', sa.Column('grade_source', sa.String(), nullable=True))
    op.add_column('picks', sa.Column('graded_at', sa.DateTime(), nullable=True))

    op.create_table('notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pick_id', sa.Integer(), sa.ForeignKey('picks.id', ondelete='CASCADE'), nullable=True),
        sa.Column('message', sa.String(), nullable=True),
        sa.Column('read', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notifications_id'), table_name='notifications')
    op.drop_table('notifications')
    op.drop_column('picks', 'graded_at')
    op.drop_column('picks', 'grade_source')
