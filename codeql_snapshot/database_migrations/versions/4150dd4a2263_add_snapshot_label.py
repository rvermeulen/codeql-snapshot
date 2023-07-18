"""Add snapshot label

Revision ID: 4150dd4a2263
Revises: abb9363cd21a
Create Date: 2023-06-23 14:05:58.298564

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4150dd4a2263'
down_revision = 'abb9363cd21a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('snapshots', sa.Column('label', sa.String(length=255), nullable=False))
    op.create_unique_constraint(op.f('uq_snapshots_global_id'), 'snapshots', ['global_id'])


def downgrade() -> None:
    op.drop_constraint(op.f('uq_snapshots_global_id'), 'snapshots', type_='unique')
    op.drop_column('snapshots', 'label')

