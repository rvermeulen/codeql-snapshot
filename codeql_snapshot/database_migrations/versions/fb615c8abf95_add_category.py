"""add category

Revision ID: fb615c8abf95
Revises: 4150dd4a2263
Create Date: 2023-07-13 15:00:22.421532

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fb615c8abf95'
down_revision = '4150dd4a2263'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new column
    op.add_column('snapshots', sa.Column('category', sa.String(length=255), nullable=True))
    # Drop the primary key constraint on the snapshots table
    op.drop_constraint(op.f('pk_snapshots'), 'snapshots', type_='primary')
    # Drop the unique constraint on the snapshots table
    op.drop_constraint(op.f('uq_snapshots_global_id'), 'snapshots', type_='unique')
    # Add the new primary key constraint on the snapshots table
    op.create_primary_key(op.f('pk_snapshots'), 'snapshots', ['global_id'])


def downgrade() -> None:
    # Remove column
    op.drop_column('snapshots', 'category')
    # Restore constraints
    op.drop_constraint(op.f('pk_snapshots'), 'snapshots', type_='primary')
    op.create_primary_key(op.f('pk_snapshots'), 'snapshots', ['project_url', 'branch', 'commit', 'language'])
    op.create_unique_constraint(op.f('uq_snapshots_global_id'), 'snapshots', ['global_id'])
    
