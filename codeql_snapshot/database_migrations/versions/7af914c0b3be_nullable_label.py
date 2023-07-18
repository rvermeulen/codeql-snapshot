"""nullable label

Revision ID: 7af914c0b3be
Revises: fb615c8abf95
Create Date: 2023-07-17 16:27:59.080685

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7af914c0b3be'
down_revision = 'fb615c8abf95'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('snapshots', 'label',
               existing_type=sa.VARCHAR(length=255),
               nullable=True)
    op.execute("UPDATE snapshots SET label = NULL WHERE label = 'default'")


def downgrade() -> None:
    op.execute("UPDATE snapshots SET label = 'default' WHERE label IS NULL")
    op.alter_column('snapshots', 'label',
               existing_type=sa.VARCHAR(length=255),
               nullable=False)
