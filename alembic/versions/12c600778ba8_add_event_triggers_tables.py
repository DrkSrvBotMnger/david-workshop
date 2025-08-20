"""Add event triggers tables

Revision ID: 12c600778ba8
Revises: 
Create Date: 2025-08-17 15:47:49.548099

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '12c600778ba8'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'event_triggers',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=True),
        sa.Column('trigger_type', sa.String(), nullable=False),
        sa.Column('config_json', sa.Text(), nullable=False),
        sa.Column('reward_event_id', sa.Integer(), sa.ForeignKey('reward_events.id', ondelete='SET NULL'), nullable=True),
        sa.Column('points_granted', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=False)
    )
    op.create_table(
        'user_event_trigger_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_trigger_id', sa.Integer(), sa.ForeignKey('event_triggers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('granted_at', sa.String(), nullable=False),
        sa.UniqueConstraint('user_id', 'event_trigger_id', name='uix_user_event_trigger')
    )

def downgrade():
    op.drop_table('user_event_trigger_log')
    op.drop_table('event_triggers')