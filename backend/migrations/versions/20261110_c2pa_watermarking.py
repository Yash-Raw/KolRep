"""add c2pa watermarking fields to generations

Revision ID: 20261110_c2pa
Revises: 119e28336ede
Create Date: 2026-11-10 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.database.base

# revision identifiers, used by Alembic.
revision: str = '20261110_c2pa'
down_revision: Union[str, Sequence[str], None] = '119e28336ede'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('generations', sa.Column('is_watermarked', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('generations', sa.Column('watermark_payload', app.database.base.CompatibleJSON(), nullable=True))
    op.add_column('generations', sa.Column('c2pa_manifest', app.database.base.CompatibleJSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('generations', 'c2pa_manifest')
    op.drop_column('generations', 'watermark_payload')
    op.drop_column('generations', 'is_watermarked')
