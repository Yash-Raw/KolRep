"""drop agent and agent_sessions tables

Revision ID: 20261114_drop_agent_tables
Revises: 20261110_c2pa
Create Date: 2026-11-14 01:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.database.base

# revision identifiers, used by Alembic.
revision: str = '20261114_drop_agent_tables'
down_revision: Union[str, Sequence[str], None] = '20261110_c2pa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop agent_sessions table and indices first (foreign key dependency)
    op.drop_index(op.f('ix_agent_sessions_status'), table_name='agent_sessions')
    op.drop_index(op.f('ix_agent_sessions_owner_id'), table_name='agent_sessions')
    op.drop_index('ix_agent_sessions_owner_agent', table_name='agent_sessions')
    op.drop_index(op.f('ix_agent_sessions_agent_id'), table_name='agent_sessions')
    op.drop_table('agent_sessions')

    # Drop agents table and indices
    op.drop_index(op.f('ix_agents_voice_id'), table_name='agents')
    op.drop_index(op.f('ix_agents_status'), table_name='agents')
    op.drop_index('ix_agents_owner_status', table_name='agents')
    op.drop_index(op.f('ix_agents_owner_id'), table_name='agents')
    op.drop_table('agents')


def downgrade() -> None:
    op.create_table('agents',
        sa.Column('id', app.database.base.GUID(), nullable=False),
        sa.Column('owner_id', app.database.base.GUID(), nullable=False),
        sa.Column('voice_id', app.database.base.GUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('first_message', sa.Text(), nullable=False),
        sa.Column('language', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['voice_id'], ['voices.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agents_owner_id'), 'agents', ['owner_id'], unique=False)
    op.create_index('ix_agents_owner_status', 'agents', ['owner_id', 'status'], unique=False)
    op.create_index(op.f('ix_agents_status'), 'agents', ['status'], unique=False)
    op.create_index(op.f('ix_agents_voice_id'), 'agents', ['voice_id'], unique=False)

    op.create_table('agent_sessions',
        sa.Column('id', app.database.base.GUID(), nullable=False),
        sa.Column('owner_id', app.database.base.GUID(), nullable=False),
        sa.Column('agent_id', app.database.base.GUID(), nullable=False),
        sa.Column('provider_conversation_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_sessions_agent_id'), 'agent_sessions', ['agent_id'], unique=False)
    op.create_index('ix_agent_sessions_owner_agent', 'agent_sessions', ['owner_id', 'agent_id'], unique=False)
    op.create_index(op.f('ix_agent_sessions_owner_id'), 'agent_sessions', ['owner_id'], unique=False)
    op.create_index(op.f('ix_agent_sessions_status'), 'agent_sessions', ['status'], unique=False)
